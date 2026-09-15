import hashlib
import logging
from typing import List, Optional
from urllib.parse import urlparse
from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_employee import AIEmployee
from app.models.conversation import Conversation
from app.models.public_session import PublicChatSession

logger = logging.getLogger("app.services.public_runtime.security")

security_bearer = HTTPBearer(auto_error=False)


def hash_token(raw_token: str) -> str:
    """Deterministic sha256 hash of public session token for storage and lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class PublicSecurityService:
    """Security Boundary for Public Runtime.
    Enforces:
    - Header-based session token resolution via sha256 hash
    - Server-side Session Ownership Invariants (conversation.company_id == session.company_id && conversation.ai_employee_id == session.ai_employee_id)
    - Browser integration controls for allowed domains
    - Rejection of expired sessions or unpublished AI employees
    """

    @staticmethod
    def validate_origin_integration_control(
        request: Request,
        allowed_domains: List[str],
    ) -> None:
        """Integration control for browser requests.
        Treats Origin/Referer as a browser integration control, NOT as primary authentication.
        """
        if not allowed_domains:
            # Open/development mode: all domains allowed
            return

        origin_header = request.headers.get("origin") or request.headers.get("referer")
        if not origin_header:
            # Non-browser or direct clients without origin are subject to strict rate limits & session checks
            return

        try:
            parsed = urlparse(origin_header)
            hostname = (parsed.hostname or "").lower()
            port = parsed.port
            # Support local development
            if hostname in {"localhost", "127.0.0.1"}:
                return

            # Check exact match or subdomain match
            matched = False
            for allowed in allowed_domains:
                allowed_clean = allowed.strip().lower()
                if hostname == allowed_clean or hostname.endswith("." + allowed_clean):
                    matched = True
                    break

            if not matched:
                logger.warning(f"Public request rejected: origin '{origin_header}' not in allowed domains {allowed_domains}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Origin domain is not authorized to embed this AI Employee widget.",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error parsing origin header '{origin_header}': {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid origin header format.",
            )

    @staticmethod
    async def resolve_active_session(
        session: AsyncSession,
        raw_token: str,
    ) -> PublicChatSession:
        """Resolves session from header token hash and validates ownership invariants."""
        if not raw_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Public session bearer token is required in Authorization header.",
            )

        token_h = hash_token(raw_token.strip())
        stmt = (
            select(PublicChatSession)
            .where(
                PublicChatSession.token_hash == token_h,
                PublicChatSession.is_active == True,
            )
        )
        res = await session.execute(stmt)
        public_session = res.scalar_one_or_none()

        if not public_session:
            logger.warning("Public session resolution failed: invalid or revoked token hash.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired public chat session.",
            )

        # Check expiration
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        exp = public_session.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=datetime.timezone.utc)
        if exp < now:
            logger.warning(f"Public session {public_session.id} expired at {public_session.expires_at}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Public chat session has expired. Please refresh the widget to start a new chat.",
            )

        # Enforce server-side session ownership invariant
        conv_stmt = select(Conversation).where(Conversation.id == public_session.conversation_id)
        conv_res = await session.execute(conv_stmt)
        conv = conv_res.scalar_one_or_none()

        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated conversation record not found.",
            )

        if conv.company_id != public_session.company_id or conv.ai_employee_id != public_session.ai_employee_id:
            logger.critical(
                f"SECURITY INVARIANT VIOLATION: Session {public_session.id} (company={public_session.company_id}, "
                f"employee={public_session.ai_employee_id}) mismatch with Conversation {conv.id} "
                f"(company={conv.company_id}, employee={conv.ai_employee_id})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session ownership invariant violation.",
            )

        return public_session
