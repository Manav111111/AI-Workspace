import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.business_entities import SupportTicket
from app.models.pending_tool_action import PendingActionStatus, PendingToolAction
from app.services.agent.models import ToolContext, ToolErrorCode
from app.services.agent.tool_executor import ToolExecutor


@pytest.mark.asyncio
async def test_write_tool_creates_pending_action_requiring_confirmation(db_session: AsyncSession):
    """Verify that a WRITE tool halts and creates a PendingToolAction awaiting explicit confirmation."""
    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    context = ToolContext(
        company_id=company_id,
        ai_employee_id=emp_id,
        conversation_id=conv_id,
    )

    executor = ToolExecutor(db_session)

    # 1. First execution attempt without confirmation
    res = await executor.execute_tool(
        tool_name="create_support_ticket",
        arguments={"subject": "Login Failure", "description": "Cannot log in with SSO"},
        context=context,
        assigned_tool_names=["create_support_ticket"],
        bypass_confirmation=False,  # default policy requires confirmation
    )

    assert res.success is False
    assert res.error_code == ToolErrorCode.CONFIRMATION_REQUIRED
    assert res.pending_action_id is not None

    # Verify pending action is stored in the database
    stmt = select(PendingToolAction).where(PendingToolAction.id == res.pending_action_id)
    r = await db_session.execute(stmt)
    pending_action = r.scalar_one_or_none()
    assert pending_action is not None
    assert pending_action.status == PendingActionStatus.PENDING.value
    assert pending_action.tool_name == "create_support_ticket"
    assert pending_action.validated_arguments["subject"] == "Login Failure"

    # Verify that the ticket was NOT created yet
    ticket_stmt = select(SupportTicket).where(SupportTicket.company_id == company_id)
    t_res = await db_session.execute(ticket_stmt)
    assert t_res.scalar_one_or_none() is None

    # 2. User confirms execution
    confirm_res = await executor.execute_pending_action(
        pending_action_id=res.pending_action_id,
        company_id=company_id,
    )

    assert confirm_res.success is True
    assert confirm_res.data is not None
    assert "ticket_number" in confirm_res.data

    # Verify status changed to CONFIRMED
    await db_session.refresh(pending_action)
    assert pending_action.status == PendingActionStatus.CONFIRMED.value

    # Verify ticket now exists in DB
    t_res2 = await db_session.execute(ticket_stmt)
    created_ticket = t_res2.scalar_one_or_none()
    assert created_ticket is not None
    assert created_ticket.subject == "Login Failure"
