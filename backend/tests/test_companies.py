import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_company_creation_and_membership(client: AsyncClient):
    # Register user
    signup_res = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "creator@acme.com",
            "password": "Password123!",
            "full_name": "Charlie Creator",
        },
    )
    token = signup_res.json()["token"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create new company
    comp_res = await client.post(
        "/api/v1/companies/",
        json={"name": "Acme Innovations"},
        headers=headers,
    )
    assert comp_res.status_code == 201
    comp_data = comp_res.json()
    assert comp_data["name"] == "Acme Innovations"
    company_id = comp_data["id"]

    # List companies for user
    list_res = await client.get("/api/v1/companies/", headers=headers)
    assert list_res.status_code == 200
    memberships = list_res.json()
    assert len(memberships) == 1
    assert memberships[0]["role"] == "OWNER"
    assert memberships[0]["company"]["id"] == company_id

    # Register a second user to invite
    signup_bob = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "bob@acme.com",
            "password": "Password123!",
            "full_name": "Bob Builder",
        },
    )
    bob_token = signup_bob.json()["token"]["access_token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # Invite Bob to Acme Innovations as MEMBER by Creator (OWNER)
    invite_res = await client.post(
        f"/api/v1/companies/{company_id}/members",
        json={"user_email": "bob@acme.com", "role": "MEMBER"},
        headers=headers,
    )
    assert invite_res.status_code == 201
    assert invite_res.json()["role"] == "MEMBER"

    # Verify Bob now has Acme Innovations listed
    bob_comps = await client.get("/api/v1/companies/", headers=bob_headers)
    assert bob_comps.status_code == 200
    assert len(bob_comps.json()) == 1
    assert bob_comps.json()[0]["role"] == "MEMBER"

    # Bob (MEMBER) cannot invite others
    unauth_invite = await client.post(
        f"/api/v1/companies/{company_id}/members",
        json={"user_email": "another@acme.com", "role": "MEMBER"},
        headers=bob_headers,
    )
    assert unauth_invite.status_code == 403
    assert unauth_invite.json()["error"]["code"] == "FORBIDDEN"
