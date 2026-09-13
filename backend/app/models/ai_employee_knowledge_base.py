import datetime
from typing import Optional, TYPE_CHECKING
import uuid
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.ai_employee import AIEmployee
    from app.models.company import Company
    from app.models.knowledge_base import KnowledgeBase


class AIEmployeeKnowledgeBase(BaseModel):
    """Association model linking an AI Employee to an authorized Knowledge Base.
    SECURITY MANDATE:
    Both the AIEmployee and the KnowledgeBase must belong to the exact same company_id.
    """
    __tablename__ = "ai_employee_knowledge_bases"

    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    ai_employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "ai_employee_id",
            "knowledge_base_id",
            name="uq_ai_employee_knowledge_base",
        ),
    )
