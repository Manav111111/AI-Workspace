import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent.policies import ToolPolicy
from app.services.agent.models import ToolCall, ToolContext, ToolErrorCode
from app.services.agent.tool_executor import ToolExecutor

def test_idempotency_key_deterministic():
    policy = ToolPolicy()
    call1 = ToolCall(name="create_lead", arguments={"name": "Alice", "email": "alice@example.com"})
    call2 = ToolCall(name="create_lead", arguments={"email": "alice@example.com", "name": "Alice"})
    
    cid = uuid.uuid4()
    conv_id = uuid.uuid4()
    # Dict key order should not change idempotency key
    key1 = policy.compute_idempotency_key(cid, conv_id, "create_lead", {"name": "Alice", "email": "alice@example.com"})
    key2 = policy.compute_idempotency_key(cid, conv_id, "create_lead", {"email": "alice@example.com", "name": "Alice"})
    assert key1 == key2
    assert len(key1) == 64

@pytest.mark.asyncio
async def test_duplicate_write_tool_returns_cached_result(db_session: AsyncSession):
    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    context = ToolContext(
        company_id=company_id,
        ai_employee_id=emp_id,
        conversation_id=conv_id,
        assigned_kb_ids=[],
    )
    executor = ToolExecutor(db_session)
    args = {"name": "Bob Prospect", "email": "bob@example.com", "source": "chat"}
    
    # 1. First execution with bypass_confirmation=True (simulating confirmed write)
    result1 = await executor.execute_tool(
        tool_name="create_lead",
        arguments=args,
        context=context,
        assigned_tool_names=["create_lead"],
        bypass_confirmation=True,
    )
    assert result1.success is True
    assert result1.data["email"] == "bob@example.com"
    
    # 2. Second execution with identical args should hit idempotency cache
    result2 = await executor.execute_tool(
        tool_name="create_lead",
        arguments=args,
        context=context,
        assigned_tool_names=["create_lead"],
        bypass_confirmation=True,
    )
    assert result2.success is True
    assert result2.data["email"] == "bob@example.com"
