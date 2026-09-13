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

logger = logging.getLogger("app.services.conversation_engine")


@dataclass
class ConversationEngineResponse:
    """Structured response from the Conversation Engine."""
    user_message: Message
    assistant_message: Message
    citations: List[Dict[str, Any]]
    retrieval_count: int
    retrieval_metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)


class ConversationEngine:
    """Central Conversational Engine for AI Employees.
    Completely decoupled from presentation layers (Avatar, Voice, Widget).
    Coordinates:
    - Multi-tenant security boundary
    - Safe message persistence (User message persisted BEFORE LLM call)
    - Grounded vector retrieval with zero-retrieval safeguards
    - Context & prompt injection defense assembly
    - LLM invocation with timeout and retry handling
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
    ) -> ConversationEngineResponse:
        total_start = time.perf_counter()

        # 1. Query Validation
        query = user_query.strip()
        if not query:
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

        # 3. Improvement #1: Persist the USER message BEFORE calling the LLM
        # This guarantees user query is never lost if external LLM times out or fails
        user_msg = await self.message_repo.create(
            conversation_id=conversation_id,
            company_id=company_id,
            role=MessageRole.USER,
            content=query,
            metadata={"user_id": str(user_id) if user_id else None},
        )

        # 4. Fetch recent conversation history (excluding the message just added)
        history_records = await self.message_repo.get_recent_history(
            conversation_id=conversation_id,
            company_id=company_id,
            limit=settings.CONVERSATION_HISTORY_MESSAGES + 1,
        )
        # Filter out the newly created message from history list
        history_formatted = [
            {"role": m.role.value.lower(), "content": m.content}
            for m in history_records
            if m.id != user_msg.id
        ]

        # 5. Execute Grounded Knowledge Retrieval with AI Employee Scoped Knowledge Access
        assigned_kbs = getattr(ai_employee, "knowledge_bases", []) or []
        assigned_kb_ids = [kb.id for kb in assigned_kbs]

        retrieval_start = time.perf_counter()
        if assigned_kb_ids:
            retrieved_chunks = await self.retrieval_service.retrieve(
                company_id=company_id,
                query=query,
                knowledge_base_ids=assigned_kb_ids,
            )
            retrieval_latency_ms = round((time.perf_counter() - retrieval_start) * 1000, 2)
            top_score = retrieved_chunks[0].score if retrieved_chunks else 0.0
            retrieval_skipped = False
        else:
            # ZERO-KNOWLEDGE POLICY: If the AI Employee has 0 assigned knowledge bases,
            # retrieval is skipped entirely to prevent unauthorized access or cross-department leaks.
            retrieved_chunks = []
            retrieval_latency_ms = 0.0
            top_score = 0.0
            retrieval_skipped = True

        # Improvement #3: Track retrieval metadata for observability
        retrieval_metadata = {
            "query": query,
            "assigned_kbs_count": len(assigned_kb_ids),
            "assigned_kb_ids": [str(k) for k in assigned_kb_ids],
            "retrieval_skipped": retrieval_skipped,
            "chunks_retrieved": len(retrieved_chunks),
            "top_score": round(top_score, 4),
            "retrieval_latency_ms": retrieval_latency_ms,
        }

        # 6. Context & Prompt Assembly with Zero-Retrieval Safeguard (Improvement #2)
        has_context = len(retrieved_chunks) > 0
        context_text = self.context_builder.build_context(retrieved_chunks) if has_context else ""

        llm_messages = PromptBuilder.build_chat_messages(
            employee_name=ai_employee.name,
            role=ai_employee.role,
            personality=ai_employee.personality,
            custom_system_prompt=ai_employee.system_prompt,
            context_text=context_text,
            has_context=has_context,
            conversation_history=history_formatted,
            current_user_query=query,
        )

        # 7. Invoke LLM Provider
        llm_start = time.perf_counter()
        try:
            llm_response = await self.llm_provider.generate(
                messages=llm_messages,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )
        except Exception as e:
            logger.error(
                f"LLM invocation failure for tenant {company_id}, employee {ai_employee.id}: {e}",
                exc_info=True,
            )
            raise

        llm_latency_ms = round((time.perf_counter() - llm_start) * 1000, 2)
        total_latency_ms = round((time.perf_counter() - total_start) * 1000, 2)

        # 8. Build Citations (Only from legitimately retrieved chunks)
        citations: List[Dict[str, Any]] = []
        if has_context:
            for c in retrieved_chunks:
                citations.append({
                    "chunk_id": str(c.chunk_id),
                    "document_id": str(c.document_id),
                    "document_name": c.source or "Document",
                    "page_number": c.page_number,
                    "header_path": c.header_path,
                    "score": round(c.score, 3),
                    "preview": c.text[:200] + "..." if len(c.text) > 200 else c.text,
                })

        # 9. Persist Assistant Response in PostgreSQL
        assistant_metadata = {
            "retrieval": retrieval_metadata,
            "llm": {
                "model": llm_response.model,
                "usage": llm_response.usage,
                "finish_reason": llm_response.finish_reason,
                "llm_latency_ms": llm_latency_ms,
            },
            "total_latency_ms": total_latency_ms,
        }

        assistant_msg = await self.message_repo.create(
            conversation_id=conversation_id,
            company_id=company_id,
            role=MessageRole.ASSISTANT,
            content=llm_response.content,
            citations=citations,
            metadata=assistant_metadata,
        )

        # 10. Update Conversation Title on First Message
        if conversation.title == "New Conversation" or conversation.title.startswith("Chat with"):
            clean_title = query[:40] + ("..." if len(query) > 40 else "")
            await self.conversation_repo.update_title(conversation_id, company_id, clean_title)

        # 11. Structured Logging for Observability
        logger.info(
            f"Chat turn complete | company={company_id} | employee={ai_employee.id} "
            f"| conv={conversation_id} | retrieved={len(retrieved_chunks)} | top_score={top_score:.3f} "
            f"| ret_lat={retrieval_latency_ms}ms | llm_lat={llm_latency_ms}ms | total_lat={total_latency_ms}ms"
        )

        metrics = {
            "retrieval_latency_ms": retrieval_latency_ms,
            "llm_latency_ms": llm_latency_ms,
            "total_latency_ms": total_latency_ms,
            "chunks_retrieved": len(retrieved_chunks),
            "model": llm_response.model,
        }

        return ConversationEngineResponse(
            user_message=user_msg,
            assistant_message=assistant_msg,
            citations=citations,
            retrieval_count=len(retrieved_chunks),
            retrieval_metadata=retrieval_metadata,
            metrics=metrics,
        )
