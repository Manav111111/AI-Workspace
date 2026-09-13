from typing import List, Optional, Sequence
import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.company import Company
from app.models.membership import Membership, MembershipRole
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self, session: AsyncSession):
        super().__init__(Company, session)

    async def get_by_slug(self, slug: str) -> Optional[Company]:
        stmt = select(Company).where(Company.slug == slug.lower().strip())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_memberships(self, user_id: uuid.UUID) -> Sequence[Membership]:
        stmt = (
            select(Membership)
            .where(Membership.user_id == user_id)
            .options(selectinload(Membership.company))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_membership(self, user_id: uuid.UUID, company_id: uuid.UUID) -> Optional[Membership]:
        stmt = select(Membership).where(
            Membership.user_id == user_id,
            Membership.company_id == company_id,
        ).options(selectinload(Membership.company))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_membership(
        self,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
        role: MembershipRole = MembershipRole.MEMBER,
    ) -> Membership:
        membership = Membership(
            user_id=user_id,
            company_id=company_id,
            role=role,
        )
        self.session.add(membership)
        await self.session.flush()
        await self.session.refresh(membership)
        return membership
