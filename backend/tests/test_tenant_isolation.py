import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tenant_isolation_strictly_enforced(client: AsyncClient):
    """MANDATORY SECURITY TEST:
    Verifies that Company A can never access, read, modify, or delete Company B's AI Employee,
    even when attempting ID manipulation, header spoofing, or direct URL targeting.
    """
    # -------------------------------------------------------------------------
    # 1. Setup Tenant A (Alice at Company Alpha)
    # -------------------------------------------------------------------------
    signup_a = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "alice@alpha-corp.com",
            "password": "AlphaPassword123!",
            "full_name": "Alice Alpha",
            "company_name": "Company Alpha",
        },
    )
    assert signup_a.status_code == 201
    data_a = signup_a.json()
    token_a = data_a["token"]["access_token"]
    company_a_id = data_a["company"]["id"]
    headers_a = {
        "Authorization": f"Bearer {token_a}",
        "X-Company-ID": company_a_id,
    }

    # Create AI Employee for Company Alpha
    res_emp_a = await client.post(
        "/api/v1/ai-employees/",
        json={
            "name": "AlphaBot",
            "role": "Alpha Financial Advisor",
            "description": "Confidential Alpha financial knowledge agent.",
            "personality": "Strict and discreet.",
            "system_prompt": "You are AlphaBot. Alpha company secret: PROJECT_ZEUS_REVENUE=$100M.",
            "status": "ACTIVE",
        },
        headers=headers_a,
    )
    assert res_emp_a.status_code == 201
    employee_a_id = res_emp_a.json()["id"]

    # -------------------------------------------------------------------------
    # 2. Setup Tenant B (Bob at Company Beta)
    # -------------------------------------------------------------------------
    signup_b = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "bob@beta-corp.com",
            "password": "BetaPassword123!",
            "full_name": "Bob Beta",
            "company_name": "Company Beta",
        },
    )
    assert signup_b.status_code == 201
    data_b = signup_b.json()
    token_b = data_b["token"]["access_token"]
    company_b_id = data_b["company"]["id"]
    headers_b = {
        "Authorization": f"Bearer {token_b}",
        "X-Company-ID": company_b_id,
    }

    # Create AI Employee for Company Beta
    res_emp_b = await client.post(
        "/api/v1/ai-employees/",
        json={
            "name": "BetaBot",
            "role": "Beta Medical Triage Assistant",
            "description": "Confidential Beta patient triage agent.",
            "personality": "Compassionate and clinical.",
            "system_prompt": "You are BetaBot. Beta proprietary diagnosis logic.",
            "status": "ACTIVE",
        },
        headers=headers_b,
    )
    assert res_emp_b.status_code == 201
    employee_b_id = res_emp_b.json()["id"]

    # -------------------------------------------------------------------------
    # 3. Legitimate Access Tests (Self Tenant)
    # -------------------------------------------------------------------------
    # Alice accesses AlphaBot -> SUCCESS
    read_a_by_a = await client.get(f"/api/v1/ai-employees/{employee_a_id}", headers=headers_a)
    assert read_a_by_a.status_code == 200
    assert read_a_by_a.json()["name"] == "AlphaBot"

    # Bob accesses BetaBot -> SUCCESS
    read_b_by_b = await client.get(f"/api/v1/ai-employees/{employee_b_id}", headers=headers_b)
    assert read_b_by_b.status_code == 200
    assert read_b_by_b.json()["name"] == "BetaBot"

    # -------------------------------------------------------------------------
    # 4. Cross-Tenant Read Isolation Tests
    # -------------------------------------------------------------------------
    # Alice attempts to read BetaBot with Alice's tenant header
    cross_read_1 = await client.get(f"/api/v1/ai-employees/{employee_b_id}", headers=headers_a)
    assert cross_read_1.status_code == 404
    assert cross_read_1.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    # Bob attempts to read AlphaBot with Bob's tenant header
    cross_read_2 = await client.get(f"/api/v1/ai-employees/{employee_a_id}", headers=headers_b)
    assert cross_read_2.status_code == 404
    assert cross_read_2.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    # -------------------------------------------------------------------------
    # 5. Header Spoofing / Unauthorized Tenant Selection Tests
    # -------------------------------------------------------------------------
    # Alice attempts to spoof X-Company-ID to Company Beta's ID
    spoofed_headers_alice = {
        "Authorization": f"Bearer {token_a}",
        "X-Company-ID": company_b_id,
    }
    spoof_attempt = await client.get(f"/api/v1/ai-employees/{employee_b_id}", headers=spoofed_headers_alice)
    assert spoof_attempt.status_code == 403
    assert spoof_attempt.json()["error"]["code"] == "FORBIDDEN"

    # -------------------------------------------------------------------------
    # 6. Cross-Tenant Modification & Deletion Isolation Tests
    # -------------------------------------------------------------------------
    # Alice attempts to modify BetaBot
    hack_update = await client.patch(
        f"/api/v1/ai-employees/{employee_b_id}",
        json={"name": "HackedByAlice"},
        headers=headers_a,
    )
    assert hack_update.status_code == 404

    # Alice attempts to delete BetaBot
    hack_delete = await client.delete(
        f"/api/v1/ai-employees/{employee_b_id}",
        headers=headers_a,
    )
    assert hack_delete.status_code == 404

    # Verify BetaBot was untouched and intact
    verify_beta = await client.get(f"/api/v1/ai-employees/{employee_b_id}", headers=headers_b)
    assert verify_beta.status_code == 200
    assert verify_beta.json()["name"] == "BetaBot"

    # -------------------------------------------------------------------------
    # 7. Cross-Tenant Company Access Isolation
    # -------------------------------------------------------------------------
    # Alice attempts to access Company Beta's company endpoint
    comp_b_access = await client.get(f"/api/v1/companies/{company_b_id}", headers=headers_a)
    # Alice has no membership in company B, so passing company_b_id in path/tenant context returns 403
    assert comp_b_access.status_code in [403, 404]

    # Alice attempts to add a member to Company Beta
    comp_b_add_member = await client.post(
        f"/api/v1/companies/{company_b_id}/members",
        json={"user_email": "alice@alpha-corp.com", "role": "OWNER"},
        headers=headers_a,
    )
    assert comp_b_add_member.status_code in [403, 404]
