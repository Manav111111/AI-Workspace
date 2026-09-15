import datetime
import enum
from typing import Optional
import uuid
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class VoiceSessionStatus(str, enum.Enum):
    CONNECTING = "CONNECTING"
    ACTIVE = "ACTIVE"
    INTERRUPTED = "INTERRUPTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class VoiceSession(BaseModel):
    """Voice Session lifecycle and telemetry record.
    Tracks audio usage, latencies, tokens, and interruptions for monitoring and Phase 8 billing.
    """
    __tablename__ = "voice_sessions"

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
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    public_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("public_chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[VoiceSessionStatus] = mapped_column(
        Enum(VoiceSessionStatus, native_enum=False, length=50),
        default=VoiceSessionStatus.CONNECTING,
        nullable=False,
    )

    # Audio & Request Usage Telemetry
    input_audio_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    output_audio_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    stt_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tts_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Latency Metrics (ms)
    time_to_first_transcript_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_to_first_audio_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Barge-In count
    interruptions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Lifecycle Timestamps
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    ended_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    company = relationship("Company")
    ai_employee = relationship("AIEmployee")
    conversation = relationship("Conversation")
    public_session = relationship("PublicChatSession")
