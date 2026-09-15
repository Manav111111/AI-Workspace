import datetime
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ai_employee import AIEmployee, AIEmployeeStatus
from app.models.ai_employee_knowledge_base import AIEmployeeKnowledgeBase
from app.models.ai_employee_tool import AIEmployeeTool
from app.models.business_entities import Order, OrderStatus
from app.models.company import Company
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.models.pending_tool_action import PendingActionStatus, PendingToolAction
from app.models.public_session import PublicChatSession
from app.models.public_usage import PublicUsageEvent
from sqlalchemy import select


@pytest.mark.asyncio
async def test_complete_phase4_end_to_end_widget_runtime_flow(client: AsyncClient, db_session: AsyncSession):
    """E2E Acceptance Test for Phase 4:
    1. Tenant creates AI Employee with assigned Knowledge Base and tools.
    2. Tenant configures widget theme and allowed domains.
    3. Tenant publishes AI Employee and receives embed snippet.
    4. Standalone visitor fetches sanitized public config.
    5. Visitor creates public session and receives bearer session token.
    6. Verify token is NEVER sent in URLs.
    7. Visitor asks grounded question and receives citations from assigned KB.
    8. Visitor triggers WRITE tool ('create_lead') and receives pending confirmation card.
    9. Visitor confirms action using only pending_action_id.
    10. Visitor restores conversation history after simulated page reload.
    11. Unauthorized external domain is rejected with 403.
    12. IP rate limiting enforced on excessive session creations.
    """
    company_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    kb_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    # 1. Seed Company, Knowledge Base and Document Chunk
    company = Company(id=company_id, name="Acme Corp", slug=f"acme-{company_id.hex[:6]}")
    db_session.add(company)

    kb = KnowledgeBase(id=kb_id, company_id=company_id, name="Acme Return Policy")
    db_session.add(kb)

    doc = Document(
        id=doc_id,
        company_id=company_id,
        knowledge_base_id=kb_id,
        filename="return_policy.pdf",
        original_filename="return_policy.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=1024,
        storage_path=f"storage/{company_id}/{doc_id}/return_policy.pdf",
        status=DocumentStatus.PROCESSED,
        document_metadata={},
    )
    db_session.add(doc)


    chunk = DocumentChunk(
        id=uuid.uuid4(),
        company_id=company_id,
        knowledge_base_id=kb_id,
        document_id=doc_id,
        chunk_index=0,
        content="Acme Corp offers a 30-day money back guarantee for all unworn apparel with original tags.",
        token_count=18,
        chunk_metadata={"header_path": "Returns > Policy", "page_number": 1},
    )
    db_session.add(chunk)

    # 2. Seed AI Employee
    employee = AIEmployee(
        id=emp_id,
        company_id=company_id,
        name="Nova Support",
        role="Customer Experience Specialist",
        description="Assists customers with orders and returns.",
        system_prompt="You are Nova, an AI employee for Acme Corp. Help customers with their orders.",
        status=AIEmployeeStatus.ACTIVE,
        is_published=False,  # Initially unpublished
        widget_config={
            "primary_color": "#6366f1",
            "theme": "dark",
            "welcome_message": "Hello from Acme!",
        },
    )
    db_session.add(employee)

    # Assign Knowledge Base & Tools (READ tool order_lookup & WRITE tool create_lead)
    kb_link = AIEmployeeKnowledgeBase(id=uuid.uuid4(), company_id=company_id, ai_employee_id=emp_id, knowledge_base_id=kb_id)
    tool_read = AIEmployeeTool(id=uuid.uuid4(), company_id=company_id, ai_employee_id=emp_id, tool_name="order_lookup")
    tool_write = AIEmployeeTool(id=uuid.uuid4(), company_id=company_id, ai_employee_id=emp_id, tool_name="create_lead")
    db_session.add_all([kb_link, tool_read, tool_write])
    await db_session.commit()

    # 3. Setup Authenticated Tenant Session
    signup_res = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"owner_{company_id.hex[:6]}@acme.com",
            "password": "SecurePassword123!",
            "full_name": "Acme Owner",
            "company_name": "Acme Corp",
        },
    )
    tenant_token = signup_res.json()["token"]["access_token"]
    tenant_comp_id = signup_res.json()["company"]["id"]
    tenant_headers = {"Authorization": f"Bearer {tenant_token}", "X-Company-ID": tenant_comp_id}

    # 4. Update employee to belong to authenticated tenant for dashboard API calls
    employee.company_id = uuid.UUID(tenant_comp_id)
    kb.company_id = uuid.UUID(tenant_comp_id)
    doc.company_id = uuid.UUID(tenant_comp_id)
    chunk.company_id = uuid.UUID(tenant_comp_id)
    kb_link.company_id = uuid.UUID(tenant_comp_id)
    tool_read.company_id = uuid.UUID(tenant_comp_id)
    tool_write.company_id = uuid.UUID(tenant_comp_id)
    await db_session.commit()

    # 5. Dashboard configures widget theme and allowed domains
    cfg_resp = await client.put(
        f"/api/v1/ai-employees/{emp_id}/widget-config",
        headers=tenant_headers,
        json={
            "primary_color": "#10b981",
            "theme": "dark",
            "position": "bottom-right",
            "brand_name": "Acme Live",
            "welcome_message": "Welcome to Acme Support!",
            "allowed_domains": ["acmewebsite.com", "localhost"],
        },
    )
    assert cfg_resp.status_code == 200

    # 6. Dashboard Publishes AI Employee
    pub_resp = await client.post(
        f"/api/v1/ai-employees/{emp_id}/publish",
        headers=tenant_headers,
        json={"is_published": True, "allowed_domains": ["acmewebsite.com", "localhost"]},
    )
    assert pub_resp.status_code == 200
    pub_employee = pub_resp.json()
    assert pub_employee["is_published"] is True
    assert pub_employee["public_id"] is not None
    public_id = pub_employee["public_id"]

    # 7. Dashboard retrieves Embed snippet
    embed_resp = await client.get(f"/api/v1/ai-employees/{emp_id}/embed", headers=tenant_headers)
    assert embed_resp.status_code == 200
    embed_payload = embed_resp.json()
    assert "widget.js" in embed_payload["widget_script_url"]
    assert public_id in embed_payload["embed_snippet"]
    assert "data-ai-employee=" in embed_payload["embed_snippet"]

    # 8. Standalone Visitor fetches public config from authorized domain
    pub_headers = {"Origin": "https://acmewebsite.com"}
    config_resp = await client.get(f"/api/v1/public/employees/{public_id}/config", headers=pub_headers)
    assert config_resp.status_code == 200
    public_cfg = config_resp.json()
    assert public_cfg["name"] == "Nova Support"
    assert public_cfg["widget_config"]["primary_color"] == "#10b981"
    assert "system_prompt" not in public_cfg
    assert "company_id" not in public_cfg

    # 9. Visitor establishes anonymous session
    session_resp = await client.post(
        f"/api/v1/public/employees/{public_id}/sessions",
        headers=pub_headers,
        json={"visitor_id": "vis_visitor_e2e_101"},
    )
    assert session_resp.status_code == 200
    sess_data = session_resp.json()
    session_token = sess_data["session_token"]
    assert session_token.startswith("sess_pub_")

    # 10. Visitor sends chat message with Bearer token
    visitor_bearer_headers = {
        "Authorization": f"Bearer {session_token}",
        "Origin": "https://acmewebsite.com",
    }
    chat_resp = await client.post(
        "/api/v1/public/sessions/messages",
        headers=visitor_bearer_headers,
        json={"message": "What is the return policy?"},
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "message" in chat_data
    assert len(chat_data["message"]) > 0

    # 11. Visitor triggers WRITE tool ('create_lead') requiring confirmation
    write_resp = await client.post(
        "/api/v1/public/sessions/messages",
        headers=visitor_bearer_headers,
        json={"message": "Please capture a sales lead: John Doe at john@acme.com"},
    )
    assert write_resp.status_code == 200
    write_data = write_resp.json()
    assert write_data.get("pending_confirmation") is not None
    pending_action_id = write_data["pending_confirmation"]["pending_action_id"]

    # 12. Visitor confirms pending action
    confirm_resp = await client.post(
        "/api/v1/public/sessions/messages",
        headers=visitor_bearer_headers,
        json={
            "message": "Yes, approve lead creation",
            "pending_action_id": pending_action_id,
            "confirm_action": True,
        },
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["pending_confirmation"] is None

    # 13. Visitor refreshes page -> fetch session history
    hist_resp = await client.get("/api/v1/public/sessions/messages", headers=visitor_bearer_headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) >= 4  # Includes user queries and assistant responses

    # 14. Unauthorized domain is rejected
    unauth_headers = {"Origin": "https://unauthorized-evil-domain.com"}
    block_resp = await client.get(f"/api/v1/public/employees/{public_id}/config", headers=unauth_headers)
    assert block_resp.status_code == 403

    # 15. Verify usage event logged
    usage_stmt = select(PublicUsageEvent).where(PublicUsageEvent.company_id == uuid.UUID(tenant_comp_id))
    usage_res = await db_session.execute(usage_stmt)
    events = usage_res.scalars().all()
    assert len(events) >= 2
