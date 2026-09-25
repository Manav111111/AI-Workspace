import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.membership import Membership, MembershipRole
from app.models.user import User
from app.services.rate_limit import (
    DistributedRateLimiter,
    RateLimitException,
    RateLimitResult,
    distributed_rate_limiter,
)


def test_distributed_rate_limiter_sliding_window_allow_and_deny():
    # Use isolated limiter instance with dummy URL to test local fallback sliding window
    limiter = DistributedRateLimiter(redis_url="redis://nonexistent-host:6379/0", timeout_seconds=0.1)

    key = f"test_window_{uuid.uuid4().hex}"
    max_requests = 3
    window_seconds = 60

    # 1. First 3 requests must be allowed
    r1 = limiter.is_allowed(key, max_requests, window_seconds)
    assert r1.allowed is True
    assert r1.remaining == 2

    r2 = limiter.is_allowed(key, max_requests, window_seconds)
    assert r2.allowed is True
    assert r2.remaining == 1

    r3 = limiter.is_allowed(key, max_requests, window_seconds)
    assert r3.allowed is True
    assert r3.remaining == 0

    # 2. 4th request must be denied with positive retry_after
    r4 = limiter.is_allowed(key, max_requests, window_seconds)
    assert r4.allowed is False
    assert r4.remaining == 0
    assert r4.retry_after > 0


def test_rate_limiter_fail_closed_mode():
    limiter = DistributedRateLimiter(redis_url="redis://nonexistent-host:6379/0", timeout_seconds=0.1)
    key = f"fail_closed_{uuid.uuid4().hex}"

    # With fail_mode="fail_closed" and Redis unreachable, request must be rejected
    res = limiter.is_allowed(key, max_requests=10, window_seconds=60, fail_mode="fail_closed")
    assert res.allowed is False
    assert res.retry_after > 0


def test_rate_limit_exception_structure():
    limiter = DistributedRateLimiter(redis_url="redis://nonexistent-host:6379/0", timeout_seconds=0.1)
    key = f"exc_{uuid.uuid4().hex}"

    # Consume all slots
    for _ in range(2):
        limiter.is_allowed(key, max_requests=2, window_seconds=60)

    # Calling check_limit must raise RateLimitException with HTTP 429
    with pytest.raises(RateLimitException) as exc_info:
        limiter.check_limit(key, max_requests=2, window_seconds=60, action_name="test action")

    exc = exc_info.value
    assert exc.status_code == 429
    assert exc.headers.get("Retry-After") is not None
    assert exc.detail["error"] == "RATE_LIMITED"
    assert "retry_after_seconds" in exc.detail


def test_multi_tenant_key_isolation_in_rate_limiter():
    limiter = DistributedRateLimiter(redis_url="redis://nonexistent-host:6379/0", timeout_seconds=0.1)

    tenant_a_key = f"rl:ingest:upl:tenant_{uuid.uuid4().hex}"
    tenant_b_key = f"rl:ingest:upl:tenant_{uuid.uuid4().hex}"

    # Tenant A consumes all 2 slots
    limiter.is_allowed(tenant_a_key, max_requests=2, window_seconds=60)
    limiter.is_allowed(tenant_a_key, max_requests=2, window_seconds=60)

    # Tenant A is now blocked
    res_a = limiter.is_allowed(tenant_a_key, max_requests=2, window_seconds=60)
    assert res_a.allowed is False

    # Tenant B must NOT be blocked (strict tenant key isolation)
    res_b = limiter.is_allowed(tenant_b_key, max_requests=2, window_seconds=60)
    assert res_b.allowed is True
    assert res_b.remaining == 1


@pytest.mark.asyncio
async def test_evaluation_run_rate_limiting_enforcement(client: AsyncClient, db_session: AsyncSession):
    company = Company(name="RateLimit Corp", slug=f"rl-{uuid.uuid4().hex[:6]}")
    user = User(email=f"owner-{uuid.uuid4().hex[:6]}@rl.com", full_name="Owner RL", hashed_password="pw")
    db_session.add_all([company, user])
    await db_session.flush()

    membership = Membership(user_id=user.id, company_id=company.id, role=MembershipRole.OWNER)
    db_session.add(membership)
    await db_session.commit()

    from app.core.security import create_access_token
    token = create_access_token(subject=str(user.id))
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": str(company.id)}

    # Consume all slots for evaluation runs for this tenant
    eval_key = f"rl:eval:run:{company.id}"
    for _ in range(5):
        distributed_rate_limiter.is_allowed(eval_key, max_requests=5, window_seconds=3600)

    # Next evaluation run must immediately return HTTP 429
    resp = await client.post(
        "/api/v1/evaluations/run",
        json={"ai_employee_id": str(uuid.uuid4()), "dataset_name": "test"},
        headers=headers,
    )
    assert resp.status_code == 429
    assert resp.headers.get("Retry-After") is not None
    data = resp.json()
    assert data["detail"]["error"] == "RATE_LIMITED"
