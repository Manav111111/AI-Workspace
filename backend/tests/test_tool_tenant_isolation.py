import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.business_entities import Order, OrderStatus
from app.services.agent.models import ToolContext, ToolErrorCode
from app.services.agent.tool_executor import ToolExecutor


@pytest.mark.asyncio
async def test_cross_tenant_order_lookup_strictly_isolated(db_session: AsyncSession):
    """Verify that Company A cannot look up orders created under Company B."""
    company_a_id = uuid.uuid4()
    company_b_id = uuid.uuid4()

    # Company B has an order ORD-SECRET-B
    order_b = Order(
        company_id=company_b_id,
        order_number="ORD-SECRET-B",
        customer_identifier="vip@companyb.com",
        status=OrderStatus.PROCESSING.value,
        items=[{"name": "Confidential Prototype", "qty": 1, "price": 9999.0}],
        total=9999.0,
    )
    db_session.add(order_b)
    await db_session.commit()

    # Company A AI Employee attempts to query ORD-SECRET-B
    context_a = ToolContext(
        company_id=company_a_id,
        ai_employee_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
    )

    executor = ToolExecutor(db_session)

    res = await executor.execute_tool(
        tool_name="order_lookup",
        arguments={"order_number": "ORD-SECRET-B"},
        context=context_a,
        assigned_tool_names=["order_lookup"],
    )

    # Must fail with RESOURCE_NOT_FOUND (Company A cannot see Company B's order)
    assert res.success is False
    assert res.error_code == ToolErrorCode.RESOURCE_NOT_FOUND
    assert res.data is None
