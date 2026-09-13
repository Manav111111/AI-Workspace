from typing import Optional, Sequence
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.knowledge_base import KnowledgeBase
from app.repositories.base import BaseRepository


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    """Tenant-scoped repository for KnowledgeBase entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(KnowledgeBase, session)

    async def get_by_tenant(
        self,
        company_id: uuid.UUID,
        kb_id: uuid.UUID,
    ) -> Optional[KnowledgeBase]:
        """Fetch a Knowledge Base strictly scoped to the specified tenant/company."""
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.company_id == company_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        company_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[KnowledgeBase]:
        """List Knowledge Bases strictly scoped to the specified tenant/company."""
        stmt = (
            select(KnowledgeBase)
            .where(KnowledgeBase.company_id == company_id)
            .order_by(KnowledgeBase.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
