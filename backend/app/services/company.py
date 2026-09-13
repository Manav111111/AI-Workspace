import re
from typing import List, Optional, Sequence
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.models.company import Company
from app.models.membership import Membership, MembershipRole
from app.models.user import User
from app.repositories.company import CompanyRepository
from app.repositories.user import UserRepository
from app.schemas.company import CompanyCreate, MembershipCreate


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


class CompanyService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.company_repo = CompanyRepository(session)
        self.user_repo = UserRepository(session)

    async def create_company(self, user: User, data: CompanyCreate) -> Company:
        base_slug = data.slug or slugify(data.name)
        slug = base_slug
        counter = 1
        while await self.company_repo.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        company = Company(
            name=data.name.strip(),
            slug=slug,
            is_active=True,
        )
        company = await self.company_repo.create(company)

        # Assign the creating user as OWNER
        await self.company_repo.create_membership(
            user_id=user.id,
            company_id=company.id,
            role=MembershipRole.OWNER,
        )
        await self.session.commit()
        await self.session.refresh(company)
        return company

    async def get_user_companies(self, user_id: uuid.UUID) -> Sequence[Membership]:
        return await self.company_repo.get_user_memberships(user_id)

    async def get_company_by_id(self, company_id: uuid.UUID) -> Company:
        company = await self.company_repo.get(company_id)
        if not company:
            raise NotFoundException("Company not found")
        return company

    async def add_member(
        self,
        actor_user: User,
        company_id: uuid.UUID,
        data: MembershipCreate,
    ) -> Membership:
        # Check that actor has OWNER or ADMIN role
        actor_membership = await self.company_repo.get_membership(actor_user.id, company_id)
        if not actor_membership or actor_membership.role not in [MembershipRole.OWNER, MembershipRole.ADMIN]:
            raise ForbiddenException("Only owners or admins can invite new members")

        target_user = await self.user_repo.get_by_email(data.user_email)
        if not target_user:
            raise NotFoundException(f"User with email '{data.user_email}' not found")

        existing_membership = await self.company_repo.get_membership(target_user.id, company_id)
        if existing_membership:
            raise ConflictException("User is already a member of this company")

        membership = await self.company_repo.create_membership(
            user_id=target_user.id,
            company_id=company_id,
            role=data.role,
        )
        await self.session.commit()
        await self.session.refresh(membership)
        return membership
