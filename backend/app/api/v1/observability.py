import datetime
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import TenantContext, get_db, get_tenant_context
from app.core.exceptions import NotFoundException
from app.models.observability import AuditEvent, TraceSummary
from app.services.observability.audit_service import AuditService
from app.services.observability.metrics import metrics_collector

router = APIRouter(prefix="/observability", tags=["Observability & Telemetry"])


class TraceSummaryResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    ai_employee_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    trace_id: str
    request_type: str
    status: str
    total_latency_ms: float
    spans_count: int
    spans_data: List[Dict[str, Any]]
    safe_metadata: Dict[str, Any]
    error_message: Optional[str] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    ai_employee_id: Optional[uuid.UUID] = None
    event_type: str
    resource_type: str
    resource_id: Optional[str] = None
    trace_id: Optional[str] = None
    safe_metadata: Dict[str, Any]
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


@router.get("/traces", response_model=List[TraceSummaryResponse])
async def list_traces(
    ai_employee_id: Optional[uuid.UUID] = Query(None),
    request_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[TraceSummaryResponse]:
    """Lists end-to-end request traces strictly scoped to the active tenant."""
    stmt = (
        select(TraceSummary)
        .where(TraceSummary.company_id == tenant.company_id)
        .order_by(desc(TraceSummary.created_at))
        .limit(limit)
        .offset(offset)
    )
    if ai_employee_id:
        stmt = stmt.where(TraceSummary.ai_employee_id == ai_employee_id)
    if request_type:
        stmt = stmt.where(TraceSummary.request_type == request_type.upper().strip())
    if status_filter:
        stmt = stmt.where(TraceSummary.status == status_filter.upper().strip())

    res = await session.execute(stmt)
    records = res.scalars().all()
    return [TraceSummaryResponse.model_validate(r) for r in records]


@router.get("/traces/{trace_id}", response_model=TraceSummaryResponse)
async def get_trace(
    trace_id: str,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> TraceSummaryResponse:
    """Retrieves detailed trace span tree and metadata with strict tenant isolation."""
    stmt = select(TraceSummary).where(
        TraceSummary.trace_id == trace_id,
        TraceSummary.company_id == tenant.company_id,
    )
    res = await session.execute(stmt)
    trace = res.scalar_one_or_none()
    if not trace:
        raise NotFoundException("Trace not found")

    return TraceSummaryResponse.model_validate(trace)


@router.get("/metrics/summary")
async def get_metrics_summary(
    tenant: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Retrieves operational latency percentiles and throughput metrics."""
    return metrics_collector.get_summary()


@router.get("/audit-logs", response_model=List[AuditEventResponse])
async def list_audit_logs(
    ai_employee_id: Optional[uuid.UUID] = Query(None),
    event_type: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[AuditEventResponse]:
    """Retrieves immutable audit trail events strictly for the active tenant."""
    events = await AuditService.list_events(
        session=session,
        company_id=tenant.company_id,
        ai_employee_id=ai_employee_id,
        event_type=event_type,
        resource_type=resource_type,
        limit=limit,
        offset=offset,
    )
    return [AuditEventResponse.model_validate(e) for e in events]
