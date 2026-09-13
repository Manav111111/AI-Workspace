import uuid
from unittest.mock import AsyncMock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent.orchestrator import AgentOrchestrator
from app.services.llm.base import LLMResponse
from app.services.agent.models import ToolCall
from app.models.ai_employee import AIEmployee
from app.models.ai_employee_tool import AIEmployeeTool

@pytest.mark.asyncio
async def test_agent_orchestrator_bounds_iterations(db_session: AsyncSession):
    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    # Create dummy employee
    employee = AIEmployee(
        id=emp_id,
        company_id=company_id,
        name="Test Agent",
        role="Support Agent",
        status="ACTIVE",
    )
    db_session.add(employee)

    # Assign tool to employee
    tool_assignment = AIEmployeeTool(
        id=uuid.uuid4(),
        company_id=company_id,
        ai_employee_id=emp_id,
        tool_name="order_lookup",
    )
    db_session.add(tool_assignment)
    await db_session.commit()

    # Re-fetch or pass employee with assigned_tools and knowledge_bases
    await db_session.refresh(employee, attribute_names=["assigned_tools", "knowledge_bases"])

    # Mock LLM that endlessly emits tool calls to test max iterations bounding
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = LLMResponse(
        content="Let me look that up again...",
        model="mock-gpt",
        tool_calls=[{
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "order_lookup",
                "arguments": "{\"order_number\": \"ORD-LOOP\"}",
            },
        }],
    )

    orchestrator = AgentOrchestrator(session=db_session, llm_provider=mock_llm)

    result = await orchestrator.execute(
        company_id=company_id,
        ai_employee=employee,
        conversation_id=conv_id,
        user_query="Find my order",
        conversation_history=[],
    )

    # Check that iterations is bounded (default AGENT_MAX_ITERATIONS = 5)
    assert result.iterations <= 5
    assert mock_llm.generate.call_count <= 5
