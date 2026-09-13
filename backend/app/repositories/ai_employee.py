from typing import Optional, Sequence
import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_employee import AIEmployee
from app.repositories.base import BaseRepository


class AIEmployeeRepository(BaseRepository[AIEmployee]):
    """Tenant-scoped repository for AI Employee entities.
    All read/write operations strictly enforce company_id scoping.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(AIEmployee, session)

    async def get_by_tenant(self, company_id: uuid.UUID, employee_id: uuid.UUID) -> Optional[AIEmployee]:
        """Fetch an AI Employee strictly scoped to the specified tenant/company."""
        stmt = (
            select(AIEmployee)
            .options(selectinload(AIEmployee.knowledge_bases))
            .where(
                AIEmployee.id == employee_id,
                AIEmployee.company_id == company_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self,
        company_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[AIEmployee]:
        """List AI Employees strictly scoped to the specified tenant/company."""
        stmt = (
            select(AIEmployee)
            .options(selectinload(AIEmployee.knowledge_bases))
            .where(AIEmployee.company_id == company_id)
            .order_by(AIEmployee.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
