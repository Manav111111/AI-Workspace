import datetime
import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.observability import AuditEvent
from app.services.observability.redactor import TelemetryRedactor

logger = logging.getLogger("app.services.observability.audit")


class AuditService:
    """Provides append-only recording and querying of administrative, operational,
    and governance audit events with strict tenant isolation and secret redaction.
    """

    @classmethod
    async def record_event(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
        event_type: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        actor_id: Optional[uuid.UUID] = None,
        ai_employee_id: Optional[uuid.UUID] = None,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Appends an immutable audit event to the tenant audit trail."""
        safe_meta = TelemetryRedactor.redact_dict(metadata or {})

        event = AuditEvent(
            company_id=company_id,
            actor_id=actor_id,
            ai_employee_id=ai_employee_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            trace_id=trace_id,
            safe_metadata=safe_meta,
        )
        session.add(event)
        await session.flush()
        logger.info(
            f"AuditEvent: company={company_id} | event={event_type} | "
            f"res={resource_type}:{resource_id} | actor={actor_id}"
        )
        return event

    @classmethod
    async def list_events(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
        ai_employee_id: Optional[uuid.UUID] = None,
        event_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[AuditEvent]:
        """Lists audit events strictly scoped to the authenticated tenant."""
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.company_id == company_id)
            .order_by(desc(AuditEvent.created_at))
            .limit(limit)
            .offset(offset)
        )
        if ai_employee_id:
            stmt = stmt.where(AuditEvent.ai_employee_id == ai_employee_id)
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if resource_type:
            stmt = stmt.where(AuditEvent.resource_type == resource_type)

        res = await session.execute(stmt)
        return list(res.scalars().all())
