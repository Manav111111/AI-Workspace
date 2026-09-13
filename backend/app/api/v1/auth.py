from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest, Token
from app.schemas.company import CompanyRead
from app.schemas.user import UserRead
from app.services.auth import AuthService
from app.services.company import CompanyService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def signup(
    data: SignupRequest,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Register a new user and optionally create their initial company workspace."""
    auth_service = AuthService(session)
    user, token, company = await auth_service.register(data)

    return {
        "user": UserRead.model_validate(user),
        "company": CompanyRead.model_validate(company) if company else None,
        "token": token,
    }


@router.post("/login", response_model=Dict[str, Any])
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Authenticate with email and password to receive a JWT access token."""
    auth_service = AuthService(session)
    user, token = await auth_service.authenticate(data)

    return {
        "user": UserRead.model_validate(user),
        "token": token,
    }


@router.get("/me", response_model=Dict[str, Any])
async def get_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get profile and company memberships for the currently authenticated user."""
    company_service = CompanyService(session)
    memberships = await company_service.get_user_companies(current_user.id)

    return {
        "user": UserRead.model_validate(current_user),
        "companies": [
            {
                "membership_id": m.id,
                "role": m.role,
                "company": CompanyRead.model_validate(m.company),
            }
            for m in memberships
        ],
    }
