import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ai_employee_crud_lifecycle(client: AsyncClient):
    # Setup company and owner
    signup_res = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "sarah@nexustech.io",
            "password": "SecurePassword123!",
            "full_name": "Sarah Connor",
            "company_name": "Nexus Tech",
        },
    )
    token = signup_res.json()["token"]["access_token"]
    company_id = signup_res.json()["company"]["id"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Company-ID": company_id,
    }

    # 1. Create AI Employee
    create_payload = {
        "name": "Aura",
        "role": "Senior Support Specialist",
        "description": "Handles tier-1 technical support and triage.",
        "personality": "Empathetic, concise, and technically rigorous.",
        "system_prompt": "You are Aura, an AI employee for Nexus Tech. Always maintain customer confidentiality.",
        "language": "en",
        "status": "ACTIVE",
        "avatar_config": {"model": "standard_v1", "style": "professional"},
        "voice_config": {"voice_id": "en_us_female_clarity", "pitch": 1.0},
    }
    create_res = await client.post("/api/v1/ai-employees/", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["name"] == "Aura"
    assert created_data["company_id"] == company_id
    assert created_data["status"] == "ACTIVE"
    employee_id = created_data["id"]

    # 2. Get AI Employee by ID
    get_res = await client.get(f"/api/v1/ai-employees/{employee_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == employee_id
    assert get_res.json()["name"] == "Aura"

    # 3. List AI Employees
    list_res = await client.get("/api/v1/ai-employees/", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["id"] == employee_id

    # 4. Update AI Employee
    update_res = await client.patch(
        f"/api/v1/ai-employees/{employee_id}",
        json={
            "role": "Lead Support AI Specialist",
            "personality": "Charismatic and proactive problem solver.",
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["role"] == "Lead Support AI Specialist"
    assert update_res.json()["personality"] == "Charismatic and proactive problem solver."

    # 5. Delete AI Employee
    del_res = await client.delete(f"/api/v1/ai-employees/{employee_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify deleted
    verify_get = await client.get(f"/api/v1/ai-employees/{employee_id}", headers=headers)
    assert verify_get.status_code == 404
    assert verify_get.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
