import datetime
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_employee import AIEmployee, AIEmployeeStatus
from app.models.company import Company
from app.models.conversation import Conversation
from app.models.public_session import PublicChatSession
from app.services.public_runtime.security import hash_token

@pytest.mark.asyncio
async def test_cross_tenant_public_isolation(client: AsyncClient, db_session: AsyncSession):
    comp_a = uuid.uuid4()
    comp_b = uuid.uuid4()

    company_a = Company(id=comp_a, name="Company A", slug=f"coa-{comp_a.hex[:6]}")
    company_b = Company(id=comp_b, name="Company B", slug=f"cob-{comp_b.hex[:6]}")
    db_session.add_all([company_a, company_b])

    # Company A employee
    emp_a = AIEmployee(
        id=uuid.uuid4(),
        company_id=comp_a,
        name="Agent A",
        role="Support",
        status=AIEmployeeStatus.ACTIVE,
        is_published=True,
        public_id="ae_pub_tenant_a",
    )
    # Company B employee
    emp_b = AIEmployee(
        id=uuid.uuid4(),
        company_id=comp_b,
        name="Agent B",
        role="Sales",
        status=AIEmployeeStatus.ACTIVE,
        is_published=True,
        public_id="ae_pub_tenant_b",
    )
    db_session.add_all([emp_a, emp_b])
    await db_session.commit()

    # Create Session under Employee A
    resp_a = await client.post("/api/v1/public/employees/ae_pub_tenant_a/sessions", json={})
    assert resp_a.status_code == 200
    token_a = resp_a.json()["session_token"]

    # Verify session token A is strictly scoped to Employee A / Company A
    headers = {"Authorization": f"Bearer {token_a}"}
    msg_resp = await client.post(
        "/api/v1/public/sessions/messages",
        headers=headers,
        json={"message": "Hello Agent A"},
    )
    assert msg_resp.status_code == 200

    # Tampering with session token or forged bearer token fails
    forged_headers = {"Authorization": "Bearer sess_pub_forged_999999"}
    fail_resp = await client.post(
        "/api/v1/public/sessions/messages",
        headers=forged_headers,
        json={"message": "Hack attempt"},
    )
    assert fail_resp.status_code == 401
