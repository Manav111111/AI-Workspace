from dataclasses import dataclass
from typing import Callable, List, Optional
import uuid
from fastapi import Depends, Header, Path, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ForbiddenException, NotFoundException, UnauthorizedException
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.company import Company
from app.models.membership import Membership, MembershipRole
from app.models.user import User
from app.repositories.company import CompanyRepository
from app.repositories.user import UserRepository

security_scheme = HTTPBearer(auto_error=False)


@dataclass
class TenantContext:
    """Security context representing the authenticated user within an authorized tenant."""
    user: User
    company: Company
    membership: Membership

    @property
    def company_id(self) -> uuid.UUID:
        return self.company.id

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id

    @property
    def role(self) -> MembershipRole:
        return self.membership.role


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Validates JWT bearer token and resolves the authenticated user."""
    if not credentials or not credentials.credentials:
        raise UnauthorizedException("Authentication token is required")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except Exception:
        raise UnauthorizedException("Invalid or expired authentication token")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Malformed token payload")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException("Invalid user ID in token")

    user_repo = UserRepository(session)
    user = await user_repo.get(user_uuid)
    if not user:
        raise UnauthorizedException("User not found")

    if not user.is_active:
        raise UnauthorizedException("User account is inactive")

    return user


async def get_tenant_context(
    company_id: Optional[uuid.UUID] = None,
    x_company_id: Optional[str] = Header(None, alias="X-Company-ID"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TenantContext:
    """Enforces multi-tenant authorization boundary.
    Resolves target company from Path or Header, verifying the user's membership.
    NEVER trusts unverified company_id from clients.
    """
    resolved_id: Optional[uuid.UUID] = None

    if company_id:
        resolved_id = company_id
    elif x_company_id:
        try:
            resolved_id = uuid.UUID(x_company_id)
        except ValueError:
            raise ForbiddenException("Invalid X-Company-ID header format")

    company_repo = CompanyRepository(session)

    if not resolved_id:
        # If no explicit company specified, default to user's first active company membership
        memberships = await company_repo.get_user_memberships(current_user.id)
        if not memberships:
            raise ForbiddenException("User does not belong to any active company")
        membership = memberships[0]
        company = membership.company
        return TenantContext(user=current_user, company=company, membership=membership)

    # Validate that current_user has a valid membership in target resolved_id
    membership = await company_repo.get_membership(
        user_id=current_user.id,
        company_id=resolved_id,
    )
    if not membership:
        raise ForbiddenException("Access denied: You do not have membership in this company")

    company = membership.company
    if not company.is_active:
        raise ForbiddenException("Target company is inactive")

    return TenantContext(user=current_user, company=company, membership=membership)


def require_roles(allowed_roles: List[MembershipRole]) -> Callable:
    """Dependency factory ensuring user has at least one of the required roles in the tenant."""
    async def role_checker(context: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if context.role not in allowed_roles:
            raise ForbiddenException(
                f"Action requires one of the following roles: {[r.value for r in allowed_roles]}"
            )
        return context

    return role_checker
