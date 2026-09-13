from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid
from sqlalchemy import Boolean, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.ai_employee import AIEmployee
    from app.models.company import Company
    from app.models.message import Message
    from app.models.user import User


class Conversation(BaseModel):
    __tablename__ = "conversations"

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
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), default="New Conversation", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    conversation_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    company: Mapped["Company"] = relationship("Company", back_populates="conversations")
    ai_employee: Mapped["AIEmployee"] = relationship("AIEmployee", back_populates="conversations")
    user: Mapped[Optional["User"]] = relationship("User")
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
