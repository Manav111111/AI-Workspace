import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_signup_and_login_flow(client: AsyncClient):
    # 1. Signup
    signup_payload = {
        "email": "owner@company-a.com",
        "password": "SuperSecretPassword123!",
        "full_name": "Alice Wonderland",
        "company_name": "Company Alpha",
    }
    signup_res = await client.post("/api/v1/auth/signup", json=signup_payload)
    assert signup_res.status_code == 201
    signup_data = signup_res.json()
    assert signup_data["user"]["email"] == "owner@company-a.com"
    assert "password" not in signup_data["user"]
    assert "token" in signup_data
    token = signup_data["token"]["access_token"]
    assert token is not None

    # 2. Duplicate registration should fail
    dup_res = await client.post("/api/v1/auth/signup", json=signup_payload)
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "RESOURCE_CONFLICT"

    # 3. Login with correct credentials
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@company-a.com", "password": "SuperSecretPassword123!"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "token" in login_data
    assert login_data["token"]["access_token"] is not None

    # 4. Login with incorrect password
    bad_login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@company-a.com", "password": "WrongPassword!"},
    )
    assert bad_login_res.status_code == 401
    assert bad_login_res.json()["error"]["code"] == "UNAUTHORIZED"

    # 5. Access /me without token
    unauth_me = await client.get("/api/v1/auth/me")
    assert unauth_me.status_code == 401
    assert unauth_me.json()["error"]["code"] == "UNAUTHORIZED"

    # 6. Access /me with token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["user"]["email"] == "owner@company-a.com"
    assert len(me_data["companies"]) == 1
    assert me_data["companies"][0]["role"] == "OWNER"
    assert me_data["companies"][0]["company"]["name"] == "Company Alpha"
