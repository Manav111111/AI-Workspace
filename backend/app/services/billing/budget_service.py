import datetime
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import BudgetExceededException, NotFoundException, ValidationException
from app.models.usage_budget import UsageBudget, UsageLedgerEntry
from app.services.billing.pricing_registry import ModelPricingRegistry
from app.services.billing.usage_adapter import StandardizedUsage
from app.services.observability.audit_service import AuditService
from app.services.observability.metrics import metrics_collector

logger = logging.getLogger("app.services.billing.budget_service")


class BudgetService:
    """Centralized governance service for tenant spend control, usage metering,
    and hard/soft budget enforcement.
    """

    @classmethod
    def _get_period_start(cls, period_type: str) -> datetime.datetime:
        now = datetime.datetime.now(datetime.timezone.utc)
        p = period_type.upper().strip()
        if p == "DAILY":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif p == "WEEKLY":
            # Monday of current week
            monday = now - datetime.timedelta(days=now.weekday())
            return monday.replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # MONTHLY (default)
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    @classmethod
    async def check_budget(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
        ai_employee_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Pre-check executed before billable operations (LLM generation, tools, voice).
        Raises BudgetExceededException if a hard limit is breached.
        Returns warning metadata if soft limit threshold is reached.
        """
        if not getattr(settings, "BUDGET_ENFORCEMENT_ENABLED", True):
            return {"allowed": True, "warning": False}

        # Find applicable active budgets: company-wide (ai_employee_id is null) or specific to this employee
        stmt = (
            select(UsageBudget)
            .where(
                UsageBudget.company_id == company_id,
                UsageBudget.is_active == True,
            )
        )
        if ai_employee_id:
            stmt = stmt.where(
                (UsageBudget.ai_employee_id == None) | (UsageBudget.ai_employee_id == ai_employee_id)
            )
        else:
            stmt = stmt.where(UsageBudget.ai_employee_id == None)

        res = await session.execute(stmt)
        budgets = res.scalars().all()

        warnings = []
        for b in budgets:
            period_start = cls._get_period_start(b.period_type)

            spend_stmt = (
                select(func.sum(UsageLedgerEntry.estimated_cost))
                .where(
                    UsageLedgerEntry.company_id == company_id,
                    UsageLedgerEntry.created_at >= period_start,
                )
            )
            if b.ai_employee_id:
                spend_stmt = spend_stmt.where(UsageLedgerEntry.ai_employee_id == b.ai_employee_id)

            spend_res = await session.execute(spend_stmt)
            raw_spend = spend_res.scalar() or Decimal("0.000000")
            current_spend = Decimal(str(raw_spend))
            limit = Decimal(str(b.limit_amount))

            utilization = (current_spend / limit) * Decimal("100") if limit > 0 else Decimal("0")

            # Check Hard Limit
            if current_spend >= limit and b.hard_limit_enabled:
                metrics_collector.record_budget_denial()
                logger.warning(
                    f"Hard budget exceeded | company={company_id} | employee={b.ai_employee_id} "
                    f"| budget='{b.budget_name}' | spent={current_spend} | limit={limit}"
                )
                try:
                    await AuditService.record_event(
                        session=session,
                        company_id=company_id,
                        ai_employee_id=b.ai_employee_id,
                        event_type="BUDGET_EXCEEDED",
                        resource_type="BUDGET",
                        resource_id=str(b.id),
                        metadata={
                            "budget_name": b.budget_name,
                            "current_spend": str(current_spend),
                            "limit_amount": str(limit),
                            "period": b.period_type,
                        },
                    )
                except Exception as ae:
                    logger.warning(f"Could not record audit event for budget exceeded: {ae}")

                raise BudgetExceededException(
                    f"The configured usage budget '{b.budget_name}' has been reached."
                )

            # Check Soft Limit Warning
            if float(utilization) >= b.soft_limit_percent:
                warnings.append({
                    "budget_id": str(b.id),
                    "budget_name": b.budget_name,
                    "utilization_percent": round(float(utilization), 1),
                    "spent": str(current_spend),
                    "limit": str(limit),
                })

        return {
            "allowed": True,
            "warning": len(warnings) > 0,
            "warnings": warnings,
        }

    @classmethod
    async def record_usage(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
        provider: str,
        model: str,
        usage: StandardizedUsage,
        ai_employee_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        trace_id: Optional[str] = None,
        operation_type: str = "LLM_GENERATION",
        audio_seconds: float = 0.0,
        idempotency_key: Optional[str] = None,
    ) -> UsageLedgerEntry:
        """Records an authoritative usage entry in the persistent ledger."""
        if idempotency_key:
            stmt = select(UsageLedgerEntry).where(
                UsageLedgerEntry.company_id == company_id,
                UsageLedgerEntry.idempotency_key == idempotency_key,
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                return existing

        pricing = await ModelPricingRegistry.get_pricing(session, provider, model)
        cost, cost_status, version_tag = ModelPricingRegistry.calculate_cost(
            pricing=pricing,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=usage.cached_tokens,
        )

        entry = UsageLedgerEntry(
            company_id=company_id,
            ai_employee_id=ai_employee_id,
            conversation_id=conversation_id,
            trace_id=trace_id,
            provider=provider,
            model=model,
            operation_type=operation_type,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=usage.cached_tokens,
            total_tokens=usage.total_tokens,
            audio_seconds=audio_seconds,
            estimated_cost=cost,
            currency="USD",
            cost_status=cost_status,
            usage_source=usage.usage_source,
            pricing_version_id=version_tag,
            idempotency_key=idempotency_key,
        )
        session.add(entry)
        await session.flush()

        logger.info(
            f"Usage recorded | company={company_id} | model={model} | "
            f"tokens={usage.total_tokens} (in={usage.input_tokens}, out={usage.output_tokens}, "
            f"cache={usage.cached_tokens}) | cost=${cost} [{cost_status}] | src={usage.usage_source}"
        )
        return entry

    @classmethod
    async def get_usage_summary(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
        ai_employee_id: Optional[uuid.UUID] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Provides aggregate operational cost and token metrics strictly for the authenticated tenant."""
        since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)

        base_filter = [
            UsageLedgerEntry.company_id == company_id,
            UsageLedgerEntry.created_at >= since,
        ]
        if ai_employee_id:
            base_filter.append(UsageLedgerEntry.ai_employee_id == ai_employee_id)

        # 1. Total tokens and cost
        totals_stmt = (
            select(
                func.sum(UsageLedgerEntry.input_tokens),
                func.sum(UsageLedgerEntry.output_tokens),
                func.sum(UsageLedgerEntry.cached_tokens),
                func.sum(UsageLedgerEntry.total_tokens),
                func.sum(UsageLedgerEntry.estimated_cost),
                func.count(UsageLedgerEntry.id),
            ).where(*base_filter)
        )
        totals_res = (await session.execute(totals_stmt)).first()
        in_tok = totals_res[0] or 0
        out_tok = totals_res[1] or 0
        cached_tok = totals_res[2] or 0
        total_tok = totals_res[3] or 0
        total_cost = totals_res[4] or Decimal("0.000000")
        total_reqs = totals_res[5] or 0

        # 2. Usage by Model
        model_stmt = (
            select(
                UsageLedgerEntry.model,
                func.sum(UsageLedgerEntry.total_tokens),
                func.sum(UsageLedgerEntry.estimated_cost),
                func.count(UsageLedgerEntry.id),
            )
            .where(*base_filter)
            .group_by(UsageLedgerEntry.model)
        )
        by_model = [
            {
                "model": row[0],
                "tokens": row[1] or 0,
                "cost": float(row[2] or 0),
                "requests": row[3] or 0,
            }
            for row in (await session.execute(model_stmt)).all()
        ]

        # 3. Usage by Source (PROVIDER_REPORTED vs TOKENIZER_ESTIMATED)
        source_stmt = (
            select(
                UsageLedgerEntry.usage_source,
                func.sum(UsageLedgerEntry.total_tokens),
                func.count(UsageLedgerEntry.id),
            )
            .where(*base_filter)
            .group_by(UsageLedgerEntry.usage_source)
        )
        by_source = [
            {
                "source": row[0],
                "tokens": row[1] or 0,
                "requests": row[2] or 0,
            }
            for row in (await session.execute(source_stmt)).all()
        ]

        # 4. Active Budgets Status
        budgets_stmt = select(UsageBudget).where(
            UsageBudget.company_id == company_id,
            UsageBudget.is_active == True,
        )
        if ai_employee_id:
            budgets_stmt = budgets_stmt.where(
                (UsageBudget.ai_employee_id == None) | (UsageBudget.ai_employee_id == ai_employee_id)
            )
        budgets = (await session.execute(budgets_stmt)).scalars().all()

        budgets_status = []
        for b in budgets:
            p_start = cls._get_period_start(b.period_type)
            s_stmt = select(func.sum(UsageLedgerEntry.estimated_cost)).where(
                UsageLedgerEntry.company_id == company_id,
                UsageLedgerEntry.created_at >= p_start,
            )
            if b.ai_employee_id:
                s_stmt = s_stmt.where(UsageLedgerEntry.ai_employee_id == b.ai_employee_id)
            spent = (await session.execute(s_stmt)).scalar() or Decimal("0.000000")
            limit = Decimal(str(b.limit_amount))
            pct = round(float((Decimal(str(spent)) / limit) * Decimal("100")), 1) if limit > 0 else 0.0

            budgets_status.append({
                "id": str(b.id),
                "name": b.budget_name,
                "ai_employee_id": str(b.ai_employee_id) if b.ai_employee_id else None,
                "period": b.period_type,
                "limit_amount": float(limit),
                "current_spend": float(spent),
                "utilization_percent": pct,
                "soft_limit_percent": b.soft_limit_percent,
                "hard_limit_enabled": b.hard_limit_enabled,
                "exceeded": float(spent) >= float(limit),
            })

        return {
            "time_window_days": days,
            "requests_count": total_reqs,
            "total_tokens": total_tok,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "cached_tokens": cached_tok,
            "total_estimated_cost": float(total_cost),
            "currency": "USD",
            "by_model": by_model,
            "by_source": by_source,
            "budgets": budgets_status,
        }

    @classmethod
    async def create_budget(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
        budget_name: str,
        limit_amount: Decimal,
        period_type: str = "MONTHLY",
        soft_limit_percent: float = 80.0,
        hard_limit_enabled: bool = True,
        ai_employee_id: Optional[uuid.UUID] = None,
    ) -> UsageBudget:
        """Creates a budget policy with strict tenant ownership."""
        if limit_amount <= Decimal("0"):
            raise ValidationException("limit_amount must be greater than zero")

        budget = UsageBudget(
            company_id=company_id,
            ai_employee_id=ai_employee_id,
            budget_name=budget_name.strip(),
            limit_amount=limit_amount,
            currency="USD",
            period_type=period_type.upper().strip(),
            soft_limit_percent=soft_limit_percent,
            hard_limit_enabled=hard_limit_enabled,
            is_active=True,
        )
        session.add(budget)
        await session.flush()

        await AuditService.record_event(
            session=session,
            company_id=company_id,
            ai_employee_id=ai_employee_id,
            event_type="BUDGET_CREATED",
            resource_type="BUDGET",
            resource_id=str(budget.id),
            metadata={
                "name": budget_name,
                "limit": str(limit_amount),
                "period": period_type,
                "hard_limit": hard_limit_enabled,
            },
        )
        return budget

    @classmethod
    async def list_budgets(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
    ) -> List[UsageBudget]:
        """Lists all budgets for a tenant."""
        stmt = (
            select(UsageBudget)
            .where(UsageBudget.company_id == company_id)
            .order_by(desc(UsageBudget.created_at))
        )
        return list((await session.execute(stmt)).scalars().all())

    @classmethod
    async def delete_budget(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
        budget_id: uuid.UUID,
    ) -> bool:
        """Deletes a budget strictly enforcing tenant scope."""
        stmt = select(UsageBudget).where(
            UsageBudget.id == budget_id,
            UsageBudget.company_id == company_id,
        )
        budget = (await session.execute(stmt)).scalar_one_or_none()
        if not budget:
            raise NotFoundException("Budget not found")

        await session.delete(budget)
        await session.flush()

        await AuditService.record_event(
            session=session,
            company_id=company_id,
            ai_employee_id=budget.ai_employee_id,
            event_type="BUDGET_DELETED",
            resource_type="BUDGET",
            resource_id=str(budget_id),
            metadata={"name": budget.budget_name},
        )
        return True
