import enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid
from sqlalchemy import Boolean, Enum, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.conversation import Conversation
    from app.models.knowledge_base import KnowledgeBase


class AIEmployeeStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class AIEmployee(BaseModel):
    __tablename__ = "ai_employees"

    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personality: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    status: Mapped[AIEmployeeStatus] = mapped_column(
        Enum(AIEmployeeStatus, native_enum=False, length=50),
        default=AIEmployeeStatus.DRAFT,
        nullable=False,
    )
    # Phase 4: Public AI Employee Runtime & Widget Configuration
    public_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    allowed_domains: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    widget_config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Extensibility for Future Avatar and Voice configuration
    avatar_config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    voice_config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    company: Mapped["Company"] = relationship("Company", back_populates="ai_employees")
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="ai_employee",
        cascade="all, delete-orphan",
    )
    knowledge_bases: Mapped[List["KnowledgeBase"]] = relationship(
        "KnowledgeBase",
        secondary="ai_employee_knowledge_bases",
        back_populates="ai_employees",
        lazy="selectin",
    )
    assigned_tools = relationship(
        "AIEmployeeTool",
        back_populates="ai_employee",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
