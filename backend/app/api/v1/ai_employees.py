from typing import List
import uuid
from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_tenant_context, require_roles, TenantContext
from app.db.session import get_db
from app.models.membership import MembershipRole
from app.schemas.ai_employee import (
    AIEmployeeCreate,
    AIEmployeeRead,
    AIEmployeeUpdate,
    KnowledgeBaseSummary,
)
from app.services.ai_employee import AIEmployeeService

router = APIRouter(prefix="/ai-employees", tags=["AI Employees"])


@router.post("/", response_model=AIEmployeeRead, status_code=status.HTTP_201_CREATED)
async def create_ai_employee(
    data: AIEmployeeCreate,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> AIEmployeeRead:
    """Create a new AI Employee within the authenticated tenant company.
    Requires OWNER or ADMIN role in the company.
    """
    service = AIEmployeeService(session)
    employee = await service.create_employee(company_id=tenant.company_id, data=data)
    return AIEmployeeRead.from_orm_employee(employee)


@router.get("/", response_model=List[AIEmployeeRead])
async def list_ai_employees(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[AIEmployeeRead]:
    """List AI Employees strictly belonging to the caller's authorized company."""
    service = AIEmployeeService(session)
    employees = await service.list_employees(company_id=tenant.company_id, skip=skip, limit=limit)
    return [AIEmployeeRead.from_orm_employee(e) for e in employees]


@router.get("/{employee_id}", response_model=AIEmployeeRead)
async def get_ai_employee(
    employee_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> AIEmployeeRead:
    """Get a specific AI Employee. Cross-tenant access is strictly denied."""
    service = AIEmployeeService(session)
    employee = await service.get_employee(company_id=tenant.company_id, employee_id=employee_id)
    return AIEmployeeRead.from_orm_employee(employee)


@router.patch("/{employee_id}", response_model=AIEmployeeRead)
async def update_ai_employee(
    employee_id: uuid.UUID,
    data: AIEmployeeUpdate,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> AIEmployeeRead:
    """Update AI Employee details, prompt, personality, or knowledge base assignments."""
    service = AIEmployeeService(session)
    employee = await service.update_employee(
        company_id=tenant.company_id,
        employee_id=employee_id,
        data=data,
    )
    return AIEmployeeRead.from_orm_employee(employee)


@router.put("/{employee_id}/knowledge-bases", response_model=AIEmployeeRead)
async def assign_knowledge_bases(
    employee_id: uuid.UUID,
    knowledge_base_ids: List[uuid.UUID] = Body(..., embed=True),
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> AIEmployeeRead:
    """Batch-updates the assigned knowledge bases for an AI Employee."""
    service = AIEmployeeService(session)
    employee = await service.assign_knowledge_bases(
        company_id=tenant.company_id,
        employee_id=employee_id,
        kb_ids=knowledge_base_ids,
    )
    return AIEmployeeRead.from_orm_employee(employee)


@router.get("/{employee_id}/knowledge-bases", response_model=List[KnowledgeBaseSummary])
async def get_assigned_knowledge_bases(
    employee_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[KnowledgeBaseSummary]:
    """Get the list of knowledge bases assigned to an AI Employee."""
    service = AIEmployeeService(session)
    employee = await service.get_employee(company_id=tenant.company_id, employee_id=employee_id)
    return [
        KnowledgeBaseSummary(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            status=kb.status.value if hasattr(kb.status, "value") else str(kb.status),
        )
        for kb in (employee.knowledge_bases or [])
    ]


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_employee(
    employee_id: uuid.UUID,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete an AI Employee within the company."""
    service = AIEmployeeService(session)
    await service.delete_employee(company_id=tenant.company_id, employee_id=employee_id)
