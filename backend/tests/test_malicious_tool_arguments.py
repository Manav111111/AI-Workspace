import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent.models import ToolContext, ToolErrorCode
from app.services.agent.tool_executor import ToolExecutor
from app.models.business_entities import Lead
from sqlalchemy import select

@pytest.mark.asyncio
async def test_malicious_extra_parameters_stripped_or_rejected(db_session: AsyncSession):
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
    
    # Missing required argument
    result = await executor.execute_tool(
        tool_name="order_lookup",
        arguments={},
        context=context,
        assigned_tool_names=["order_lookup"],
    )
    assert result.success is False
    assert result.error_code == ToolErrorCode.VALIDATION_ERROR

@pytest.mark.asyncio
async def test_tool_caller_cannot_spoof_tenant_context(db_session: AsyncSession):
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
    
    # Attempting to supply a spoofed company_id in tool arguments
    spoofed_company_id = str(uuid.uuid4())
    result = await executor.execute_tool(
        tool_name="create_lead",
        arguments={
            "name": "Attacker",
            "email": "attacker@example.com",
            "company_id": spoofed_company_id,
        },
        context=context,
        assigned_tool_names=["create_lead"],
        bypass_confirmation=True,
    )
    assert result.success is True
    # The lead must be created under context.company_id, NOT spoofed_company_id
    lead_id = uuid.UUID(result.data["lead_id"])
    stmt = select(Lead).where(Lead.id == lead_id)
    res = await db_session.execute(stmt)
    lead = res.scalar_one()
    assert lead.company_id == company_id
    assert str(lead.company_id) != spoofed_company_id
