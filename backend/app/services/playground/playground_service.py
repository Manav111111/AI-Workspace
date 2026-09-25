import copy
import datetime
import logging
import time
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.ai_employee import AIEmployee
from app.models.playground import PlaygroundMessage, PlaygroundSession
from app.services.agent.orchestrator import AgentOrchestrator
from app.services.agent.tool_registry import tool_registry
from app.services.billing.budget_service import BudgetService
from app.services.billing.usage_adapter import UsageAdapter
from app.services.context_builder import ContextBuilder
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMProvider, LLMResponse
from app.services.observability.redactor import TelemetryRedactor
from app.services.observability.tracer import (
    TraceCollector,
    generate_trace_id,
    tracer,
)
from app.services.prompt_builder import PromptBuilder
from app.services.retrieval import RetrievalService, RetrievedChunk

logger = logging.getLogger("app.services.playground.service")


class PlaygroundService:
    """Tenant-isolated AI Employee testing, debugging, and experimentation service.
    Reuses existing production ConversationEngine components (RetrievalService,
    PromptBuilder, LLMProvider, ToolRegistry) while operating on independent,
    isolated configuration snapshots to prevent polluting production state.
    """

    @classmethod
    async def create_session(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        ai_employee_id: uuid.UUID,
        session_name: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> PlaygroundSession:
        """Initializes a new playground session with an immutable configuration snapshot."""
        stmt = (
            select(AIEmployee)
            .where(
                AIEmployee.id == ai_employee_id,
                AIEmployee.company_id == company_id,
            )
        )
        ai_employee = (await session.execute(stmt)).scalar_one_or_none()
        if not ai_employee:
            raise NotFoundException("AI Employee not found in active company")

        overrides = config_overrides or {}
        assigned_kbs = getattr(ai_employee, "knowledge_bases", []) or []
        default_kb_ids = [str(kb.id) for kb in assigned_kbs]
        assigned_tools_rel = getattr(ai_employee, "assigned_tools", []) or []
        default_tools = [t.tool_name for t in assigned_tools_rel]

        snapshot = {
            "system_prompt": overrides.get("system_prompt", ai_employee.system_prompt or ""),
            "personality": overrides.get("personality", ai_employee.personality or ""),
            "model": overrides.get("model", getattr(settings, "LLM_MODEL", "gemini-3.6-flash")),
            "temperature": float(overrides.get("temperature", getattr(settings, "LLM_TEMPERATURE", 0.2))),
            "top_k": int(overrides.get("top_k", getattr(settings, "RAG_TOP_K", 5))),
            "retrieval_mode": overrides.get("retrieval_mode", getattr(settings, "RETRIEVAL_MODE", "dense")),
            "assigned_kb_ids": overrides.get("assigned_kb_ids", default_kb_ids),
            "assigned_tools": overrides.get("assigned_tools", default_tools),
        }

        pg_session = PlaygroundSession(
            company_id=company_id,
            user_id=user_id,
            ai_employee_id=ai_employee_id,
            session_name=session_name.strip() if session_name else f"Test: {ai_employee.name}",
            config_snapshot=snapshot,
            status="ACTIVE",
        )
        session.add(pg_session)
        await session.flush()
        return pg_session

    @classmethod
    async def get_session(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> PlaygroundSession:
        """Retrieves a playground session with strict tenant isolation."""
        stmt = select(PlaygroundSession).where(
            PlaygroundSession.id == session_id,
            PlaygroundSession.company_id == company_id,
        )
        pg_session = (await session.execute(stmt)).scalar_one_or_none()
        if not pg_session:
            raise NotFoundException("Playground session not found")
        return pg_session

    @classmethod
    async def list_sessions(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
        ai_employee_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PlaygroundSession]:
        """Lists playground sessions for the tenant."""
        stmt = (
            select(PlaygroundSession)
            .where(PlaygroundSession.company_id == company_id)
            .order_by(desc(PlaygroundSession.created_at))
            .limit(limit)
            .offset(offset)
        )
        if ai_employee_id:
            stmt = stmt.where(PlaygroundSession.ai_employee_id == ai_employee_id)
        return list((await session.execute(stmt)).scalars().all())

    @classmethod
    async def delete_session(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> bool:
        """Deletes a playground session strictly verifying tenant ownership."""
        pg_session = await cls.get_session(session, company_id, session_id)
        await session.delete(pg_session)
        await session.flush()
        return True

    @classmethod
    async def send_message(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        user_query: str,
    ) -> Dict[str, Any]:
        """Executes a test query in the playground using the snapshot configuration,
        recording retrieval scores, safe prompt structure, and execution trace.
        """
        query = user_query.strip()
        if not query:
            raise ValidationException("Message content cannot be empty")

        pg_session = await cls.get_session(session, company_id, session_id)
        config = pg_session.config_snapshot

        # 1. Budget Pre-Check
        await BudgetService.check_budget(
            session=session,
            company_id=company_id,
            ai_employee_id=pg_session.ai_employee_id,
        )

        trace_id = generate_trace_id()
        total_start = time.perf_counter()

        # 2. Persist USER message
        user_msg = PlaygroundMessage(
            session_id=session_id,
            company_id=company_id,
            role="user",
            content=query,
            trace_id=trace_id,
        )
        session.add(user_msg)
        await session.flush()

        # 3. Retrieve recent history within this playground session
        history_stmt = (
            select(PlaygroundMessage)
            .where(
                PlaygroundMessage.session_id == session_id,
                PlaygroundMessage.company_id == company_id,
                PlaygroundMessage.id != user_msg.id,
            )
            .order_by(desc(PlaygroundMessage.created_at))
            .limit(10)
        )
        history_records = list(reversed((await session.execute(history_stmt)).scalars().all()))
        conversation_history = [
            {"role": m.role.lower(), "content": m.content}
            for m in history_records
        ]

        async with TraceCollector(
            trace_id=trace_id,
            company_id=company_id,
            ai_employee_id=pg_session.ai_employee_id,
            request_type="PLAYGROUND",
        ) as collector:
            async with tracer.start_as_current_span(
                "playground.turn",
                trace_id=trace_id,
                attributes={"session_id": str(session_id)},
            ) as root_span:
                # 4. Scoped Retrieval with Snapshot Parameters
                raw_kb_ids = config.get("assigned_kb_ids", [])
                kb_uuids = [uuid.UUID(k) for k in raw_kb_ids if k]

                retrieval_start = time.perf_counter()
                retriever = RetrievalService()
                if kb_uuids:
                    async with tracer.start_as_current_span("playground.retrieval") as r_span:
                        retrieved_chunks = await retriever.retrieve(
                            company_id=company_id,
                            query=query,
                            knowledge_base_ids=kb_uuids,
                        )
                        r_span.set_attributes({
                            "chunks_retrieved": len(retrieved_chunks),
                            "kbs_count": len(kb_uuids),
                        })
                else:
                    retrieved_chunks = []
                retrieval_latency_ms = round((time.perf_counter() - retrieval_start) * 1000, 2)

                # Format retrieval debug data
                retrieval_debug = []
                citations = []
                for rank, c in enumerate(retrieved_chunks, start=1):
                    preview_txt = c.text[:300] + ("..." if len(c.text) > 300 else "")
                    chunk_meta = {
                        "rank": rank,
                        "chunk_id": str(c.chunk_id),
                        "document_id": str(c.document_id),
                        "document_name": c.source or "Document",
                        "page_number": c.page_number,
                        "header_path": c.header_path,
                        "score": round(c.score, 4),
                        "preview": TelemetryRedactor.redact_string(preview_txt),
                    }
                    retrieval_debug.append(chunk_meta)
                    citations.append({
                        "chunk_id": str(c.chunk_id),
                        "document_id": str(c.document_id),
                        "document_name": c.source or "Document",
                        "page_number": c.page_number,
                        "header_path": c.header_path,
                        "score": round(c.score, 3),
                        "preview": preview_txt,
                    })

                # 5. Safe Prompt Assembly & Inspection
                context_builder = ContextBuilder()
                context_text = context_builder.build_context(retrieved_chunks) if retrieved_chunks else ""

                with tracer.start_as_current_span("playground.prompt_assembly"):
                    messages = PromptBuilder.build_chat_messages(
                        employee_name="AI Employee",
                        role="Assistant",
                        personality=config.get("personality", ""),
                        custom_system_prompt=config.get("system_prompt", ""),
                        context_text=context_text,
                        has_context=len(retrieved_chunks) > 0,
                        conversation_history=conversation_history,
                        current_user_query=query,
                    )

                prompt_debug = {
                    "system_prompt": TelemetryRedactor.redact_string(config.get("system_prompt", "")),
                    "personality": TelemetryRedactor.redact_string(config.get("personality", "")),
                    "retrieved_context_preview": TelemetryRedactor.redact_string(context_text[:500]),
                    "messages_count": len(messages),
                    "model": config.get("model"),
                    "temperature": config.get("temperature"),
                }

                # 6. LLM Generation
                llm = get_llm_provider(model=config.get("model"))
                provider_name = getattr(llm, "provider", getattr(settings, "LLM_PROVIDER", "gemini"))
                model_name = getattr(llm, "model", config.get("model", "gemini-3.6-flash"))

                async with tracer.start_as_current_span("playground.llm_generation") as llm_span:
                    llm_start = time.perf_counter()
                    llm_resp: LLMResponse = await llm.generate(
                        messages=messages,
                        temperature=float(config.get("temperature", 0.2)),
                        max_tokens=getattr(settings, "LLM_MAX_TOKENS", 1000),
                    )
                    llm_latency_ms = round((time.perf_counter() - llm_start) * 1000, 2)

                    usage_obj = UsageAdapter.extract_usage(
                        provider=provider_name,
                        raw_usage=llm_resp.usage,
                        messages=messages,
                        generated_text=llm_resp.content,
                    )
                    llm_span.set_attributes({
                        "total_tokens": usage_obj.total_tokens,
                        "usage_source": usage_obj.usage_source,
                    })

                    # Record in usage ledger
                    ledger_entry = await BudgetService.record_usage(
                        session=session,
                        company_id=company_id,
                        ai_employee_id=pg_session.ai_employee_id,
                        trace_id=trace_id,
                        provider=provider_name,
                        model=model_name,
                        operation_type="LLM_GENERATION",
                        usage=usage_obj,
                    )

                total_latency_ms = round((time.perf_counter() - total_start) * 1000, 2)
                metrics = {
                    "retrieval_latency_ms": retrieval_latency_ms,
                    "llm_latency_ms": llm_latency_ms,
                    "total_latency_ms": total_latency_ms,
                    "total_tokens": usage_obj.total_tokens,
                    "estimated_cost_usd": float(ledger_entry.estimated_cost),
                }

                # 7. Persist Assistant PlaygroundMessage
                assistant_msg = PlaygroundMessage(
                    session_id=session_id,
                    company_id=company_id,
                    role="assistant",
                    content=llm_resp.content,
                    citations=citations,
                    retrieval_debug=retrieval_debug,
                    prompt_debug=prompt_debug,
                    trace_id=trace_id,
                    metrics=metrics,
                )
                session.add(assistant_msg)
                await session.flush()

                root_span.set_attributes({
                    "total_latency_ms": total_latency_ms,
                    "total_tokens": usage_obj.total_tokens,
                })

            # 8. Persist Trace Summary
            try:
                collector.set_metadata("total_tokens", usage_obj.total_tokens)
                collector.set_metadata("estimated_cost_usd", float(ledger_entry.estimated_cost))
                trace_summary = collector.build_summary()
                session.add(trace_summary)
                await session.flush()
            except Exception as te:
                logger.warning(f"Could not persist playground trace summary: {te}")

        return {
            "user_message": {
                "id": str(user_msg.id),
                "role": user_msg.role,
                "content": user_msg.content,
                "created_at": user_msg.created_at.isoformat(),
            },
            "assistant_message": {
                "id": str(assistant_msg.id),
                "role": assistant_msg.role,
                "content": assistant_msg.content,
                "created_at": assistant_msg.created_at.isoformat(),
            },
            "citations": citations,
            "retrieval_debug": retrieval_debug,
            "prompt_debug": prompt_debug,
            "metrics": metrics,
            "trace_id": trace_id,
        }

    @classmethod
    async def compare_configurations(
        cls,
        session: AsyncSession,
        company_id: uuid.UUID,
        ai_employee_id: uuid.UUID,
        test_queries: List[str],
        config_a: Dict[str, Any],
        config_b: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Runs side-by-side comparative execution of test queries against Config A and Config B,
        measuring differences in answers, retrieval chunk rank, token consumption, and latency.
        """
        queries = [q.strip() for q in test_queries if q.strip()]
        if not queries:
            raise ValidationException("At least one test query is required for comparison")
        if len(queries) > 5:
            queries = queries[:5]  # Bound comparison count

        results = []
        retriever = RetrievalService()

        for q in queries:
            # Run Config A
            start_a = time.perf_counter()
            kb_ids_a = [uuid.UUID(k) for k in config_a.get("assigned_kb_ids", []) if k]
            chunks_a = await retriever.retrieve(company_id=company_id, query=q, knowledge_base_ids=kb_ids_a) if kb_ids_a else []
            ctx_a = ContextBuilder().build_context(chunks_a) if chunks_a else ""
            msgs_a = PromptBuilder.build_chat_messages(
                employee_name="AI Employee A",
                role="Assistant",
                personality=config_a.get("personality", ""),
                custom_system_prompt=config_a.get("system_prompt", ""),
                context_text=ctx_a,
                has_context=len(chunks_a) > 0,
                conversation_history=[],
                current_user_query=q,
            )
            llm_a = get_llm_provider(model=config_a.get("model"))
            resp_a = await llm_a.generate(messages=msgs_a, temperature=float(config_a.get("temperature", 0.2)))
            lat_a = round((time.perf_counter() - start_a) * 1000, 2)
            usage_a = UsageAdapter.extract_usage("gemini", resp_a.usage, messages=msgs_a, generated_text=resp_a.content)

            # Run Config B
            start_b = time.perf_counter()
            kb_ids_b = [uuid.UUID(k) for k in config_b.get("assigned_kb_ids", []) if k]
            chunks_b = await retriever.retrieve(company_id=company_id, query=q, knowledge_base_ids=kb_ids_b) if kb_ids_b else []
            ctx_b = ContextBuilder().build_context(chunks_b) if chunks_b else ""
            msgs_b = PromptBuilder.build_chat_messages(
                employee_name="AI Employee B",
                role="Assistant",
                personality=config_b.get("personality", ""),
                custom_system_prompt=config_b.get("system_prompt", ""),
                context_text=ctx_b,
                has_context=len(chunks_b) > 0,
                conversation_history=[],
                current_user_query=q,
            )
            llm_b = get_llm_provider(model=config_b.get("model"))
            resp_b = await llm_b.generate(messages=msgs_b, temperature=float(config_b.get("temperature", 0.2)))
            lat_b = round((time.perf_counter() - start_b) * 1000, 2)
            usage_b = UsageAdapter.extract_usage("gemini", resp_b.usage, messages=msgs_b, generated_text=resp_b.content)

            results.append({
                "query": q,
                "config_a": {
                    "answer": resp_a.content,
                    "latency_ms": lat_a,
                    "chunks_retrieved": len(chunks_a),
                    "total_tokens": usage_a.total_tokens,
                },
                "config_b": {
                    "answer": resp_b.content,
                    "latency_ms": lat_b,
                    "chunks_retrieved": len(chunks_b),
                    "total_tokens": usage_b.total_tokens,
                },
            })

        return {
            "queries_evaluated": len(queries),
            "comparisons": results,
        }
