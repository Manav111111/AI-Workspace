import datetime
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class TraceSummary(BaseModel):
    """Persisted trace summary for multi-tenant AI Employee request execution.
    Captures end-to-end request latency, span hierarchy, and operational metadata
    with strict tenant isolation and secret redaction.
    """
    __tablename__ = "trace_summaries"

    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ai_employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("ai_employees.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        nullable=True,
        index=True,
    )
    trace_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    request_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="CHAT",
        index=True,
    )  # e.g., "CHAT", "PLAYGROUND", "PUBLIC_CHAT", "EVALUATION"
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="SUCCESS",
        index=True,
    )  # "SUCCESS", "ERROR"
    total_latency_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    spans_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    # Serialized span trees (redacted)
    spans_data: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    # Redacted high-level execution attributes and metrics
    safe_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    company = relationship("Company")
    ai_employee = relationship("AIEmployee")


class AuditEvent(BaseModel):
    """Append-only audit trail logging important AI Employee, configuration, tool, and budget actions.
    Enforces tenant boundaries and prevents cross-tenant access.
    """
    __tablename__ = "audit_events"

    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        nullable=True,
        index=True,
    )  # User ID or None for system
    ai_employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("ai_employees.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )  # e.g., "AI_EMPLOYEE_UPDATED", "BUDGET_CREATED", "BUDGET_EXCEEDED", "TOOL_EXECUTED"
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # e.g., "AI_EMPLOYEE", "KNOWLEDGE_BASE", "BUDGET", "TOOL"
    resource_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    trace_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    safe_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    company = relationship("Company")
    ai_employee = relationship("AIEmployee")
