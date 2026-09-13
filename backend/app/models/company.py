from typing import TYPE_CHECKING, List
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.membership import Membership
    from app.models.ai_employee import AIEmployee
    from app.models.knowledge_base import KnowledgeBase
    from app.models.conversation import Conversation


class Company(BaseModel):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    memberships: Mapped[List["Membership"]] = relationship(
        "Membership",
        back_populates="company",
        cascade="all, delete-orphan",
    )
    ai_employees: Mapped[List["AIEmployee"]] = relationship(
        "AIEmployee",
        back_populates="company",
        cascade="all, delete-orphan",
    )
    knowledge_bases: Mapped[List["KnowledgeBase"]] = relationship(
        "KnowledgeBase",
        back_populates="company",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="company",
        cascade="all, delete-orphan",
    )
