from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import TenantContext, get_tenant_context
from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.models.business_entities import Lead, Order, SupportTicket, ToolExecution
from app.models.pending_tool_action import PendingToolAction
from app.schemas.tool import (
    LeadResponse,
    OrderCreateRequest,
    OrderResponse,
    PendingActionResponse,
    SupportTicketResponse,
    ToolExecutionResponse,
)
from app.services.agent.tool_executor import ToolExecutor

router = APIRouter(tags=["Business Entities & Audit Logs"])


# ─── Orders ────────────────────────────────────────────────────────────────────

@router.get("/orders", response_model=List[OrderResponse], status_code=status.HTTP_200_OK)
async def list_orders(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[OrderResponse]:
    """Lists orders belonging to the active tenant company."""
    stmt = (
        select(Order)
        .where(Order.company_id == tenant.company_id)
        .order_by(desc(Order.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await session.execute(stmt)
    return [OrderResponse.model_validate(o) for o in res.scalars().all()]


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreateRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Creates a new order under the active tenant company (for demo / seeding purposes)."""
    order = Order(
        company_id=tenant.company_id,
        order_number=payload.order_number.strip().upper(),
        customer_identifier=payload.customer_identifier.strip().lower(),
        status=payload.status.strip().upper(),
        items=payload.items,
        total=payload.total,
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return OrderResponse.model_validate(order)


# ─── Leads ─────────────────────────────────────────────────────────────────────

@router.get("/leads", response_model=List[LeadResponse], status_code=status.HTTP_200_OK)
async def list_leads(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[LeadResponse]:
    """Lists sales leads captured by AI Employees for the active tenant company."""
    stmt = (
        select(Lead)
        .where(Lead.company_id == tenant.company_id)
        .order_by(desc(Lead.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await session.execute(stmt)
    return [LeadResponse.model_validate(l) for l in res.scalars().all()]


# ─── Support Tickets ───────────────────────────────────────────────────────────

@router.get("/support-tickets", response_model=List[SupportTicketResponse], status_code=status.HTTP_200_OK)
async def list_support_tickets(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[SupportTicketResponse]:
    """Lists customer support tickets created by AI Employees for the active tenant company."""
    stmt = (
        select(SupportTicket)
        .where(SupportTicket.company_id == tenant.company_id)
        .order_by(desc(SupportTicket.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await session.execute(stmt)
    return [SupportTicketResponse.model_validate(t) for t in res.scalars().all()]


# ─── Tool Execution Audit Logs ─────────────────────────────────────────────────

@router.get("/tool-executions", response_model=List[ToolExecutionResponse], status_code=status.HTTP_200_OK)
async def list_tool_executions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[ToolExecutionResponse]:
    """Lists audit logs of tool executions performed by AI Employees under this tenant."""
    stmt = (
        select(ToolExecution)
        .where(ToolExecution.company_id == tenant.company_id)
        .order_by(desc(ToolExecution.created_at))
        .limit(limit)
        .offset(offset)
    )
    res = await session.execute(stmt)
    return [ToolExecutionResponse.model_validate(te) for te in res.scalars().all()]


# ─── Pending Tool Actions ──────────────────────────────────────────────────────

@router.get("/pending-actions", response_model=List[PendingActionResponse], status_code=status.HTTP_200_OK)
async def list_pending_actions(
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[PendingActionResponse]:
    """Lists pending tool actions awaiting confirmation under this tenant."""
    stmt = (
        select(PendingToolAction)
        .where(PendingToolAction.company_id == tenant.company_id)
        .order_by(desc(PendingToolAction.created_at))
    )
    res = await session.execute(stmt)
    return [PendingActionResponse.model_validate(pa) for pa in res.scalars().all()]


@router.post("/pending-actions/{id}/confirm", status_code=status.HTTP_200_OK)
async def confirm_pending_action(
    id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
):
    """Executes a pending tool action after explicit user confirmation."""
    executor = ToolExecutor(session)
    result = await executor.execute_pending_action(
        pending_action_id=id,
        company_id=tenant.company_id,
        user_id=tenant.user_id,
    )
    await session.commit()
    return {
        "success": result.success,
        "data": result.data,
        "error": result.error,
        "message": result.display_message,
    }
