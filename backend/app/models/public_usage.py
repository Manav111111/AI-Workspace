import datetime
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class PublicUsageEvent(BaseModel):
    """Persisted usage & audit event for public runtime sessions.
    Tracks token consumption, latencies, message counts, and tool invocations.
    Serves as foundational telemetry for customer analytics and future billing.
    """
    __tablename__ = "public_usage_events"

    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ai_employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("public_chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # e.g., "MESSAGE", "TOOL_CALL", "CONFIRMATION"
    message_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    tool_call_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    input_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    latency_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    # Relationships
    company = relationship("Company")
    ai_employee = relationship("AIEmployee")
    session = relationship("PublicChatSession")
