import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_employee import AIEmployee, AIEmployeeStatus
from app.models.company import Company
from app.services.public_runtime.rate_limit import rate_limiter

@pytest.mark.asyncio
async def test_public_rate_limiting_enforcement(client: AsyncClient, db_session: AsyncSession):
    comp_id = uuid.uuid4()
    emp_id = uuid.uuid4()

    company = Company(id=comp_id, name="Rate Co", slug=f"rate-{comp_id.hex[:6]}")
    db_session.add(company)

    employee = AIEmployee(
        id=emp_id,
        company_id=comp_id,
        name="Rate Bot",
        role="Tester",
        status=AIEmployeeStatus.ACTIVE,
        is_published=True,
        public_id="ae_pub_rate_bot",
    )
    db_session.add(employee)
    await db_session.commit()

    # Pre-flood rate limit window for test key to verify 429 response
    test_ip = "192.168.1.100"
    for _ in range(25):
        rate_limiter.is_allowed(f"session_create_{test_ip}", max_requests=20, window_seconds=60)

    # Make request with X-Forwarded-For: test_ip
    resp = await client.post(
        "/api/v1/public/employees/ae_pub_rate_bot/sessions",
        headers={"x-forwarded-for": test_ip},
        json={},
    )
    assert resp.status_code == 429
    assert "rate limit exceeded" in resp.text.lower()
