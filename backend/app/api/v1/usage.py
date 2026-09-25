import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import TenantContext, get_db, get_tenant_context
from app.models.usage_budget import UsageBudget, UsageLedgerEntry
from app.services.billing.budget_service import BudgetService

router = APIRouter(tags=["Usage Metering & Budget Governance"])


class UsageLedgerResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    ai_employee_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    trace_id: Optional[str] = None
    provider: str
    model: str
    operation_type: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    total_tokens: int
    estimated_cost: float
    currency: str
    cost_status: str
    usage_source: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetCreateRequest(BaseModel):
    budget_name: str = Field(..., max_length=100)
    limit_amount: Decimal = Field(..., gt=0)
    period_type: str = Field(default="MONTHLY")  # MONTHLY, WEEKLY, DAILY
    soft_limit_percent: float = Field(default=80.0, ge=1.0, le=100.0)
    hard_limit_enabled: bool = Field(default=True)
    ai_employee_id: Optional[uuid.UUID] = None


class BudgetResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    ai_employee_id: Optional[uuid.UUID] = None
    budget_name: str
    limit_amount: float
    currency: str
    period_type: str
    soft_limit_percent: float
    hard_limit_enabled: bool
    is_active: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("/usage/summary")
async def get_usage_summary(
    ai_employee_id: Optional[uuid.UUID] = Query(None),
    days: int = Query(30, ge=1, le=365),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves operational token usage, estimated costs, and budget health."""
    return await BudgetService.get_usage_summary(
        session=session,
        company_id=tenant.company_id,
        ai_employee_id=ai_employee_id,
        days=days,
    )


@router.get("/usage/ledger", response_model=List[UsageLedgerResponse])
async def list_usage_ledger(
    ai_employee_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[UsageLedgerResponse]:
    """Retrieves authoritative usage ledger entries strictly for the active tenant."""
    stmt = (
        select(UsageLedgerEntry)
        .where(UsageLedgerEntry.company_id == tenant.company_id)
        .order_by(desc(UsageLedgerEntry.created_at))
        .limit(limit)
        .offset(offset)
    )
    if ai_employee_id:
        stmt = stmt.where(UsageLedgerEntry.ai_employee_id == ai_employee_id)

    res = await session.execute(stmt)
    records = res.scalars().all()
    # Map decimal cost to float for JSON response
    output = []
    for r in records:
        entry_dict = {
            "id": r.id,
            "company_id": r.company_id,
            "ai_employee_id": r.ai_employee_id,
            "conversation_id": r.conversation_id,
            "trace_id": r.trace_id,
            "provider": r.provider,
            "model": r.model,
            "operation_type": r.operation_type,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "cached_tokens": r.cached_tokens,
            "total_tokens": r.total_tokens,
            "estimated_cost": float(r.estimated_cost),
            "currency": r.currency,
            "cost_status": r.cost_status,
            "usage_source": r.usage_source,
            "created_at": r.created_at,
        }
        output.append(UsageLedgerResponse.model_validate(entry_dict))
    return output


@router.get("/budgets", response_model=List[BudgetResponse])
async def list_budgets(
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[BudgetResponse]:
    """Lists budget governance policies for the active tenant."""
    budgets = await BudgetService.list_budgets(session=session, company_id=tenant.company_id)
    return [
        BudgetResponse(
            id=b.id,
            company_id=b.company_id,
            ai_employee_id=b.ai_employee_id,
            budget_name=b.budget_name,
            limit_amount=float(b.limit_amount),
            currency=b.currency,
            period_type=b.period_type,
            soft_limit_percent=b.soft_limit_percent,
            hard_limit_enabled=b.hard_limit_enabled,
            is_active=b.is_active,
            created_at=b.created_at,
        )
        for b in budgets
    ]


@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreateRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> BudgetResponse:
    """Creates a new spend budget policy with soft warning thresholds and hard limits."""
    b = await BudgetService.create_budget(
        session=session,
        company_id=tenant.company_id,
        budget_name=payload.budget_name,
        limit_amount=payload.limit_amount,
        period_type=payload.period_type,
        soft_limit_percent=payload.soft_limit_percent,
        hard_limit_enabled=payload.hard_limit_enabled,
        ai_employee_id=payload.ai_employee_id,
    )
    return BudgetResponse(
        id=b.id,
        company_id=b.company_id,
        ai_employee_id=b.ai_employee_id,
        budget_name=b.budget_name,
        limit_amount=float(b.limit_amount),
        currency=b.currency,
        period_type=b.period_type,
        soft_limit_percent=b.soft_limit_percent,
        hard_limit_enabled=b.hard_limit_enabled,
        is_active=b.is_active,
        created_at=b.created_at,
    )


@router.delete("/budgets/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Deletes a budget policy, strictly verifying tenant ownership."""
    await BudgetService.delete_budget(
        session=session,
        company_id=tenant.company_id,
        budget_id=id,
    )
