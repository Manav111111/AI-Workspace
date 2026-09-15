import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_employee import AIEmployee, AIEmployeeStatus
from app.models.company import Company

@pytest.mark.asyncio
async def test_public_employee_publishing_and_sanitized_config(client: AsyncClient, db_session: AsyncSession):
    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()

    company = Company(id=company_id, name="Public Co", slug=f"pub-{company_id.hex[:6]}")
    db_session.add(company)

    employee = AIEmployee(
        id=emp_id,
        company_id=company_id,
        name="Maya Assistant",
        role="Customer Support",
        description="Public AI Employee",
        system_prompt="TOP SECRET SYSTEM PROMPT MUST NOT LEAK",
        status=AIEmployeeStatus.ACTIVE,
        is_published=True,
        public_id="ae_pub_maya12345",
        allowed_domains=["allowed.com"],
        widget_config={"primary_color": "#4f46e5", "welcome_message": "Hello from Maya!"},
    )
    db_session.add(employee)
    await db_session.commit()

    # 1. Fetch sanitized public configuration
    resp = await client.get("/api/v1/public/employees/ae_pub_maya12345/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["public_id"] == "ae_pub_maya12345"
    assert data["name"] == "Maya Assistant"
    assert data["role"] == "Customer Support"
    assert data["widget_config"]["primary_color"] == "#4f46e5"

    # CRITICAL: Verify system_prompt, company_id, internal database IDs are NEVER leaked
    assert "system_prompt" not in data
    assert "TOP SECRET" not in str(data)
    assert "company_id" not in data
    assert str(emp_id) not in str(data)
    assert str(company_id) not in str(data)

@pytest.mark.asyncio
async def test_unpublished_employee_returns_404(client: AsyncClient, db_session: AsyncSession):
    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    company = Company(id=company_id, name="Unpublished Co", slug=f"unpub-{company_id.hex[:6]}")
    db_session.add(company)

    employee = AIEmployee(
        id=emp_id,
        company_id=company_id,
        name="Draft Agent",
        role="Draft",
        status=AIEmployeeStatus.DRAFT,
        is_published=False,  # NOT published
        public_id="ae_pub_draft999",
    )
    db_session.add(employee)
    await db_session.commit()

    resp = await client.get("/api/v1/public/employees/ae_pub_draft999/config")
    assert resp.status_code == 404
