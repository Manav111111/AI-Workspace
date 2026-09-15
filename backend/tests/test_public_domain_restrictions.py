import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_employee import AIEmployee, AIEmployeeStatus
from app.models.company import Company

@pytest.mark.asyncio
async def test_domain_restriction_enforcement(client: AsyncClient, db_session: AsyncSession):
    comp_id = uuid.uuid4()
    emp_id = uuid.uuid4()

    company = Company(id=comp_id, name="Domain Co", slug=f"dom-{comp_id.hex[:6]}")
    db_session.add(company)

    # Employee configured with strict allowed_domains
    employee = AIEmployee(
        id=emp_id,
        company_id=comp_id,
        name="Domain Maya",
        role="Support",
        status=AIEmployeeStatus.ACTIVE,
        is_published=True,
        public_id="ae_pub_domain_strict",
        allowed_domains=["shop.mybrand.com", "mybrand.com"],
    )
    db_session.add(employee)
    await db_session.commit()

    # 1. Request from authorized origin succeeds
    auth_headers = {"Origin": "https://shop.mybrand.com"}
    ok_resp = await client.get("/api/v1/public/employees/ae_pub_domain_strict/config", headers=auth_headers)
    assert ok_resp.status_code == 200

    # 2. Localhost development origin succeeds
    local_headers = {"Origin": "http://localhost:3000"}
    local_resp = await client.get("/api/v1/public/employees/ae_pub_domain_strict/config", headers=local_headers)
    assert local_resp.status_code == 200

    # 3. Unauthorized origin rejected with 403 Forbidden
    evil_headers = {"Origin": "https://malicious-scam-site.com"}
    block_resp = await client.get("/api/v1/public/employees/ae_pub_domain_strict/config", headers=evil_headers)
    assert block_resp.status_code == 403
    assert "not authorized" in block_resp.text.lower()
