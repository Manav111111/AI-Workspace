import io
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import MessageRole
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.services.conversation_engine import ConversationEngine


@pytest.mark.asyncio
async def test_end_to_end_rag_grounded_conversation_pipeline(client: AsyncClient, db_session: AsyncSession):
    """End-to-End RAG Test:
    Company Signup → Create AI Employee → Create KB → Upload Document → Ingestion
    → Open Conversation → Question → Embedding → Qdrant → Context → LLM → Citation → Saved Conversation
    """
    # 1. Sign up user & company
    signup = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "e2e_rag@company.com",
            "password": "Password123!",
            "full_name": "RAG Evaluator",
            "company_name": "E2E RAG Solutions",
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
            "name": "Maya",
            "role": "Customer Experience Officer",
            "personality": "Empathetic, clear, and accurate",
            "system_prompt": "You represent E2E RAG Solutions. Be concise.",
            "status": "ACTIVE",
        },
        headers=headers,
    )
    assert emp_res.status_code == 201
    employee_id = emp_res.json()["id"]

    # 3. Create Knowledge Base
    kb_res = await client.post(
        "/api/v1/knowledge-bases/",
        json={
            "name": "Company Operations Handbook",
            "description": "Standard company return and warranty terms",
        },
        headers=headers,
    )
    assert kb_res.status_code == 201
    kb_id = kb_res.json()["id"]

    # 4. Upload Company Document (Known fact: 30 days refund period)
    doc_content = (
        "E2E RAG Solutions Customer Return Policy\n\n"
        "Customers may return eligible products within 30 days of purchase.\n"
        "All refunds are processed back to the original payment method within 5 business days.\n"
        "Items must be in original condition with tags attached."
    )
    upload_res = await client.post(
        "/api/v1/documents/upload",
        params={"knowledge_base_id": kb_id},
        files={"file": ("refund_policy.txt", io.BytesIO(doc_content.encode("utf-8")), "text/plain")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Verify Document is PROCESSED and chunks are in Qdrant
    doc_check = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert doc_check.status_code == 200
    assert doc_check.json()["status"] == "PROCESSED"
    chunks_check = await client.get(f"/api/v1/documents/{doc_id}/chunks", headers=headers)
    assert chunks_check.status_code == 200
    assert len(chunks_check.json()) >= 1

    # 4.5. Assign Knowledge Base to AI Employee (Knowledge Governance)
    assign_res = await client.put(
        f"/api/v1/ai-employees/{employee_id}/knowledge-bases",
        json={"knowledge_base_ids": [kb_id]},
        headers=headers,
    )
    assert assign_res.status_code == 200
    assert len(assign_res.json()["knowledge_base_ids"]) == 1

    # 5. Create Conversation
    conv_res = await client.post(
        "/api/v1/conversations/",
        json={
            "ai_employee_id": employee_id,
            "title": "Customer Return Question",
        },
        headers=headers,
    )
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    # 6. Ask Question Covered by the Document
    # Tests: question → embedding → Qdrant → context → LLM → citation → saved conversation
    chat_res = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "What is the return period for eligible products?"},
        headers=headers,
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()

    # Verify Grounded Answer contains known fact
    assistant_text = chat_data["assistant_message"]["content"]
    assert "30 days" in assistant_text

    # Verify Citation is returned from the uploaded document
    citations = chat_data["citations"]
    assert len(citations) >= 1
    top_citation = citations[0]
    assert top_citation["document_id"] == doc_id
    assert top_citation["document_name"] == "refund_policy.txt"
    assert top_citation["score"] > 0

    # Verify Latency and Retrieval Metrics are present
    metrics = chat_data["metrics"]
    assert "retrieval_latency_ms" in metrics
    assert "llm_latency_ms" in metrics
    assert "total_latency_ms" in metrics
    assert metrics["chunks_retrieved"] >= 1

    # 7. Ask Unanswerable Question (Not in KB)
    # Verifies Grounded Answering Policy (no fabrication)
    unrelated_res = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Do you offer international shipping to Antarctica?"},
        headers=headers,
    )
    assert unrelated_res.status_code == 200
    unrelated_data = unrelated_res.json()
    unrelated_reply = unrelated_data["assistant_message"]["content"]

    # Must state information is not available
    assert "not available in the company's knowledge base" in unrelated_reply.lower() or "not available" in unrelated_reply.lower()

    # 8. Verify Messages Persisted in Database
    msgs_res = await client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers)
    assert msgs_res.status_code == 200
    all_msgs = msgs_res.json()
    # Should have 4 messages: User Q1, Assistant A1, User Q2, Assistant A2
    assert len(all_msgs) == 4
    assert all_msgs[0]["role"] == "USER"
    assert all_msgs[1]["role"] == "ASSISTANT"
    assert len(all_msgs[1]["citations"]) >= 1
    assert all_msgs[2]["role"] == "USER"
    assert all_msgs[3]["role"] == "ASSISTANT"
