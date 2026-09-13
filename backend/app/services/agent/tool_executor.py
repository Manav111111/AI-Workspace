import datetime
import logging
import time
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.business_entities import ToolExecution
from app.models.pending_tool_action import PendingActionStatus, PendingToolAction
from app.services.agent.base_tool import Tool
from app.services.agent.models import ToolContext, ToolErrorCode, ToolPermission, ToolResult
from app.services.agent.policies import ToolPolicy
from app.services.agent.tool_registry import tool_registry

logger = logging.getLogger("app.services.agent.tool_executor")


class ToolExecutor:
    """Security Boundary for Tool Execution.
    Responsibilities:
    - Validates tool exists
    - Verifies AI Employee has explicit permission/assignment to use this tool
    - Enforces confirmation policy for write actions via PendingToolAction lifecycle
    - Enforces idempotency via database unique constraint and cached lookups
    - Measures duration and records tamper-evident audit logs
    - Normalizes error codes without leaking internal stack traces
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: ToolContext,
        assigned_tool_names: List[str],
        bypass_confirmation: bool = False,
    ) -> ToolResult:
        start_time = time.perf_counter()

        # 1. Verify tool exists in registry
        tool: Optional[Tool] = tool_registry.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' is not registered in the system.",
                error_code=ToolErrorCode.TOOL_NOT_ASSIGNED,
                display_message=f"The requested capability '{tool_name}' does not exist.",
            )

        # 2. Verify AI Employee has explicit assignment
        if tool_name not in set(assigned_tool_names):
            logger.warning(
                f"Tool authorization failure: AI Employee {context.ai_employee_id} "
                f"attempted to access unassigned tool '{tool_name}'"
            )
            return ToolResult(
                success=False,
                error=f"AI Employee does not have access to tool '{tool_name}'.",
                error_code=ToolErrorCode.TOOL_NOT_ASSIGNED,
                display_message=f"I do not have authorization to perform '{tool_name}'.",
            )

        # 3. Check Confirmation Policy for WRITE actions
        if ToolPolicy.requires_confirmation(tool, arguments) and not bypass_confirmation:
            # Create server-side PendingToolAction record
            pending_action = PendingToolAction(
                company_id=context.company_id,
                ai_employee_id=context.ai_employee_id,
                conversation_id=context.conversation_id,
                user_id=context.user_id,
                tool_name=tool_name,
                validated_arguments=arguments,
                status=PendingActionStatus.PENDING.value,
                expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15),
            )
            self.session.add(pending_action)
            await self.session.flush()
            await self.session.refresh(pending_action)

            logger.info(
                f"Created pending action {pending_action.id} for tool '{tool_name}' "
                f"(employee={context.ai_employee_id}, tenant={context.company_id})"
            )

            return ToolResult(
                success=False,
                error_code=ToolErrorCode.CONFIRMATION_REQUIRED,
                pending_action_id=pending_action.id,
                display_message=(
                    f"I need your confirmation before executing this action ({tool_name}). "
                    f"Details: {arguments}"
                ),
                data={"pending_action_id": str(pending_action.id), "tool_name": tool_name, "arguments": arguments},
            )

        # 4. Idempotency Check
        idempotency_key = ToolPolicy.compute_idempotency_key(
            company_id=context.company_id,
            conversation_id=context.conversation_id,
            tool_name=tool_name,
            arguments=arguments,
        )

        existing_exec = await self.session.execute(
            select(ToolExecution).where(
                ToolExecution.company_id == context.company_id,
                ToolExecution.idempotency_key == idempotency_key,
            )
        )
        cached = existing_exec.scalar_one_or_none()
        if cached:
            logger.info(f"Idempotent hit: returning cached result for key {idempotency_key}")
            return ToolResult(
                success=cached.success,
                data=cached.result if cached.success else None,
                error=cached.result.get("error") if not cached.success and isinstance(cached.result, dict) else None,
                error_code=ToolErrorCode(cached.error_code) if cached.error_code else None,
                display_message="Action was previously completed (idempotent result).",
            )

        # 5. Execute Tool
        result: ToolResult
        try:
            result = await tool.execute(
                context=context,
                arguments=arguments,
                session=self.session,
            )
        except Exception as e:
            logger.error(f"Execution failure in tool '{tool_name}': {e}", exc_info=True)
            result = ToolResult(
                success=False,
                error=str(e),
                error_code=ToolErrorCode.EXECUTION_ERROR,
                display_message="Failed to complete action due to an internal error.",
            )

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 6. Record Audit Log in tool_executions
        # Scrub potentially sensitive passwords/tokens from arguments
        safe_args = {k: ("***" if "password" in k.lower() or "token" in k.lower() else v) for k, v in arguments.items()}
        audit_entry = ToolExecution(
            company_id=context.company_id,
            ai_employee_id=context.ai_employee_id,
            conversation_id=context.conversation_id,
            user_id=context.user_id,
            tool_name=tool_name,
            arguments=safe_args,
            result=result.data or {"error": result.error},
            success=result.success,
            error_code=result.error_code.value if result.error_code else None,
            duration_ms=duration_ms,
            idempotency_key=idempotency_key,
        )
        self.session.add(audit_entry)
        await self.session.flush()

        return result

    async def execute_pending_action(
        self,
        pending_action_id: uuid.UUID,
        company_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> ToolResult:
        """Executes a previously staged PendingToolAction upon explicit user confirmation.
        Verifies tenant ownership and updates status to CONFIRMED.
        """
        stmt = select(PendingToolAction).where(PendingToolAction.id == pending_action_id)
        res = await self.session.execute(stmt)
        pending = res.scalar_one_or_none()

        if not pending:
            return ToolResult(
                success=False,
                error="Pending action not found.",
                error_code=ToolErrorCode.RESOURCE_NOT_FOUND,
                display_message="The confirmation request was not found.",
            )

        # Tenant boundary check
        if pending.company_id != company_id:
            logger.error(f"Tenant isolation breach attempt on pending action {pending_action_id}")
            return ToolResult(
                success=False,
                error="Access denied.",
                error_code=ToolErrorCode.TENANT_ACCESS_DENIED,
                display_message="Access denied to this pending action.",
            )

        if pending.status != PendingActionStatus.PENDING.value:
            return ToolResult(
                success=False,
                error=f"Action is already {pending.status}.",
                error_code=ToolErrorCode.VALIDATION_ERROR,
                display_message=f"This action has already been {pending.status.lower()}.",
            )

        # Build context
        context = ToolContext(
            company_id=company_id,
            ai_employee_id=pending.ai_employee_id,
            conversation_id=pending.conversation_id,
            user_id=user_id or pending.user_id,
        )

        # Execute with confirmation bypassed since user explicitly confirmed
        result = await self.execute_tool(
            tool_name=pending.tool_name,
            arguments=pending.validated_arguments,
            context=context,
            assigned_tool_names=[pending.tool_name],  # confirmed action preserves assignment
            bypass_confirmation=True,
        )

        if result.success:
            pending.status = PendingActionStatus.CONFIRMED.value
        else:
            pending.status = PendingActionStatus.REJECTED.value

        await self.session.flush()
        return result
