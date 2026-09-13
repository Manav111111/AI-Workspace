from typing import Optional, Sequence
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Tenant-scoped repository for Document entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)

    async def get_by_tenant(
        self,
        company_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Optional[Document]:
        """Fetch a Document strictly scoped to the specified tenant/company."""
        stmt = select(Document).where(
            Document.id == document_id,
            Document.company_id == company_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_knowledge_base(
        self,
        company_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Document]:
        """List Documents in a Knowledge Base strictly scoped to the tenant/company."""
        stmt = (
            select(Document)
            .where(
                Document.company_id == company_id,
                Document.knowledge_base_id == knowledge_base_id,
            )
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
