import enum
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.document import Document


class KnowledgeBaseStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class KnowledgeBase(BaseModel):
    __tablename__ = "knowledge_bases"

    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[KnowledgeBaseStatus] = mapped_column(
        Enum(KnowledgeBaseStatus, native_enum=False, length=50),
        default=KnowledgeBaseStatus.ACTIVE,
        nullable=False,
    )

    company: Mapped["Company"] = relationship("Company", back_populates="knowledge_bases")
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
    )
