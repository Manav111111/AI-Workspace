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
async def test_create_and_resume_public_session(client: AsyncClient, db_session: AsyncSession):
    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()

    company = Company(id=company_id, name="Sess Co", slug=f"sess-{company_id.hex[:6]}")
    db_session.add(company)

    employee = AIEmployee(
        id=emp_id,
        company_id=company_id,
        name="Support Maya",
        role="Assistant",
        status=AIEmployeeStatus.ACTIVE,
        is_published=True,
        public_id="ae_pub_sess1",
    )
    db_session.add(employee)
    await db_session.commit()

    # 1. Create a public session
    resp = await client.post(
        "/api/v1/public/employees/ae_pub_sess1/sessions",
        json={"visitor_id": "visitor_client_abc"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "session_token" in data
    assert data["session_token"].startswith("sess_pub_")
    token1 = data["session_token"]

    # 2. Resuming session with identical visitor_id
    resp2 = await client.post(
        "/api/v1/public/employees/ae_pub_sess1/sessions",
        json={"visitor_id": "visitor_client_abc"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "session_token" in data2

@pytest.mark.asyncio
async def test_session_ownership_invariant_violation_rejected(client: AsyncClient, db_session: AsyncSession):
    """Verify that a session mismatched with a conversation from another tenant or employee is rejected with 403."""
    comp_a = uuid.uuid4()
    comp_b = uuid.uuid4()
    emp_a = uuid.uuid4()
    emp_b = uuid.uuid4()

    company_a = Company(id=comp_a, name="Co A", slug=f"coa-{comp_a.hex[:6]}")
    company_b = Company(id=comp_b, name="Co B", slug=f"cob-{comp_b.hex[:6]}")
    db_session.add_all([company_a, company_b])

    employee_a = AIEmployee(id=emp_a, company_id=comp_a, name="Emp A", role="A", status=AIEmployeeStatus.ACTIVE, is_published=True, public_id="ae_pub_a")
    employee_b = AIEmployee(id=emp_b, company_id=comp_b, name="Emp B", role="B", status=AIEmployeeStatus.ACTIVE, is_published=True, public_id="ae_pub_b")
    db_session.add_all([employee_a, employee_b])

    # Conversation belongs to Company B / Employee B
    conv_b = Conversation(id=uuid.uuid4(), company_id=comp_b, ai_employee_id=emp_b, title="B chat")
    db_session.add(conv_b)

    # Malicious/Tampered Session claims Company A / Employee A, but points to Conversation B
    raw_token = "sess_pub_malicious_token"
    mismatched_session = PublicChatSession(
        id=uuid.uuid4(),
        company_id=comp_a,
        ai_employee_id=emp_a,
        conversation_id=conv_b.id,  # Mismatched!
        token_hash=hash_token(raw_token),
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
    )
    db_session.add(mismatched_session)
    await db_session.commit()

    # Request using the mismatched token must fail with 403 Session Invariant Violation
    headers = {"Authorization": f"Bearer {raw_token}"}
    resp = await client.post(
        "/api/v1/public/sessions/messages",
        headers=headers,
        json={"message": "Exploit attempt"},
    )
    assert resp.status_code == 403
    assert "invariant" in resp.text.lower()
