from typing import TYPE_CHECKING, Any, Dict
import uuid
from sqlalchemy import ForeignKey, Integer, JSON, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.document import Document


class DocumentChunk(BaseModel):
    __tablename__ = "document_chunks"

    # Explicit tenant boundary on every chunk
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
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
