import enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid
from sqlalchemy import Enum, ForeignKey, JSON, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class MessageRole(str, enum.Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"


class Message(BaseModel):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, native_enum=False, length=20),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    message_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
