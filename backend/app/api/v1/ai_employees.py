from typing import List, Optional
import uuid
from fastapi import APIRouter, Body, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_tenant_context, require_roles, TenantContext
from app.core.config import settings
from app.db.session import get_db
from app.models.membership import MembershipRole
from app.schemas.ai_employee import (
    AIEmployeeCreate,
    AIEmployeeRead,
    AIEmployeeUpdate,
    KnowledgeBaseSummary,
)
from app.schemas.public_runtime import (
    EmployeeEmbedCodeResponse,
    EmployeePublishRequest,
    EmployeeWidgetConfigRequest,
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


# Phase 4: Publishing & Widget Embed APIs
@router.post("/{employee_id}/publish", response_model=AIEmployeeRead)
async def publish_ai_employee(
    employee_id: uuid.UUID,
    payload: Optional[EmployeePublishRequest] = None,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> AIEmployeeRead:
    """Publishes an AI Employee, generating a cryptographic public_id and making it accessible via public widget."""
    import secrets
    service = AIEmployeeService(session)
    emp = await service.get_employee(company_id=tenant.company_id, employee_id=employee_id)

    if not emp.public_id:
        emp.public_id = f"ae_pub_{secrets.token_hex(16)}"

    emp.is_published = True if payload is None else payload.is_published
    if payload and payload.allowed_domains is not None:
        emp.allowed_domains = payload.allowed_domains

    session.add(emp)
    await session.commit()
    await session.refresh(emp, attribute_names=["knowledge_bases", "assigned_tools"])
    return AIEmployeeRead.from_orm_employee(emp)


@router.post("/{employee_id}/unpublish", response_model=AIEmployeeRead)
async def unpublish_ai_employee(
    employee_id: uuid.UUID,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> AIEmployeeRead:
    """Unpublishes an AI Employee, immediately disabling public widget runtime access."""
    service = AIEmployeeService(session)
    emp = await service.get_employee(company_id=tenant.company_id, employee_id=employee_id)
    emp.is_published = False
    session.add(emp)
    await session.commit()
    await session.refresh(emp, attribute_names=["knowledge_bases", "assigned_tools"])
    return AIEmployeeRead.from_orm_employee(emp)


@router.get("/{employee_id}/embed", response_model=EmployeeEmbedCodeResponse)
async def get_ai_employee_embed(
    employee_id: uuid.UUID,
    request: Request,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> EmployeeEmbedCodeResponse:
    """Returns the standalone embed snippet and preview configuration for the AI Employee."""
    import secrets
    service = AIEmployeeService(session)
    emp = await service.get_employee(company_id=tenant.company_id, employee_id=employee_id)

    # Auto-generate public_id if not present
    if not emp.public_id:
        emp.public_id = f"ae_pub_{secrets.token_hex(16)}"
        session.add(emp)
        await session.commit()
        await session.refresh(emp)

    # Determine backend origin for API requests
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost:8000"
    api_url = f"{scheme}://{host}{settings.API_V1_STR}"

    # Determine frontend origin for widget.js and preview
    frontend_origin = settings.BACKEND_CORS_ORIGINS[0] if (settings.BACKEND_CORS_ORIGINS and isinstance(settings.BACKEND_CORS_ORIGINS, list)) else "http://localhost:3000"
    widget_url = f"{frontend_origin}/widget.js"
    preview_url = f"{frontend_origin}/preview/{emp.public_id}"

    snippet = (
        f'<script\n'
        f'  src="{widget_url}"\n'
        f'  data-ai-employee="{emp.public_id}"\n'
        f'  data-api-base="{api_url}"\n'
        f'  defer>\n'
        f'</script>'
    )

    return EmployeeEmbedCodeResponse(
        public_id=emp.public_id,
        is_published=emp.is_published,
        widget_script_url=widget_url,
        embed_snippet=snippet,
        preview_url=preview_url,
        allowed_domains=emp.allowed_domains or [],
        widget_config=emp.widget_config or {},
    )



@router.put("/{employee_id}/widget-config", response_model=AIEmployeeRead)
async def update_ai_employee_widget_config(
    employee_id: uuid.UUID,
    config: EmployeeWidgetConfigRequest,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> AIEmployeeRead:
    """Updates branding, theme, position, and allowed domains for the embeddable widget."""
    service = AIEmployeeService(session)
    emp = await service.get_employee(company_id=tenant.company_id, employee_id=employee_id)

    current_config = dict(emp.widget_config or {})
    if config.primary_color:
        current_config["primary_color"] = config.primary_color
    if config.theme:
        current_config["theme"] = config.theme
    if config.position:
        current_config["position"] = config.position
    if config.brand_name:
        current_config["brand_name"] = config.brand_name
    if config.welcome_message:
        current_config["welcome_message"] = config.welcome_message
    if config.logo_url:
        current_config["logo_url"] = config.logo_url

    emp.widget_config = current_config
    if config.allowed_domains is not None:
        emp.allowed_domains = config.allowed_domains

    session.add(emp)
    await session.commit()
    await session.refresh(emp, attribute_names=["knowledge_bases", "assigned_tools"])
    return AIEmployeeRead.from_orm_employee(emp)

