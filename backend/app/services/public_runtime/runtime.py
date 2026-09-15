import datetime
import logging
import secrets
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai_employee import AIEmployee, AIEmployeeStatus
from app.models.conversation import Conversation
from app.models.public_session import PublicChatSession
from app.models.public_usage import PublicUsageEvent
from app.schemas.public_runtime import (
    PublicChatResponse,
    PublicCitation,
    PublicEmployeeConfigResponse,
    PublicMessageCreate,
    PublicMessageHistoryItem,
    PublicPendingConfirmation,
    PublicSessionResponse,
)
from app.services.conversation_engine import ConversationEngine
from app.services.public_runtime.security import PublicSecurityService, hash_token

logger = logging.getLogger("app.services.public_runtime.runtime")


class PublicRuntimeService:
    """Core Public Runtime Orchestrator.
    Coordinates public visitor interactions with published AI Employees without exposing private credentials.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_published_employee(self, public_id: str) -> AIEmployee:
        """Find published employee by cryptographically generated public identifier."""
        stmt = (
            select(AIEmployee)
            .where(
                AIEmployee.public_id == public_id,
                AIEmployee.is_published == True,
                AIEmployee.status == AIEmployeeStatus.ACTIVE,
            )
            .options(
                selectinload(AIEmployee.knowledge_bases),
                selectinload(AIEmployee.assigned_tools),
            )
        )
        res = await self.session.execute(stmt)
        emp = res.scalar_one_or_none()
        if not emp:
            logger.info(f"Public employee lookup failed for public_id: {public_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI Employee not found or not published.",
            )
        return emp

    async def get_public_config(self, public_id: str) -> PublicEmployeeConfigResponse:
        """Sanitized employee configuration for widget bootstrapping."""
        emp = await self.get_published_employee(public_id)
        return PublicEmployeeConfigResponse(
            public_id=emp.public_id or "",
            name=emp.name,
            role=emp.role,
            description=emp.description,
            language=emp.language,
            avatar_config=emp.avatar_config or {},
            widget_config=emp.widget_config or {},
        )

    async def create_or_resume_session(
        self,
        public_id: str,
        visitor_id: Optional[str] = None,
        origin_domain: Optional[str] = None,
    ) -> PublicSessionResponse:
        """Creates an anonymous visitor session or resumes an active one."""
        emp = await self.get_published_employee(public_id)

        # 1. Check if visitor has an active unexpired session
        now = datetime.datetime.now(datetime.timezone.utc)
        if visitor_id:
            stmt = (
                select(PublicChatSession)
                .where(
                    PublicChatSession.ai_employee_id == emp.id,
                    PublicChatSession.visitor_id == visitor_id,
                    PublicChatSession.is_active == True,
                    PublicChatSession.expires_at > now,
                )
                .order_by(PublicChatSession.created_at.desc())
            )
            res = await self.session.execute(stmt)
            existing = res.scalar_one_or_none()
            if existing:
                # Issue a new raw token for resumed session while updating token_hash
                raw_token = f"sess_pub_{secrets.token_hex(24)}"
                existing.token_hash = hash_token(raw_token)
                existing.expires_at = now + datetime.timedelta(hours=24)
                await self.session.commit()
                return PublicSessionResponse(
                    session_token=raw_token,
                    expires_at=existing.expires_at,
                    employee=await self.get_public_config(public_id),
                )

        # 2. Create new conversation for visitor
        conversation = Conversation(
            company_id=emp.company_id,
            ai_employee_id=emp.id,
            user_id=None,  # Public anonymous visitor
            title=f"Website Chat with {emp.name}",
            conversation_metadata={"source": "public_widget", "visitor_id": visitor_id},
        )
        self.session.add(conversation)
        await self.session.flush()

        # 3. Create public session
        raw_token = f"sess_pub_{secrets.token_hex(24)}"
        public_session = PublicChatSession(
            company_id=emp.company_id,
            ai_employee_id=emp.id,
            conversation_id=conversation.id,
            token_hash=hash_token(raw_token),
            visitor_id=visitor_id,
            origin_domain=origin_domain,
            expires_at=now + datetime.timedelta(hours=24),
        )
        self.session.add(public_session)
        await self.session.commit()

        return PublicSessionResponse(
            session_token=raw_token,
            expires_at=public_session.expires_at,
            employee=await self.get_public_config(public_id),
        )

    async def handle_message(
        self,
        public_session: PublicChatSession,
        payload: PublicMessageCreate,
    ) -> PublicChatResponse:
        """Processes a visitor message via the unified ConversationEngine.
        Enforces:
        - Max 50 messages per session (abuse ceiling)
        - Visitors cannot execute arbitrary tools or pass tool parameters directly
        - Write tools require confirmation of existing server-side PendingToolAction
        - Emits PublicUsageEvent record
        """
        # Session message count limit
        if public_session.message_count >= 50:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Session message limit reached. Please refresh the page to start a new chat.",
            )

        start_time = time.perf_counter()

        # Delegate execution directly to the unified ConversationEngine
        engine = ConversationEngine(self.session)
        engine_response = await engine.respond(
            company_id=public_session.company_id,
            conversation_id=public_session.conversation_id,
            user_query=payload.message,
            user_id=None,
            pending_action_id=payload.pending_action_id,
            confirm_action=payload.confirm_action,
        )

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Update session message count
        public_session.message_count += 1
        self.session.add(public_session)

        # Map citations
        citations: List[PublicCitation] = []
        for c in engine_response.citations:
            citations.append(
                PublicCitation(
                    document_name=c.get("document_name", "Knowledge Document"),
                    page_number=c.get("page_number"),
                    header_path=c.get("header_path"),
                    score=round(float(c.get("score", 0.0)), 3),
                )
            )

        # Map tool activity
        tool_activity: List[str] = []
        for tc in engine_response.tool_calls:
            name = tc.get("name") or tc.get("tool_name")
            if name:
                tool_activity.append(name)

        # Map pending confirmation if write action triggered
        pending_conf: Optional[PublicPendingConfirmation] = None
        if engine_response.pending_confirmation:
            pc = engine_response.pending_confirmation
            pending_conf = PublicPendingConfirmation(
                pending_action_id=str(pc.get("pending_action_id")),
                tool_name=str(pc.get("tool_name")),
                arguments=pc.get("arguments", {}),
                message=pc.get("message"),
            )

        # Record PublicUsageEvent
        usage_event = PublicUsageEvent(
            company_id=public_session.company_id,
            ai_employee_id=public_session.ai_employee_id,
            session_id=public_session.id,
            event_type="CONFIRMATION" if payload.pending_action_id else ("TOOL_CALL" if tool_activity else "MESSAGE"),
            message_count=1,
            tool_call_count=len(tool_activity),
            input_tokens=engine_response.metrics.get("prompt_tokens", 0) or 0,
            output_tokens=engine_response.metrics.get("completion_tokens", 0) or 0,
            latency_ms=latency_ms,
        )
        self.session.add(usage_event)
        await self.session.commit()

        return PublicChatResponse(
            message=engine_response.assistant_message.content,
            citations=citations,
            tool_activity=tool_activity,
            pending_confirmation=pending_conf,
            created_at=engine_response.assistant_message.created_at,
        )

    async def get_session_history(
        self,
        public_session: PublicChatSession,
    ) -> List[PublicMessageHistoryItem]:
        """Fetches conversation history for active session."""
        conv_stmt = (
            select(Conversation)
            .where(Conversation.id == public_session.conversation_id)
            .options(selectinload(Conversation.messages))
        )
        conv_res = await self.session.execute(conv_stmt)
        conv = conv_res.scalar_one_or_none()
        if not conv:
            return []

        history: List[PublicMessageHistoryItem] = []
        for msg in conv.messages:
            cits: List[PublicCitation] = []
            if msg.citations:
                for c in msg.citations:
                    cits.append(
                        PublicCitation(
                            document_name=c.get("document_name", "Document"),
                            page_number=c.get("page_number"),
                            header_path=c.get("header_path"),
                            score=round(float(c.get("score", 0.0)), 3),
                        )
                    )
            t_activity = []
            if msg.message_metadata and "tool_calls" in msg.message_metadata:
                for tc in msg.message_metadata["tool_calls"]:
                    name = tc.get("name") or tc.get("tool_name")
                    if name:
                        t_activity.append(name)

            history.append(
                PublicMessageHistoryItem(
                    role=msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                    content=msg.content,
                    citations=cits,
                    tool_activity=t_activity,
                    created_at=msg.created_at,
                )
            )

        return history
