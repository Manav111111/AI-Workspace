import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_employee import AIEmployee, AIEmployeeStatus
from app.models.ai_employee_tool import AIEmployeeTool
from app.models.company import Company
from app.models.pending_tool_action import PendingActionStatus, PendingToolAction
from sqlalchemy import select

@pytest.mark.asyncio
async def test_public_write_tool_requires_confirmation(client: AsyncClient, db_session: AsyncSession):
    comp_id = uuid.uuid4()
    emp_id = uuid.uuid4()

    company = Company(id=comp_id, name="Public Lead Co", slug=f"plead-{comp_id.hex[:6]}")
    db_session.add(company)

    # Employee assigned create_lead (WRITE tool requiring confirmation)
    employee = AIEmployee(
        id=emp_id,
        company_id=comp_id,
        name="Lead Bot",
        role="Sales",
        status=AIEmployeeStatus.ACTIVE,
        is_published=True,
        public_id="ae_pub_lead_bot",
    )
    db_session.add(employee)

    tool_assignment = AIEmployeeTool(
        id=uuid.uuid4(),
        company_id=comp_id,
        ai_employee_id=emp_id,
        tool_name="create_lead",
    )
    db_session.add(tool_assignment)
    await db_session.commit()

    # 1. Start public session
    sess_resp = await client.post("/api/v1/public/employees/ae_pub_lead_bot/sessions", json={})
    assert sess_resp.status_code == 200
    token = sess_resp.json()["session_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Trigger lead creation: "Please collect my lead: Alice at alice@example.com"
    msg_resp = await client.post(
        "/api/v1/public/sessions/messages",
        headers=headers,
        json={"message": "Please capture my lead: Alice at alice@example.com"},
    )
    assert msg_resp.status_code == 200
    res_data = msg_resp.json()

    # 3. Must yield a pending_confirmation payload requiring user approval
    assert res_data.get("pending_confirmation") is not None
    pending_conf = res_data["pending_confirmation"]
    action_id = pending_conf["pending_action_id"]
    assert pending_conf["tool_name"] == "create_lead"

    # Verify pending action recorded server-side
    action_stmt = select(PendingToolAction).where(PendingToolAction.id == uuid.UUID(action_id))
    action_res = await db_session.execute(action_stmt)
    pending_record = action_res.scalar_one()
    assert pending_record.status == PendingActionStatus.PENDING.value

    # 4. Confirm the pending action via public chat endpoint
    confirm_resp = await client.post(
        "/api/v1/public/sessions/messages",
        headers=headers,
        json={
            "message": "Yes, proceed with lead creation",
            "pending_action_id": action_id,
            "confirm_action": True,
        },
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["pending_confirmation"] is None

    # Verify record transitioned to CONFIRMED
    await db_session.refresh(pending_record)
    assert pending_record.status == PendingActionStatus.CONFIRMED.value
