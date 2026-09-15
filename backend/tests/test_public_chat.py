import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_employee import AIEmployee, AIEmployeeStatus
from app.models.ai_employee_tool import AIEmployeeTool
from app.models.business_entities import Order, OrderStatus
from app.models.company import Company
from app.models.public_usage import PublicUsageEvent
from sqlalchemy import select

@pytest.mark.asyncio
async def test_public_chat_flow_and_usage_telemetry(client: AsyncClient, db_session: AsyncSession):
    comp_id = uuid.uuid4()
    emp_id = uuid.uuid4()

    company = Company(id=comp_id, name="Public Shop", slug=f"pshop-{comp_id.hex[:6]}")
    db_session.add(company)

    # Seed an active published employee with order_lookup tool
    employee = AIEmployee(
        id=emp_id,
        company_id=comp_id,
        name="Maya Shop",
        role="Store Associate",
        status=AIEmployeeStatus.ACTIVE,
        is_published=True,
        public_id="ae_pub_shop_maya",
        widget_config={"welcome_message": "Hello!"},
    )
    db_session.add(employee)

    tool_assignment = AIEmployeeTool(
        id=uuid.uuid4(),
        company_id=comp_id,
        ai_employee_id=emp_id,
        tool_name="order_lookup",
    )
    db_session.add(tool_assignment)

    # Seed an order
    order = Order(
        id=uuid.uuid4(),
        company_id=comp_id,
        order_number="ORD-PUB-100",
        customer_identifier="visitor@example.com",
        status=OrderStatus.SHIPPED.value,
        items=[{"sku": "KB-1", "name": "Mechanical Keyboard", "qty": 1, "price": 120.0}],
        total=120.0,
    )
    db_session.add(order)
    await db_session.commit()

    # 1. Create Public Session
    session_resp = await client.post(
        "/api/v1/public/employees/ae_pub_shop_maya/sessions",
        json={"visitor_id": "vis_123"},
    )
    assert session_resp.status_code == 200
    token = session_resp.json()["session_token"]

    # 2. Send Chat Message (Order inquiry triggering tool execution)
    headers = {"Authorization": f"Bearer {token}"}
    chat_resp = await client.post(
        "/api/v1/public/sessions/messages",
        headers=headers,
        json={"message": "Where is order ORD-PUB-100?"},
    )
    assert chat_resp.status_code == 200
    res_data = chat_resp.json()
    assert "message" in res_data
    assert len(res_data["message"]) > 0

    # 3. Fetch Message History
    hist_resp = await client.get("/api/v1/public/sessions/messages", headers=headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) >= 2  # user message and assistant message

    # 4. Verify PublicUsageEvent recorded in DB
    usage_stmt = select(PublicUsageEvent).where(PublicUsageEvent.company_id == comp_id)
    usage_res = await db_session.execute(usage_stmt)
    events = usage_res.scalars().all()
    assert len(events) >= 1
    event = events[0]
    assert event.company_id == comp_id
    assert event.ai_employee_id == emp_id
    assert event.message_count == 1
