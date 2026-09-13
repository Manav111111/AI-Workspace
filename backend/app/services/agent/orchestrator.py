from dataclasses import dataclass, field
import json
import logging
import time
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.ai_employee import AIEmployee
from app.models.business_entities import ToolExecution
from app.models.pending_tool_action import PendingActionStatus, PendingToolAction
from app.services.agent.models import ToolContext, ToolErrorCode, ToolResult
from app.services.agent.tool_executor import ToolExecutor
from app.services.agent.tool_registry import tool_registry
from app.services.context_builder import ContextBuilder
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMProvider, LLMResponse
from app.services.prompt_builder import PromptBuilder
from app.services.retrieval import RetrievalService, RetrievedChunk

logger = logging.getLogger("app.services.agent.orchestrator")


@dataclass
class AgentExecutionResult:
    content: str
    tool_calls_executed: List[Dict[str, Any]] = field(default_factory=list)
    pending_confirmation: Optional[Dict[str, Any]] = None
    citations: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_chunks: List[RetrievedChunk] = field(default_factory=list)
    retrieval_metadata: Dict[str, Any] = field(default_factory=dict)
    iterations: int = 1
    metrics: Dict[str, Any] = field(default_factory=dict)


class AgentOrchestrator:
    """Orchestrates bounded multi-turn agent execution combining RAG, assigned tools, and memory.
    Ensures:
    - AI Employee only uses assigned tools
    - Scoped RAG retrieval matches assigned knowledge bases
    - Write tools trigger PendingToolAction confirmation
    - Bounded execution loop (AGENT_MAX_ITERATIONS)
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: Optional[LLMProvider] = None,
        retrieval_service: Optional[RetrievalService] = None,
        context_builder: Optional[ContextBuilder] = None,
    ):
        self.session = session
        self.llm_provider = llm_provider or get_llm_provider()
        self.retrieval_service = retrieval_service or RetrievalService()
        self.context_builder = context_builder or ContextBuilder()
        self.tool_executor = ToolExecutor(session)

    async def execute(
        self,
        company_id: uuid.UUID,
        ai_employee: AIEmployee,
        conversation_id: uuid.UUID,
        user_query: str,
        conversation_history: List[Dict[str, str]],
        user_id: Optional[uuid.UUID] = None,
        pending_action_id: Optional[uuid.UUID] = None,
        confirm_action: bool = False,
    ) -> AgentExecutionResult:
        total_start = time.perf_counter()

        # 1. Handle Explicit User Confirmation of a Pending Action
        if pending_action_id:
            if confirm_action:
                exec_res = await self.tool_executor.execute_pending_action(
                    pending_action_id=pending_action_id,
                    company_id=company_id,
                    user_id=user_id,
                )
                if exec_res.success:
                    reply = exec_res.display_message or "The action has been successfully confirmed and executed."
                else:
                    reply = f"Unable to execute action: {exec_res.error or exec_res.display_message}"

                return AgentExecutionResult(
                    content=reply,
                    tool_calls_executed=[{
                        "pending_action_id": str(pending_action_id),
                        "success": exec_res.success,
                        "result": exec_res.data,
                    }],
                    iterations=1,
                    metrics={"total_latency_ms": round((time.perf_counter() - total_start) * 1000, 2)},
                )
            else:
                # Cancel pending action
                stmt = select(PendingToolAction).where(PendingToolAction.id == pending_action_id)
                r = await self.session.execute(stmt)
                pa = r.scalar_one_or_none()
                if pa and pa.company_id == company_id:
                    pa.status = PendingActionStatus.REJECTED.value
                    await self.session.flush()

                return AgentExecutionResult(
                    content="The requested action has been cancelled.",
                    iterations=1,
                    metrics={"total_latency_ms": round((time.perf_counter() - total_start) * 1000, 2)},
                )

        # 2. Extract Assigned Knowledge Bases & Scoped Retrieval
        assigned_kbs = getattr(ai_employee, "knowledge_bases", []) or []
        assigned_kb_ids = [kb.id for kb in assigned_kbs]

        retrieval_start = time.perf_counter()
        if assigned_kb_ids:
            retrieved_chunks = await self.retrieval_service.retrieve(
                company_id=company_id,
                query=user_query,
                knowledge_base_ids=assigned_kb_ids,
            )
            retrieval_latency_ms = round((time.perf_counter() - retrieval_start) * 1000, 2)
        else:
            retrieved_chunks = []
            retrieval_latency_ms = 0.0
        retrieval_metadata = {
            "query": user_query,
            "assigned_kbs_count": len(assigned_kb_ids),
            "assigned_kb_ids": [str(k) for k in assigned_kb_ids],
            "retrieval_skipped": len(assigned_kb_ids) == 0,
            "chunks_retrieved": len(retrieved_chunks),
            "top_score": round(retrieved_chunks[0].score, 4) if retrieved_chunks else 0.0,
            "retrieval_latency_ms": retrieval_latency_ms,
        }

        has_context = len(retrieved_chunks) > 0
        context_text = self.context_builder.build_context(retrieved_chunks) if has_context else ""

        # 3. Extract Assigned Tools & Format Tool Definitions for LLM
        assigned_tools_rel = getattr(ai_employee, "assigned_tools", []) or []
        assigned_tool_names = [t.tool_name for t in assigned_tools_rel]
        assigned_tool_objs = tool_registry.get_tools_for_employee(assigned_tool_names)

        tools_def: Optional[List[Dict[str, Any]]] = None
        if assigned_tool_objs:
            tools_def = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                }
                for tool in assigned_tool_objs
            ]

        # 4. Build Initial Messages
        messages = PromptBuilder.build_chat_messages(
            employee_name=ai_employee.name,
            role=ai_employee.role,
            personality=ai_employee.personality,
            custom_system_prompt=ai_employee.system_prompt,
            context_text=context_text,
            has_context=has_context,
            conversation_history=conversation_history,
            current_user_query=user_query,
        )

        tool_context = ToolContext(
            company_id=company_id,
            ai_employee_id=ai_employee.id,
            conversation_id=conversation_id,
            user_id=user_id,
            assigned_kb_ids=assigned_kb_ids,
        )

        # 5. Bounded Agent Loop
        tool_calls_executed: List[Dict[str, Any]] = []
        pending_confirmation: Optional[Dict[str, Any]] = None
        final_text = ""
        iterations = 0
        total_llm_latency_ms = 0.0
        max_iterations = getattr(settings, "AGENT_MAX_ITERATIONS", 5)

        while iterations < max_iterations:
            iterations += 1

            llm_start = time.perf_counter()
            llm_response: LLMResponse = await self.llm_provider.generate(
                messages=messages,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                tools=tools_def,
            )
            total_llm_latency_ms += round((time.perf_counter() - llm_start) * 1000, 2)

            # Check if LLM requested tool calls
            if llm_response.tool_calls:
                # Add assistant message with tool calls to history
                assistant_tool_msg = {
                    "role": "assistant",
                    "content": llm_response.content or "",
                    "tool_calls": llm_response.tool_calls,
                }
                messages.append(assistant_tool_msg)

                for tc in llm_response.tool_calls:
                    fn = tc.get("function", {})
                    fn_name = fn.get("name", "")
                    fn_args_raw = fn.get("arguments", "{}")

                    try:
                        args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
                    except Exception:
                        args = {}

                    tool_res: ToolResult = await self.tool_executor.execute_tool(
                        tool_name=fn_name,
                        arguments=args,
                        context=tool_context,
                        assigned_tool_names=assigned_tool_names,
                    )

                    # Check if action requires user confirmation
                    if tool_res.error_code == ToolErrorCode.CONFIRMATION_REQUIRED:
                        pending_confirmation = {
                            "pending_action_id": str(tool_res.pending_action_id),
                            "tool_name": fn_name,
                            "arguments": args,
                            "message": tool_res.display_message,
                        }
                        final_text = (
                            tool_res.display_message
                            or f"I am preparing to execute {fn_name}. Please confirm to proceed."
                        )
                        tool_calls_executed.append({
                            "name": fn_name,
                            "arguments": args,
                            "status": "CONFIRMATION_REQUIRED",
                            "pending_action_id": str(tool_res.pending_action_id),
                        })
                        break

                    # Append tool result to context
                    res_payload = tool_res.data if tool_res.success else {"error": tool_res.error, "code": tool_res.error_code}
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", str(uuid.uuid4())),
                        "name": fn_name,
                        "content": json.dumps(res_payload),
                    })

                    tool_calls_executed.append({
                        "name": fn_name,
                        "arguments": args,
                        "success": tool_res.success,
                        "result": res_payload,
                    })

                # If confirmation is required, halt iteration immediately
                if pending_confirmation:
                    break

            else:
                # No tool calls requested, LLM produced final answer
                final_text = llm_response.content
                break

        # Fallback if loop exhausted without final text
        if not final_text and not pending_confirmation:
            final_text = "I have processed your request."

        # 6. Extract Citations from Retrieved Chunks
        citations = []
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

        total_latency_ms = round((time.perf_counter() - total_start) * 1000, 2)
        metrics = {
            "retrieval_latency_ms": retrieval_latency_ms,
            "llm_latency_ms": round(total_llm_latency_ms, 2),
            "total_latency_ms": total_latency_ms,
            "chunks_retrieved": len(retrieved_chunks),
            "iterations": iterations,
            "tool_calls_count": len(tool_calls_executed),
        }

        return AgentExecutionResult(
            content=final_text,
            tool_calls_executed=tool_calls_executed,
            pending_confirmation=pending_confirmation,
            citations=citations,
            retrieved_chunks=retrieved_chunks,
            retrieval_metadata=retrieval_metadata,
            iterations=iterations,
            metrics=metrics,
        )
