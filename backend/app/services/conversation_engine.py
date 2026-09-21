from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.message import Message, MessageRole
from app.repositories.ai_employee import AIEmployeeRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.services.context_builder import ContextBuilder
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMProvider
from app.services.prompt_builder import PromptBuilder
from app.services.retrieval import RetrievalService, RetrievedChunk
from app.schemas.avatar import map_conversation_context_to_presentation

logger = logging.getLogger("app.services.conversation_engine")


@dataclass
class ConversationEngineResponse:
    """Structured response from the Conversation Engine."""
    user_message: Message
    assistant_message: Message
    citations: List[Dict[str, Any]]
    retrieval_count: int
    retrieval_metadata: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    pending_confirmation: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    presentation: Optional[Dict[str, Any]] = None


class ConversationEngine:
    """Central Conversational Engine for AI Employees.
    Completely decoupled from presentation layers (Avatar, Voice, Widget).
    Coordinates:
    - Multi-tenant security boundary
    - Safe message persistence (User message persisted BEFORE LLM call)
    - Agent Orchestrator invocation (combines RAG + assigned business tools + memory)
    - Tool execution with tenant isolation and confirmation lifecycle
    - Citation tracking and observability logging
    """

    def __init__(
        self,
        session: AsyncSession,
        retrieval_service: Optional[RetrievalService] = None,
        llm_provider: Optional[LLMProvider] = None,
        context_builder: Optional[ContextBuilder] = None,
    ):
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.message_repo = MessageRepository(session)
        self.employee_repo = AIEmployeeRepository(session)
        self.retrieval_service = retrieval_service or RetrievalService()
        self.llm_provider = llm_provider or get_llm_provider()
        self.context_builder = context_builder or ContextBuilder()

    async def respond(
        self,
        company_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_query: str,
        user_id: Optional[uuid.UUID] = None,
        pending_action_id: Optional[uuid.UUID] = None,
        confirm_action: bool = False,
    ) -> ConversationEngineResponse:
        total_start = time.perf_counter()

        # 1. Query Validation
        query = user_query.strip()
        if not query and not pending_action_id:
            raise ValidationException("Message content cannot be empty")
        if len(query) > 2000:
            raise ValidationException("Message content exceeds maximum allowed length (2000 characters)")

        # 2. Multi-Tenant Authorization & Entity Lookup
        conversation = await self.conversation_repo.get_by_id(conversation_id, company_id)
        if not conversation:
            raise NotFoundException("Conversation not found")

        ai_employee = await self.employee_repo.get_by_tenant(
            company_id=company_id,
            employee_id=conversation.ai_employee_id,
        )
        if not ai_employee:
            raise NotFoundException("AI Employee associated with this conversation was not found")

        # 3. Persist the USER message BEFORE calling orchestrator/LLM
        user_msg = await self.message_repo.create(
            conversation_id=conversation_id,
            company_id=company_id,
            role=MessageRole.USER,
            content=query if query else ("Confirmed action" if confirm_action else "Cancelled action"),
            metadata={
                "user_id": str(user_id) if user_id else None,
                "pending_action_id": str(pending_action_id) if pending_action_id else None,
            },
        )

        # 4. Fetch recent conversation history
        history_records = await self.message_repo.get_recent_history(
            conversation_id=conversation_id,
            company_id=company_id,
            limit=settings.CONVERSATION_HISTORY_MESSAGES + 1,
        )
        history_formatted = [
            {"role": m.role.value.lower(), "content": m.content}
            for m in history_records
            if m.id != user_msg.id
        ]

        # 5. Delegate to Agent Orchestrator (combines RAG + assigned tools)
        from app.services.agent.orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator(
            session=self.session,
            llm_provider=self.llm_provider,
            retrieval_service=self.retrieval_service,
            context_builder=self.context_builder,
        )

        agent_res = await orchestrator.execute(
            company_id=company_id,
            ai_employee=ai_employee,
            conversation_id=conversation_id,
            user_query=query,
            conversation_history=history_formatted,
            user_id=user_id,
            pending_action_id=pending_action_id,
            confirm_action=confirm_action,
        )

        total_latency_ms = round((time.perf_counter() - total_start) * 1000, 2)

        # 6. Persist Assistant Response in PostgreSQL
        assistant_metadata = {
            "retrieval": {
                "chunks_count": len(agent_res.retrieved_chunks),
            },
            "tools": {
                "calls_count": len(agent_res.tool_calls_executed),
                "calls": agent_res.tool_calls_executed,
            },
            "pending_confirmation": agent_res.pending_confirmation,
            "total_latency_ms": total_latency_ms,
        }

        assistant_msg = await self.message_repo.create(
            conversation_id=conversation_id,
            company_id=company_id,
            role=MessageRole.ASSISTANT,
            content=agent_res.content,
            citations=agent_res.citations,
            metadata=assistant_metadata,
        )

        # 7. Update Conversation Title on First Message
        if conversation.title == "New Conversation" or conversation.title.startswith("Chat with"):
            clean_title = query[:40] + ("..." if len(query) > 40 else "")
            if clean_title:
                await self.conversation_repo.update_title(conversation_id, company_id, clean_title)

        logger.info(
            f"Agent chat turn complete | company={company_id} | employee={ai_employee.id} "
            f"| conv={conversation_id} | tools={len(agent_res.tool_calls_executed)} "
            f"| chunks={len(agent_res.retrieved_chunks)} | total_lat={total_latency_ms}ms"
        )

        # 8. Deterministic Presentation Metadata for Avatar/Voice Layers
        tool_names = [tc.get("tool_name") for tc in agent_res.tool_calls_executed] if agent_res.tool_calls_executed else []
        pres_metadata = map_conversation_context_to_presentation(
            reply_text=agent_res.content,
            tool_activity=tool_names,
            pending_confirmation=agent_res.pending_confirmation,
            user_query=query,
        )

        return ConversationEngineResponse(
            user_message=user_msg,
            assistant_message=assistant_msg,
            citations=agent_res.citations,
            retrieval_count=len(agent_res.retrieved_chunks),
            retrieval_metadata=agent_res.retrieval_metadata,
            tool_calls=agent_res.tool_calls_executed,
            pending_confirmation=agent_res.pending_confirmation,
            metrics=agent_res.metrics,
            presentation=pres_metadata.model_dump(),
        )
