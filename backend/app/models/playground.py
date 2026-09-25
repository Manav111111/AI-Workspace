from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import JSON, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class PlaygroundSession(BaseModel):
    """Tenant-isolated testing and debugging session for an AI Employee.
    Holds an immutable or working configuration snapshot to test prompt modifications,
    retrieval parameters, and tool execution without altering production state.
    """
    __tablename__ = "playground_sessions"

    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ai_employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Playground Session",
    )
    # Configuration snapshot (system_prompt, personality, temperature, top_k, retrieval_mode, model, assigned_kb_ids, assigned_tools)
    config_snapshot: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="ACTIVE",
        nullable=False,
        index=True,
    )

    # Relationships
    company = relationship("Company")
    user = relationship("User")
    ai_employee = relationship("AIEmployee")
    messages: Mapped[List["PlaygroundMessage"]] = relationship(
        "PlaygroundMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="PlaygroundMessage.created_at",
        lazy="selectin",
    )


class PlaygroundMessage(BaseModel):
    """Message exchanged in a Playground session with rich debugging context."""
    __tablename__ = "playground_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("playground_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )  # "user", "assistant", "system"
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    citations: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    # Granular retrieval debug data: chunk_id, scores (dense, sparse, rrf, rerank), previews
    retrieval_debug: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    # Granular prompt structure debug: system, persona, context, history, user query
    prompt_debug: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    trace_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    metrics: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    session = relationship("PlaygroundSession", back_populates="messages")
