from typing import Optional, Sequence
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException
from app.models.knowledge_base import KnowledgeBase
from app.repositories.knowledge_base import KnowledgeBaseRepository
from app.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate
from app.services.qdrant_service import QdrantService


class KnowledgeBaseService:
    def __init__(self, session: AsyncSession, qdrant_service: Optional[QdrantService] = None):
        self.session = session
        self.repo = KnowledgeBaseRepository(session)
        self.qdrant = qdrant_service or QdrantService()

    async def create_knowledge_base(
        self,
        company_id: uuid.UUID,
        data: KnowledgeBaseCreate,
    ) -> KnowledgeBase:
        kb = KnowledgeBase(
            company_id=company_id,
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            status=data.status,
        )
        created = await self.repo.create(kb)
        await self.session.commit()
        await self.session.refresh(created)
        return created

    async def get_knowledge_base(
        self,
        company_id: uuid.UUID,
        kb_id: uuid.UUID,
    ) -> KnowledgeBase:
        kb = await self.repo.get_by_tenant(company_id=company_id, kb_id=kb_id)
        if not kb:
            raise NotFoundException("Knowledge Base not found in this company")
        return kb

    async def list_knowledge_bases(
        self,
        company_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[KnowledgeBase]:
        return await self.repo.list_by_tenant(company_id=company_id, skip=skip, limit=limit)

    async def update_knowledge_base(
        self,
        company_id: uuid.UUID,
        kb_id: uuid.UUID,
        data: KnowledgeBaseUpdate,
    ) -> KnowledgeBase:
        kb = await self.get_knowledge_base(company_id=company_id, kb_id=kb_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(kb, key, value)

        updated = await self.repo.update(kb)
        await self.session.commit()
        await self.session.refresh(updated)
        return updated

    async def delete_knowledge_base(
        self,
        company_id: uuid.UUID,
        kb_id: uuid.UUID,
    ) -> None:
        kb = await self.get_knowledge_base(company_id=company_id, kb_id=kb_id)
        # Delete Qdrant vectors associated with this KB
        self.qdrant.delete_knowledge_base_vectors(company_id=company_id, knowledge_base_id=kb.id)
        await self.repo.delete(kb)
        await self.session.commit()
