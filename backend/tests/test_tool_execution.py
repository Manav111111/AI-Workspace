import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.business_entities import Order, OrderStatus
from app.services.agent.models import ToolContext, ToolErrorCode
from app.services.agent.tool_executor import ToolExecutor


@pytest.mark.asyncio
async def test_order_lookup_tool_execution(db_session: AsyncSession):
    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    # Seed an order under company_id
    order = Order(
        company_id=company_id,
        order_number="ORD-9999",
        customer_identifier="customer@example.com",
        status=OrderStatus.SHIPPED.value,
        items=[{"sku": "LAPTOP-01", "name": "AI Developer Laptop", "qty": 1, "price": 1499.0}],
        total=1499.0,
    )
    db_session.add(order)
    await db_session.commit()

    context = ToolContext(
        company_id=company_id,
        ai_employee_id=emp_id,
        conversation_id=conv_id,
    )

    executor = ToolExecutor(db_session)

    # 1. Lookup by order_number
    res = await executor.execute_tool(
        tool_name="order_lookup",
        arguments={"order_number": "ORD-9999"},
        context=context,
        assigned_tool_names=["order_lookup"],
    )
    assert res.success is True
    assert res.data is not None
    assert res.data["order_number"] == "ORD-9999"
    assert res.data["status"] == "SHIPPED"
    assert res.data["total"] == 1499.0

    # 2. Lookup by customer_identifier
    res_cust = await executor.execute_tool(
        tool_name="order_lookup",
        arguments={"customer_identifier": "customer@example.com"},
        context=context,
        assigned_tool_names=["order_lookup"],
    )
    assert res_cust.success is True
    assert res_cust.data["order_number"] == "ORD-9999"

    # 3. Lookup non-existent order
    res_missing = await executor.execute_tool(
        tool_name="order_lookup",
        arguments={"order_number": "ORD-0000"},
        context=context,
        assigned_tool_names=["order_lookup"],
    )
    assert res_missing.success is False
    assert res_missing.error_code == ToolErrorCode.RESOURCE_NOT_FOUND


@pytest.mark.asyncio
async def test_create_lead_tool_execution(db_session: AsyncSession):
    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    context = ToolContext(
        company_id=company_id,
        ai_employee_id=emp_id,
        conversation_id=conv_id,
    )

    executor = ToolExecutor(db_session)

    # Execute with bypass_confirmation=True (simulating confirmed execution)
    res = await executor.execute_tool(
        tool_name="create_lead",
        arguments={
            "name": "Sarah Connor",
            "email": "sarah@cyberdyne.com",
            "phone": "+1-555-0199",
            "interest": "AI Infrastructure",
        },
        context=context,
        assigned_tool_names=["create_lead"],
        bypass_confirmation=True,
    )

    assert res.success is True
    assert res.data is not None
    assert res.data["name"] == "Sarah Connor"
    assert res.data["email"] == "sarah@cyberdyne.com"
    assert "lead_id" in res.data


@pytest.mark.asyncio
async def test_create_support_ticket_execution(db_session: AsyncSession):
    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    context = ToolContext(
        company_id=company_id,
        ai_employee_id=emp_id,
        conversation_id=conv_id,
    )

    executor = ToolExecutor(db_session)

    res = await executor.execute_tool(
        tool_name="create_support_ticket",
        arguments={
            "subject": "Screen Flicker on Boot",
            "description": "The laptop screen flickers for 5 seconds when booting up.",
            "priority": "medium",
            "customer_email": "user@test.com",
        },
        context=context,
        assigned_tool_names=["create_support_ticket"],
        bypass_confirmation=True,
    )

    assert res.success is True
    assert res.data is not None
    assert res.data["subject"] == "Screen Flicker on Boot"
    assert res.data["priority"] == "MEDIUM"
    assert res.data["ticket_number"].startswith("TCK-")
