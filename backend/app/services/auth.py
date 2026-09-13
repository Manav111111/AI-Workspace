import re
import uuid
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import ConflictException, UnauthorizedException, ValidationException
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.company import Company
from app.models.membership import MembershipRole
from app.models.user import User
from app.repositories.company import CompanyRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, SignupRequest, Token


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.company_repo = CompanyRepository(session)

    async def register(self, data: SignupRequest) -> Tuple[User, Token, Optional[Company]]:
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise ConflictException(f"User with email '{data.email}' already exists")

        # Create user
        user = User(
            email=data.email.lower().strip(),
            full_name=data.full_name.strip(),
            hashed_password=get_password_hash(data.password),
            is_active=True,
        )
        user = await self.user_repo.create(user)

        # Optional initial company creation
        company = None
        if data.company_name and data.company_name.strip():
            c_name = data.company_name.strip()
            base_slug = slugify(c_name)
            slug = base_slug
            counter = 1
            while await self.company_repo.get_by_slug(slug):
                slug = f"{base_slug}-{counter}"
                counter += 1

            company = Company(
                name=c_name,
                slug=slug,
                is_active=True,
            )
            company = await self.company_repo.create(company)

            # Assign user as OWNER of the new company
            await self.company_repo.create_membership(
                user_id=user.id,
                company_id=company.id,
                role=MembershipRole.OWNER,
            )

        await self.session.commit()
        await self.session.refresh(user)

        token = Token(
            access_token=create_access_token(subject=str(user.id)),
            token_type="bearer",
        )
        return user, token, company

    async def authenticate(self, data: LoginRequest) -> Tuple[User, Token]:
        user = await self.user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password")

        if not user.is_active:
            raise UnauthorizedException("User account is deactivated")

        token = Token(
            access_token=create_access_token(subject=str(user.id)),
            token_type="bearer",
        )
        return user, token
