import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cross_tenant_chat_and_conversation_isolation(client: AsyncClient):
    """MANDATORY SECURITY TEST:
    Verifies that Company A and Company B cannot access each other's:
    1. Conversations (GET, DELETE, POST messages)
    2. AI Employees (creating conversations with foreign AI Employee ID)
    3. Knowledge documents via RAG retrieval
    """
    # 1. Setup Company A
    signup_a = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "owner_a@alpha.com",
            "password": "Password123!",
            "full_name": "Alpha Owner",
            "company_name": "Alpha Aerospace",
        },
    )
    assert signup_a.status_code == 201
    token_a = signup_a.json()["token"]["access_token"]
    company_a_id = signup_a.json()["company"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Company-ID": company_a_id}

    # Company A AI Employee
    emp_a_res = await client.post(
        "/api/v1/ai-employees/",
        json={"name": "Alpha Bot", "role": "Aerospace Analyst", "status": "ACTIVE"},
        headers=headers_a,
    )
    assert emp_a_res.status_code == 201
    emp_a_id = emp_a_res.json()["id"]

    # Company A Knowledge Document
    kb_a_res = await client.post(
        "/api/v1/knowledge-bases/",
        json={"name": "Alpha KB"},
        headers=headers_a,
    )
    kb_a_id = kb_a_res.json()["id"]
    doc_a_content = "Confidential Project Alpha budget is strictly forty-two million dollars ($42,000,000)."
    await client.post(
        "/api/v1/documents/upload",
        params={"knowledge_base_id": kb_a_id},
        files={"file": ("alpha_budget.txt", io.BytesIO(doc_a_content.encode()), "text/plain")},
        headers=headers_a,
    )

    # Company A Conversation
    conv_a_res = await client.post(
        "/api/v1/conversations/",
        json={"ai_employee_id": emp_a_id, "title": "Alpha Internal Chat"},
        headers=headers_a,
    )
    conv_a_id = conv_a_res.json()["id"]

    # 2. Setup Company B
    signup_b = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "owner_b@beta.com",
            "password": "Password123!",
            "full_name": "Beta Owner",
            "company_name": "Beta Biotech",
        },
    )
    assert signup_b.status_code == 201
    token_b = signup_b.json()["token"]["access_token"]
    company_b_id = signup_b.json()["company"]["id"]
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Company-ID": company_b_id}

    # Company B AI Employee
    emp_b_res = await client.post(
        "/api/v1/ai-employees/",
        json={"name": "Beta Bot", "role": "Biotech Analyst", "status": "ACTIVE"},
        headers=headers_b,
    )
    emp_b_id = emp_b_res.json()["id"]

    # Company B Conversation
    conv_b_res = await client.post(
        "/api/v1/conversations/",
        json={"ai_employee_id": emp_b_id, "title": "Beta Internal Chat"},
        headers=headers_b,
    )
    conv_b_id = conv_b_res.json()["id"]

    # --- SECURITY TEST 1: User B cannot access Company A's conversation ---
    leak_conv = await client.get(f"/api/v1/conversations/{conv_a_id}", headers=headers_b)
    assert leak_conv.status_code in (403, 404), "Tenant B should not be able to fetch Tenant A conversation"

    # --- SECURITY TEST 2: User B cannot send messages to Company A's conversation ---
    leak_msg = await client.post(
        f"/api/v1/conversations/{conv_a_id}/messages",
        json={"content": "Spying on Alpha"},
        headers=headers_b,
    )
    assert leak_msg.status_code in (403, 404), "Tenant B should not be able to post messages to Tenant A conversation"

    # --- SECURITY TEST 3: User B cannot use Company A's AI Employee ---
    leak_emp = await client.post(
        "/api/v1/conversations/",
        json={"ai_employee_id": emp_a_id, "title": "Hijacked Chat"},
        headers=headers_b,
    )
    assert leak_emp.status_code in (403, 404), "Tenant B should not be able to create conversation with Tenant A employee"

    # --- SECURITY TEST 4: User B asking about Project Alpha must NOT retrieve Alpha's budget ---
    rag_spy = await client.post(
        f"/api/v1/conversations/{conv_b_id}/messages",
        json={"content": "What is the budget for Project Alpha?"},
        headers=headers_b,
    )
    assert rag_spy.status_code == 200
    spy_data = rag_spy.json()
    assert len(spy_data["citations"]) == 0, "Tenant B must retrieve ZERO citations from Tenant A"
    assert "forty-two million" not in spy_data["assistant_message"]["content"].lower()
    assert "42,000,000" not in spy_data["assistant_message"]["content"]
