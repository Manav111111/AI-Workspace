import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.public_session import PublicChatSession
from app.schemas.public_runtime import (
    PublicChatResponse,
    PublicEmployeeConfigResponse,
    PublicMessageCreate,
    PublicMessageHistoryItem,
    PublicSessionCreateRequest,
    PublicSessionResponse,
)
from app.services.public_runtime.rate_limit import get_client_ip, rate_limiter
from app.services.public_runtime.runtime import PublicRuntimeService
from app.services.public_runtime.security import PublicSecurityService

logger = logging.getLogger("app.api.v1.public")

router = APIRouter(prefix="/public", tags=["Public Runtime"])
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_public_session(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> PublicChatSession:
    """Dependency extracting and validating Bearer session token from Authorization header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Public session bearer token is required in Authorization header (Authorization: Bearer sess_pub_xxx).",
        )
    return await PublicSecurityService.resolve_active_session(db, credentials.credentials)


@router.get("/employees/{public_id}/config", response_model=PublicEmployeeConfigResponse)
async def get_public_employee_config(
    public_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves sanitized public configuration for an AI Employee.
    Zero leakage of system prompts, internal database UUIDs, company credentials, or tool internals.
    """
    client_ip = get_client_ip(request)
    rate_limiter.check_limit(f"config_{client_ip}", max_requests=60, window_seconds=60, action_name="fetching employee config")

    runtime = PublicRuntimeService(db)
    emp = await runtime.get_published_employee(public_id)

    # Validate domain integration control
    PublicSecurityService.validate_origin_integration_control(request, emp.allowed_domains or [])

    return await runtime.get_public_config(public_id)


@router.post("/employees/{public_id}/sessions", response_model=PublicSessionResponse)
async def create_public_session(
    public_id: str,
    payload: PublicSessionCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Creates or resumes an anonymous visitor chat session.
    Protected by IP rate limiting (20 sessions/minute).
    """
    client_ip = get_client_ip(request)
    rate_limiter.check_limit(f"session_create_{client_ip}", max_requests=20, window_seconds=60, action_name="session creation")

    runtime = PublicRuntimeService(db)
    emp = await runtime.get_published_employee(public_id)

    # Validate domain integration control
    PublicSecurityService.validate_origin_integration_control(request, emp.allowed_domains or [])

    origin = request.headers.get("origin") or request.headers.get("referer")
    return await runtime.create_or_resume_session(
        public_id=public_id,
        visitor_id=payload.visitor_id,
        origin_domain=origin,
    )


@router.post("/sessions/messages", response_model=PublicChatResponse)
async def send_public_message(
    payload: PublicMessageCreate,
    request: Request,
    public_session: PublicChatSession = Depends(get_current_public_session),
    db: AsyncSession = Depends(get_db),
):
    """Sends a visitor message in an active public chat session.
    Requires header: `Authorization: Bearer sess_pub_xxx`.
    Protected by rate limiting (30 messages/minute per session).
    Zero client-supplied tool arguments or arbitrary tool execution.
    """
    rate_limiter.check_limit(
        f"msg_{public_session.id}",
        max_requests=30,
        window_seconds=60,
        action_name="sending messages",
    )

    runtime = PublicRuntimeService(db)
    return await runtime.handle_message(public_session, payload)


@router.get("/sessions/messages", response_model=List[PublicMessageHistoryItem])
async def get_public_session_messages(
    public_session: PublicChatSession = Depends(get_current_public_session),
    db: AsyncSession = Depends(get_db),
):
    """Fetches conversation history for the active session (for restoring chat state upon page refresh)."""
    runtime = PublicRuntimeService(db)
    return await runtime.get_session_history(public_session)
