from decimal import Decimal
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import BudgetExceededException
from app.main import app
from app.models.ai_employee import AIEmployee
from app.models.company import Company
from app.models.membership import Membership, MembershipRole
from app.models.user import User
from app.services.auth import create_access_token
from app.services.billing.budget_service import BudgetService
from app.services.billing.pricing_registry import ModelPricingRegistry, PricingRule
from app.services.billing.usage_adapter import StandardizedUsage, UsageAdapter


def test_usage_adapter_gemini_and_openai_extraction():
    """Validates authoritative usage extraction across Gemini and OpenAI payloads."""
    # 1. Gemini payload
    gemini_raw = {
        "promptTokenCount": 250,
        "candidatesTokenCount": 80,
        "totalTokenCount": 330,
        "cachedContentTokenCount": 100,
    }
    gemini_usage = UsageAdapter.extract_usage("gemini", gemini_raw)
    assert gemini_usage.input_tokens == 250
    assert gemini_usage.output_tokens == 80
    assert gemini_usage.cached_tokens == 100
    assert gemini_usage.total_tokens == 330
    assert gemini_usage.usage_source == "PROVIDER_REPORTED"

    # 2. OpenAI payload
    openai_raw = {
        "prompt_tokens": 500,
        "completion_tokens": 120,
        "total_tokens": 620,
        "prompt_tokens_details": {"cached_tokens": 50},
    }
    openai_usage = UsageAdapter.extract_usage("openai", openai_raw)
    assert openai_usage.input_tokens == 500
    assert openai_usage.output_tokens == 120
    assert openai_usage.cached_tokens == 50
    assert openai_usage.total_tokens == 620
    assert openai_usage.usage_source == "PROVIDER_REPORTED"

    # 3. Fallback estimation
    est_usage = UsageAdapter.extract_usage(
        "gemini",
        raw_usage=None,
        messages=[{"role": "user", "content": "A" * 40}],  # 40 chars ≈ 10 tokens
        generated_text="B" * 20,                           # 20 chars ≈ 5 tokens
    )
    assert est_usage.input_tokens == 10
    assert est_usage.output_tokens == 5
    assert est_usage.total_tokens == 15
    assert est_usage.usage_source == "TOKENIZER_ESTIMATED"


def test_decimal_safe_pricing_calculation():
    """Guarantees decimal precision without floating point inaccuracies."""
    rule = PricingRule(
        provider="gemini",
        model="gemini-3.6-flash",
        input_price_per_million=Decimal("0.075000"),
        output_price_per_million=Decimal("0.300000"),
        cached_input_price_per_million=Decimal("0.018750"),
    )

    # 1,000,000 input tokens = $0.075000
    cost, status, version = ModelPricingRegistry.calculate_cost(
        pricing=rule,
        input_tokens=1_000_000,
        output_tokens=0,
        cached_tokens=0,
    )
    assert cost == Decimal("0.075000")
    assert status == "FINAL"

    # Complex calculation with cached tokens
    cost2, status2, _ = ModelPricingRegistry.calculate_cost(
        pricing=rule,
        input_tokens=200_000,  # 100k non-cached ($0.0075) + 100k cached ($0.001875)
        output_tokens=50_000,  # 50k output ($0.015)
        cached_tokens=100_000,
    )
    # Total = 0.0075 + 0.001875 + 0.015 = 0.024375
    assert cost2 == Decimal("0.024375")


@pytest.mark.asyncio
async def test_budget_soft_warning_and_hard_enforcement(db_session: AsyncSession):
    """Verifies that spending triggers soft warnings at 80% and blocks execution at 100%."""
    company = Company(name="Budgeting Co", slug="budgeting-co")
    db_session.add(company)
    await db_session.flush()

    # Create monthly budget of $1.00 with 80% soft limit and hard limit enabled
    budget = await BudgetService.create_budget(
        session=db_session,
        company_id=company.id,
        budget_name="Testing Cap",
        limit_amount=Decimal("1.0000"),
        soft_limit_percent=80.0,
        hard_limit_enabled=True,
    )

    # Check 1: Empty spend -> allowed, no warning
    check1 = await BudgetService.check_budget(db_session, company.id)
    assert check1["allowed"] is True
    assert check1["warning"] is False

    # Simulate $0.85 spend (85% of budget)
    usage_entry = await BudgetService.record_usage(
        session=db_session,
        company_id=company.id,
        provider="gemini",
        model="gemini-3.6-flash",
        usage=StandardizedUsage(
            input_tokens=10_000_000,  # $0.75
            output_tokens=500_000,     # $0.15 -> total $0.90
            cached_tokens=0,
            total_tokens=10_500_000,
            usage_source="PROVIDER_REPORTED",
        ),
    )
    assert usage_entry.estimated_cost == Decimal("0.900000")

    # Check 2: 90% spend -> allowed, but warning triggered
    check2 = await BudgetService.check_budget(db_session, company.id)
    assert check2["allowed"] is True
    assert check2["warning"] is True
    assert len(check2["warnings"]) == 1
    assert check2["warnings"][0]["utilization_percent"] == 90.0

    # Simulate another $0.20 spend -> total $1.10 (exceeds $1.00 hard limit)
    await BudgetService.record_usage(
        session=db_session,
        company_id=company.id,
        provider="gemini",
        model="gemini-3.6-flash",
        usage=StandardizedUsage(
            input_tokens=0,
            output_tokens=1_000_000,  # $0.30
            cached_tokens=0,
            total_tokens=1_000_000,
            usage_source="PROVIDER_REPORTED",
        ),
    )

    # Check 3: Hard limit reached -> raises BudgetExceededException
    with pytest.raises(BudgetExceededException) as excinfo:
        await BudgetService.check_budget(db_session, company.id)
    assert "Testing Cap" in str(excinfo.value.message)


@pytest.mark.asyncio
async def test_usage_summary_and_budget_apis(client: AsyncClient):
    """Tests GET /api/v1/usage/summary, /ledger, and /budgets CRUD via HTTP."""
    signup = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "usage_admin@example.com",
            "password": "Password123!",
            "full_name": "Usage Admin",
            "company_name": "Usage API Co",
        },
    )
    assert signup.status_code == 201
    token = signup.json()["token"]["access_token"]
    company_id = signup.json()["company"]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": company_id}

    # 1. Create Budget
    b_res = await client.post(
        "/api/v1/budgets",
        headers=headers,
        json={
            "budget_name": "Monthly Prod Cap",
            "limit_amount": 50.0,
            "period_type": "MONTHLY",
            "soft_limit_percent": 80.0,
            "hard_limit_enabled": True,
        },
    )
    assert b_res.status_code == 201
    budget_id = b_res.json()["id"]

    # 2. List Budgets
    list_res = await client.get(
        "/api/v1/budgets",
        headers=headers,
    )
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 3. Get Usage Summary
    sum_res = await client.get(
        "/api/v1/usage/summary",
        headers=headers,
    )
    assert sum_res.status_code == 200
    assert "total_tokens" in sum_res.json()
    assert "budgets" in sum_res.json()

    # 4. Delete Budget
    del_res = await client.delete(
        f"/api/v1/budgets/{budget_id}",
        headers=headers,
    )
    assert del_res.status_code == 204

