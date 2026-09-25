from datetime import datetime
import enum
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.knowledge_base import KnowledgeBase
    from app.models.document import Document


class IngestionJobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class IngestionStage(str, enum.Enum):
    QUEUED = "QUEUED"
    PARSING = "PARSING"
    CLEANING = "CLEANING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    VECTOR_UPSERT = "VECTOR_UPSERT"
    INDEX_UPDATE = "INDEX_UPDATE"
    COMPLETED = "COMPLETED"


class IngestionJob(BaseModel):
    __tablename__ = "ingestion_jobs"

    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[IngestionJobStatus] = mapped_column(
        Enum(IngestionJobStatus, native_enum=False, length=50),
        default=IngestionJobStatus.QUEUED,
        nullable=False,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_stage: Mapped[str] = mapped_column(
        String(50),
        default=IngestionStage.QUEUED.value,
        nullable=False,
    )

    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship("Company")
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase")
    document: Mapped["Document"] = relationship("Document")
