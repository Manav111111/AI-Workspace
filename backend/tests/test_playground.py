import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.models.ai_employee import AIEmployee
from app.models.company import Company
from app.models.knowledge_base import KnowledgeBase
from app.models.membership import Membership, MembershipRole
from app.models.user import User
from app.services.auth import create_access_token
from app.services.playground.playground_service import PlaygroundService


@pytest.mark.asyncio
async def test_playground_session_creation_and_config_snapshot(db_session: AsyncSession):
    """Verifies playground session creates an isolated config snapshot."""
    company = Company(name="Playground Co", slug="playground-co")
    user = User(email="pg_user@example.com", hashed_password="hashed_password", full_name="PG User")
    db_session.add_all([company, user])
    await db_session.flush()

    employee = AIEmployee(
        company_id=company.id,
        name="Support Bot",
        role="Tier 1 Support",
        personality="Helpful and concise",
        system_prompt="Answer based strictly on company knowledge.",
    )
    db_session.add(employee)
    await db_session.flush()

    session = await PlaygroundService.create_session(
        session=db_session,
        company_id=company.id,
        user_id=user.id,
        ai_employee_id=employee.id,
        session_name="My Experiment",
        config_overrides={
            "system_prompt": "Modified experimental prompt",
            "temperature": 0.7,
            "top_k": 3,
        },
    )

    assert session.session_name == "My Experiment"
    assert session.config_snapshot["system_prompt"] == "Modified experimental prompt"
    assert session.config_snapshot["temperature"] == 0.7
    assert session.config_snapshot["top_k"] == 3
    # Verify production employee was NOT modified
    assert employee.system_prompt == "Answer based strictly on company knowledge."


@pytest.mark.asyncio
async def test_playground_turn_execution_and_inspectors(db_session: AsyncSession):
    """Verifies playground message execution returns retrieval debug, prompt debug, and trace linkage."""
    company = Company(name="Playground Turn Co", slug="playground-turn-co")
    user = User(email="pg_turn@example.com", hashed_password="hashed_password", full_name="Turn User")
    db_session.add_all([company, user])
    await db_session.flush()

    employee = AIEmployee(
        company_id=company.id,
        name="Researcher",
        role="Product Expert",
        personality="Analytical",
        system_prompt="Provide factual information.",
    )
    db_session.add(employee)
    await db_session.flush()

    pg_session = await PlaygroundService.create_session(
        session=db_session,
        company_id=company.id,
        user_id=user.id,
        ai_employee_id=employee.id,
    )

    res = await PlaygroundService.send_message(
        session=db_session,
        company_id=company.id,
        user_id=user.id,
        session_id=pg_session.id,
        user_query="What are your product features?",
    )

    assert "assistant_message" in res
    assert "prompt_debug" in res
    assert "retrieval_debug" in res
    assert "metrics" in res
    assert "trace_id" in res
    assert len(res["trace_id"]) == 32
    assert res["prompt_debug"]["personality"] == "Analytical"


@pytest.mark.asyncio
async def test_playground_cross_tenant_isolation(client: AsyncClient, db_session: AsyncSession):
    """Guarantees Tenant A cannot access or send messages in Tenant B's playground session."""
    # 1. Signup Tenant A
    res_a = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "user_a@example.com",
            "password": "Password123!",
            "full_name": "User A",
            "company_name": "Tenant A",
        },
    )
    assert res_a.status_code == 201
    token_a = res_a.json()["token"]["access_token"]
    company_id_a = res_a.json()["company"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Company-ID": company_id_a}

    # 2. Signup Tenant B
    res_b = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "user_b@example.com",
            "password": "Password123!",
            "full_name": "User B",
            "company_name": "Tenant B",
        },
    )
    assert res_b.status_code == 201
    token_b = res_b.json()["token"]["access_token"]
    company_id_b = res_b.json()["company"]["id"]
    user_id_b = uuid.UUID(res_b.json()["user"]["id"])

    # 3. Create Bot and Playground Session in Tenant B
    emp_b = AIEmployee(company_id=uuid.UUID(company_id_b), name="Bot B", role="Assistant")
    db_session.add(emp_b)
    await db_session.flush()

    session_b = await PlaygroundService.create_session(
        session=db_session,
        company_id=uuid.UUID(company_id_b),
        user_id=user_id_b,
        ai_employee_id=emp_b.id,
    )

    # 4. User A attempts to read session B
    get_res = await client.get(
        f"/api/v1/playground/sessions/{session_b.id}",
        headers=headers_a,
    )
    assert get_res.status_code == 404

    # 5. User A attempts to send message to session B
    msg_res = await client.post(
        f"/api/v1/playground/sessions/{session_b.id}/messages",
        headers=headers_a,
        json={"content": "Malicious attempt"},
    )
    assert msg_res.status_code == 404



@pytest.mark.asyncio
async def test_playground_compare_configurations(db_session: AsyncSession):
    """Tests side-by-side comparison of two configurations."""
    company = Company(name="Compare Co", slug="compare-co")
    db_session.add(company)
    await db_session.flush()


    emp = AIEmployee(company_id=company.id, name="Comparison Bot", role="Assistant")
    db_session.add(emp)
    await db_session.flush()

    config_a = {"system_prompt": "Be brief", "model": "mock-model", "temperature": 0.1}
    config_b = {"system_prompt": "Be detailed", "model": "mock-model", "temperature": 0.8}

    comparison = await PlaygroundService.compare_configurations(
        session=db_session,
        company_id=company.id,
        ai_employee_id=emp.id,
        test_queries=["Explain pricing"],
        config_a=config_a,
        config_b=config_b,
    )

    assert comparison["queries_evaluated"] == 1
    comp_item = comparison["comparisons"][0]
    assert comp_item["query"] == "Explain pricing"
    assert "answer" in comp_item["config_a"]
    assert "answer" in comp_item["config_b"]
