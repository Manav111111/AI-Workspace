from typing import List, Optional, Sequence
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ValidationException
from app.models.ai_employee import AIEmployee
from app.models.knowledge_base import KnowledgeBase
from app.repositories.ai_employee import AIEmployeeRepository
from app.schemas.ai_employee import AIEmployeeCreate, AIEmployeeUpdate


class AIEmployeeService:
    """Service layer for AI Employee business logic.
    Strictly tenant-scoped using the authenticated tenant's company_id.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AIEmployeeRepository(session)

    async def _resolve_and_validate_kbs(
        self, company_id: uuid.UUID, kb_ids: List[uuid.UUID]
    ) -> List[KnowledgeBase]:
        """Validates that all specified knowledge base IDs strictly belong to the company_id.
        TENANT BOUNDARY: Cross-tenant association attempts will raise ValidationException.
        """
        if not kb_ids:
            return []

        unique_ids = list(set(kb_ids))
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.id.in_(unique_ids),
            KnowledgeBase.company_id == company_id,
        )
        res = await self.session.execute(stmt)
        kbs = res.scalars().all()

        if len(kbs) != len(unique_ids):
            raise ValidationException(
                "One or more specified knowledge bases do not exist or belong to another company."
            )
        return list(kbs)

    async def create_employee(self, company_id: uuid.UUID, data: AIEmployeeCreate) -> AIEmployee:
        assigned_kbs = []
        if data.knowledge_base_ids:
            assigned_kbs = await self._resolve_and_validate_kbs(company_id, data.knowledge_base_ids)
        # Handle initial tool assignments
        assigned_tools_objs = []
        if getattr(data, "tools", None):
            from app.models.ai_employee_tool import AIEmployeeTool
            from app.services.agent.tool_registry import tool_registry
            registered = {t.name for t in tool_registry.list_available_tools()}
            valid_tools = [name for name in set(data.tools) if name in registered]
            assigned_tools_objs = [
                AIEmployeeTool(company_id=company_id, tool_name=t)
                for t in valid_tools
            ]

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
            knowledge_bases=assigned_kbs,
            assigned_tools=assigned_tools_objs,
        )
        created = await self.repo.create(employee)
        await self.session.commit()
        # Fetch with eager relationship loading
        return await self.get_employee(company_id=company_id, employee_id=created.id)

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
        # Handle knowledge base assignment update if specified
        if "knowledge_base_ids" in update_data:
            kb_ids = update_data.pop("knowledge_base_ids")
            if kb_ids is not None:
                employee.knowledge_bases = await self._resolve_and_validate_kbs(company_id, kb_ids)

        # Handle tool assignment update if specified
        if "tools" in update_data:
            tool_names = update_data.pop("tools")
            if tool_names is not None:
                from app.models.ai_employee_tool import AIEmployeeTool
                from app.services.agent.tool_registry import tool_registry
                registered = {t.name for t in tool_registry.list_available_tools()}
                valid_tools = [name for name in set(tool_names) if name in registered]
                employee.assigned_tools = [
                    AIEmployeeTool(company_id=company_id, tool_name=t)
                    for t in valid_tools
                ]

        for key, value in update_data.items():
            if value is not None:
                setattr(employee, key, value)

        await self.repo.update(employee)
        await self.session.commit()
        return await self.get_employee(company_id=company_id, employee_id=employee_id)

    async def assign_knowledge_bases(
        self,
        company_id: uuid.UUID,
        employee_id: uuid.UUID,
        kb_ids: List[uuid.UUID],
    ) -> AIEmployee:
        """Batch-updates the assigned knowledge bases for an AI Employee."""
        employee = await self.get_employee(company_id=company_id, employee_id=employee_id)
        employee.knowledge_bases = await self._resolve_and_validate_kbs(company_id, kb_ids)
        await self.session.commit()
        return await self.get_employee(company_id=company_id, employee_id=employee_id)

    async def delete_employee(self, company_id: uuid.UUID, employee_id: uuid.UUID) -> None:
        employee = await self.get_employee(company_id=company_id, employee_id=employee_id)
        await self.repo.delete(employee)
        await self.session.commit()
