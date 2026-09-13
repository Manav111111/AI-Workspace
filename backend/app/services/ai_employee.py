from typing import List, Optional, Sequence
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException
from app.models.ai_employee import AIEmployee
from app.repositories.ai_employee import AIEmployeeRepository
from app.schemas.ai_employee import AIEmployeeCreate, AIEmployeeUpdate


class AIEmployeeService:
    """Service layer for AI Employee business logic.
    Strictly tenant-scoped using the authenticated tenant's company_id.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AIEmployeeRepository(session)

    async def create_employee(self, company_id: uuid.UUID, data: AIEmployeeCreate) -> AIEmployee:
        employee = AIEmployee(
            company_id=company_id,
            name=data.name.strip(),
            role=data.role.strip(),
            description=data.description.strip() if data.description else None,
            personality=data.personality.strip() if data.personality else None,
            system_prompt=data.system_prompt.strip() if data.system_prompt else None,
            language=data.language or "en",
            status=data.status,
            avatar_config=data.avatar_config or {},
            voice_config=data.voice_config or {},
        )
        created = await self.repo.create(employee)
        await self.session.commit()
        await self.session.refresh(created)
        return created

    async def get_employee(self, company_id: uuid.UUID, employee_id: uuid.UUID) -> AIEmployee:
        employee = await self.repo.get_by_tenant(company_id=company_id, employee_id=employee_id)
        if not employee:
            raise NotFoundException("AI Employee not found in this company")
        return employee

    async def list_employees(
        self,
        company_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[AIEmployee]:
        return await self.repo.list_by_tenant(company_id=company_id, skip=skip, limit=limit)

    async def update_employee(
        self,
        company_id: uuid.UUID,
        employee_id: uuid.UUID,
        data: AIEmployeeUpdate,
    ) -> AIEmployee:
        employee = await self.get_employee(company_id=company_id, employee_id=employee_id)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(employee, key, value)

        updated = await self.repo.update(employee)
        await self.session.commit()
        await self.session.refresh(updated)
        return updated

    async def delete_employee(self, company_id: uuid.UUID, employee_id: uuid.UUID) -> None:
        employee = await self.get_employee(company_id=company_id, employee_id=employee_id)
        await self.repo.delete(employee)
        await self.session.commit()
