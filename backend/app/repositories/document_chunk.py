from typing import Optional, Sequence
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document_chunk import DocumentChunk
from app.repositories.base import BaseRepository


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    """Tenant-scoped repository for DocumentChunk entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(DocumentChunk, session)

    async def list_by_document(
        self,
        company_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Sequence[DocumentChunk]:
        """Fetch all chunks for a document scoped to the specified tenant/company."""
        stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.company_id == company_id,
                DocumentChunk.document_id == document_id,
            )
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_document(
        self,
        company_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> int:
        """Delete all chunks for a document (used for idempotent reprocessing or document deletion)."""
        stmt = (
            delete(DocumentChunk)
            .where(
                DocumentChunk.company_id == company_id,
                DocumentChunk.document_id == document_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def list_by_knowledge_bases(
        self,
        company_id: uuid.UUID,
        knowledge_base_ids: Optional[Sequence[uuid.UUID]] = None,
        limit: Optional[int] = None,
    ) -> Sequence[DocumentChunk]:
        """Fetch all chunks for a tenant, optionally filtered to a list of knowledge base IDs."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.company_id == company_id)
        )
        if knowledge_base_ids:
            stmt = stmt.where(DocumentChunk.knowledge_base_id.in_(knowledge_base_ids))

        stmt = stmt.order_by(DocumentChunk.created_at.asc())
        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return result.scalars().all()

