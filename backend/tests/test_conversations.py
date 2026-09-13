import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_conversation_crud_and_messaging_lifecycle(client: AsyncClient):
    # 1. Sign up user & company
    signup = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "chat_user@enterprise.com",
            "password": "Password123!",
            "full_name": "Chat Admin",
            "company_name": "Enterprise Chat Inc",
        },
    )
    assert signup.status_code == 201
    token = signup.json()["token"]["access_token"]
    company_id = signup.json()["company"]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": company_id}

    # 2. Create AI Employee
    emp_res = await client.post(
        "/api/v1/ai-employees/",
        json={
            "name": "Sarah Connor",
            "role": "Operations Specialist",
            "personality": "Direct, professional, and helpful",
            "system_prompt": "Always be polite and direct.",
            "status": "ACTIVE",
        },
        headers=headers,
    )
    assert emp_res.status_code == 201
    employee_id = emp_res.json()["id"]

    # 3. Create Conversation
    conv_res = await client.post(
        "/api/v1/conversations/",
        json={
            "ai_employee_id": employee_id,
            "title": "Onboarding Inquiry",
        },
        headers=headers,
    )
    assert conv_res.status_code == 201
    conv_data = conv_res.json()
    assert conv_data["title"] == "Onboarding Inquiry"
    assert conv_data["company_id"] == company_id
    assert conv_data["ai_employee_id"] == employee_id
    conv_id = conv_data["id"]

    # 4. List Conversations
    list_res = await client.get("/api/v1/conversations/", headers=headers)
    assert list_res.status_code == 200
    convs = list_res.json()
    assert len(convs) >= 1
    assert any(c["id"] == conv_id for c in convs)

    # 5. Get Specific Conversation
    get_res = await client.get(f"/api/v1/conversations/{conv_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == conv_id

    # 6. Check Initial Empty Messages
    msgs_res = await client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers)
    assert msgs_res.status_code == 200
    assert len(msgs_res.json()) == 0

    # 7. Send Message to Conversation
    chat_res = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Hello Sarah, what is your refund policy?"},
        headers=headers,
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "user_message" in chat_data
    assert "assistant_message" in chat_data
    assert chat_data["user_message"]["content"] == "Hello Sarah, what is your refund policy?"
    assert chat_data["assistant_message"]["role"] == "ASSISTANT"
    assert len(chat_data["assistant_message"]["content"]) > 0

    # 8. Check Messages History (Both User and Assistant must be in order)
    msgs_after = await client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers)
    assert msgs_after.status_code == 200
    history = msgs_after.json()
    assert len(history) == 2
    assert history[0]["role"] == "USER"
    assert history[0]["content"] == "Hello Sarah, what is your refund policy?"
    assert history[1]["role"] == "ASSISTANT"

    # 9. Delete Conversation
    del_res = await client.delete(f"/api/v1/conversations/{conv_id}", headers=headers)
    assert del_res.status_code == 204

    # 10. Verify Deleted Conversation returns 404
    get_del = await client.get(f"/api/v1/conversations/{conv_id}", headers=headers)
    assert get_del.status_code == 404
