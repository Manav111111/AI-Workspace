from typing import Any, Dict, List
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_tenant_context, require_roles, TenantContext
from app.db.session import get_db
from app.models.membership import MembershipRole
from app.models.user import User
from app.schemas.company import (
    CompanyCreate,
    CompanyRead,
    MembershipCreate,
    MembershipRead,
)
from app.services.company import CompanyService

router = APIRouter(prefix="/companies", tags=["Companies & Workspaces"])


@router.post("/", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(
    data: CompanyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CompanyRead:
    """Create a new company workspace. The creator is automatically assigned as OWNER."""
    company_service = CompanyService(session)
    company = await company_service.create_company(user=current_user, data=data)
    return CompanyRead.model_validate(company)


@router.get("/", response_model=List[MembershipRead])
async def list_user_companies(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[MembershipRead]:
    """List all companies the authenticated user belongs to."""
    company_service = CompanyService(session)
    memberships = await company_service.get_user_companies(current_user.id)
    return [MembershipRead.model_validate(m) for m in memberships]


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(
    tenant: TenantContext = Depends(get_tenant_context),
) -> CompanyRead:
    """Get details of a specific company. Accessible only by authorized company members."""
    return CompanyRead.model_validate(tenant.company)


@router.post("/{company_id}/members", response_model=MembershipRead, status_code=status.HTTP_201_CREATED)
async def add_company_member(
    data: MembershipCreate,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> MembershipRead:
    """Invite/add a user to the company workspace. Requires OWNER or ADMIN role."""
    company_service = CompanyService(session)
    membership = await company_service.add_member(
        actor_user=tenant.user,
        company_id=tenant.company_id,
        data=data,
    )
    return MembershipRead.model_validate(membership)
