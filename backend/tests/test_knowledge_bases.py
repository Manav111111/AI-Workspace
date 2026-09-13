import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_knowledge_base_crud_lifecycle(client: AsyncClient):
    # Register user & company
    signup = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "kb_admin@enterprise.com",
            "password": "Password123!",
            "full_name": "KB Admin",
            "company_name": "Enterprise Knowledge Corp",
        },
    )
    assert signup.status_code == 201
    token = signup.json()["token"]["access_token"]
    company_id = signup.json()["company"]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": company_id}

    # 1. Create Knowledge Base
    create_res = await client.post(
        "/api/v1/knowledge-bases/",
        json={
            "name": "Customer Support FAQ",
            "description": "Standard operating procedures and return policies.",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    kb_data = create_res.json()
    assert kb_data["name"] == "Customer Support FAQ"
    assert kb_data["company_id"] == company_id
    kb_id = kb_data["id"]

    # 2. List Knowledge Bases
    list_res = await client.get("/api/v1/knowledge-bases/", headers=headers)
    assert list_res.status_code == 200
    kbs = list_res.json()
    assert len(kbs) == 1
    assert kbs[0]["id"] == kb_id

    # 3. Get Knowledge Base
    get_res = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Customer Support FAQ"

    # 4. Update Knowledge Base
    patch_res = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        json={"name": "Global Support Knowledge Base", "status": "ACTIVE"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Global Support Knowledge Base"

    # 5. Delete Knowledge Base
    del_res = await client.delete(f"/api/v1/knowledge-bases/{kb_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify deleted
    verify_get = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=headers)
    assert verify_get.status_code == 404
    assert verify_get.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
