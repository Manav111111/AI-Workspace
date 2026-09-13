import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent.models import ToolContext, ToolErrorCode
from app.services.agent.tool_executor import ToolExecutor


@pytest.mark.asyncio
async def test_unassigned_tool_invocation_rejected(db_session: AsyncSession):
    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    context = ToolContext(
        company_id=company_id,
        ai_employee_id=emp_id,
        conversation_id=conv_id,
    )

    executor = ToolExecutor(db_session)

    # Employee is only assigned "product_search"
    # Attempt to invoke "order_lookup"
    res = await executor.execute_tool(
        tool_name="order_lookup",
        arguments={"order_number": "ORD-1234"},
        context=context,
        assigned_tool_names=["product_search"],  # order_lookup not assigned!
    )

    assert res.success is False
    assert res.error_code == ToolErrorCode.TOOL_NOT_ASSIGNED
    assert "not have access" in res.error.lower() or "not assigned" in res.error.lower()


@pytest.mark.asyncio
async def test_unregistered_tool_invocation_rejected(db_session: AsyncSession):
    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    context = ToolContext(
        company_id=company_id,
        ai_employee_id=emp_id,
        conversation_id=conv_id,
    )

    executor = ToolExecutor(db_session)

    # Attempt to invoke an arbitrary non-existent tool
    res = await executor.execute_tool(
        tool_name="arbitrary_code_runner",
        arguments={"code": "import os; os.system('ls')"},
        context=context,
        assigned_tool_names=["arbitrary_code_runner"],
    )

    assert res.success is False
    assert res.error_code == ToolErrorCode.TOOL_NOT_ASSIGNED
    assert "not registered" in res.error.lower()
