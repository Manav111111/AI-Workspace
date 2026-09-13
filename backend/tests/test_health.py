import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_check(client: AsyncClient):
    response = await client.get("/ready")
    # In test environment, the real engine might not connect to pg, but endpoint returns json structure
    assert response.status_code in [200, 503]
    assert "status" in response.json()
