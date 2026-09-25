import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.models.company import Company
from app.models.membership import Membership, MembershipRole
from app.models.user import User
from app.services.auth import create_access_token
from app.services.observability.audit_service import AuditService
from app.services.observability.metrics import OperationalMetricsCollector
from app.services.observability.redactor import TelemetryRedactor
from app.services.observability.tracer import (
    Span,
    TraceCollector,
    Tracer,
    generate_span_id,
    generate_trace_id,
)


def test_w3c_trace_context_generation():
    """Validates W3C-compliant 32-hex trace_id and 16-hex span_id."""
    trace_id = generate_trace_id()
    span_id = generate_span_id()

    assert len(trace_id) == 32
    assert int(trace_id, 16) > 0
    assert len(span_id) == 16
    assert int(span_id, 16) > 0

    header = Tracer.format_traceparent(trace_id, span_id, sampled=True)
    assert header == f"00-{trace_id}-{span_id}-01"

    parsed = Tracer.parse_traceparent(header)
    assert parsed is not None
    assert parsed["trace_id"] == trace_id
    assert parsed["span_id"] == span_id
    assert parsed["sampled"] is True


def test_telemetry_redaction_rules():
    """Guarantees sensitive API keys, passwords, and tokens are scrubbed."""
    raw_str = (
        "Calling service with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz and "
        "Gemini key AIzaSyD-1234567890abcdefghijklmnopqrstuv and OpenAI sk-abcdef12345678901234567890"
    )
    redacted = TelemetryRedactor.redact_string(raw_str)
    assert "Bearer [REDACTED]" in redacted
    assert "[REDACTED_GEMINI_KEY]" in redacted
    assert "[REDACTED_OPENAI_KEY]" in redacted

    payload = {
        "user_email": "tenant@example.com",
        "api_key": "secret_key_123",
        "nested": {
            "password": "super_secret_password",
            "safe_param": "regular_value",
            "auth_header": "Bearer secret_jwt",
        },
    }
    cleaned = TelemetryRedactor.redact_dict(payload)
    assert cleaned["user_email"] == "tenant@example.com"
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["nested"]["password"] == "[REDACTED]"
    assert cleaned["nested"]["safe_param"] == "regular_value"
    assert cleaned["nested"]["auth_header"] == "[REDACTED]"


@pytest.mark.asyncio
async def test_span_hierarchy_and_collector():
    """Tests parent-child span nesting and trace collector aggregation."""
    tracer = Tracer()
    trace_id = generate_trace_id()
    company_id = uuid.uuid4()

    collector = TraceCollector(
        trace_id=trace_id,
        company_id=company_id,
        request_type="CHAT",
    )

    with collector:
        async with tracer.start_as_current_span("root_span", trace_id=trace_id) as root:
            root.set_attribute("root_attr", "root_value")

            async with tracer.start_as_current_span("child_retrieval") as child1:
                child1.set_attribute("kbs", 2)
                assert child1.parent_span_id == root.span_id

            async with tracer.start_as_current_span("child_llm") as child2:
                child2.set_attribute("model", "gemini-3.6-flash")
                assert child2.parent_span_id == root.span_id

    summary = collector.build_summary()
    assert summary.trace_id == trace_id
    assert summary.company_id == company_id
    assert summary.spans_count == 3
    assert summary.status == "SUCCESS"
    assert summary.total_latency_ms >= 0.0


def test_operational_metrics_collector():
    """Validates bounded-cardinality operational metrics calculations."""
    collector = OperationalMetricsCollector(max_latency_samples=100)
    collector.record_request("SUCCESS", total_latency_ms=100.0, retrieval_latency_ms=20.0, llm_latency_ms=75.0)
    collector.record_request("SUCCESS", total_latency_ms=200.0, retrieval_latency_ms=40.0, llm_latency_ms=150.0)
    collector.record_request("ERROR", total_latency_ms=50.0)
    collector.record_budget_denial()

    summary = collector.get_summary()
    assert summary["requests_total"] == 3
    assert summary["requests_success"] == 2
    assert summary["requests_error"] == 1
    assert summary["budget_denials_total"] == 1
    assert summary["latencies_ms"]["total"]["avg"] == 116.67


@pytest.mark.asyncio
async def test_audit_service_and_tenant_isolation(db_session: AsyncSession):
    """Guarantees audit trail logs events and isolates them strictly per tenant."""
    company_a = Company(name="Audit Co A", slug="audit-co-a")
    company_b = Company(name="Audit Co B", slug="audit-co-b")
    db_session.add_all([company_a, company_b])
    await db_session.flush()

    # Log event for Company A
    await AuditService.record_event(
        session=db_session,
        company_id=company_a.id,
        event_type="AI_EMPLOYEE_UPDATED",
        resource_type="AI_EMPLOYEE",
        resource_id="emp-1",
        metadata={"action": "updated prompt", "api_key": "AIzaSyD-secret"},
    )

    # Log event for Company B
    await AuditService.record_event(
        session=db_session,
        company_id=company_b.id,
        event_type="BUDGET_CREATED",
        resource_type="BUDGET",
        resource_id="b-1",
        metadata={"limit": "100.00"},
    )

    events_a = await AuditService.list_events(db_session, company_id=company_a.id)
    events_b = await AuditService.list_events(db_session, company_id=company_b.id)

    assert len(events_a) == 1
    assert events_a[0].event_type == "AI_EMPLOYEE_UPDATED"
    # Verify metadata secret was scrubbed
    assert events_a[0].safe_metadata["api_key"] == "[REDACTED]"

    assert len(events_b) == 1
    assert events_b[0].event_type == "BUDGET_CREATED"


@pytest.mark.asyncio
async def test_observability_api_endpoints(client: AsyncClient):
    """Tests GET /api/v1/observability/traces and /metrics/summary via HTTP."""
    signup = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "obs_user@example.com",
            "password": "Password123!",
            "full_name": "Obs User",
            "company_name": "Observability Test Co",
        },
    )
    assert signup.status_code == 201
    token = signup.json()["token"]["access_token"]
    company_id = signup.json()["company"]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": company_id}

    # 1. Metrics summary
    m_res = await client.get(
        "/api/v1/observability/metrics/summary",
        headers=headers,
    )
    assert m_res.status_code == 200
    assert "requests_total" in m_res.json()

    # 2. Traces list (empty initially)
    t_res = await client.get(
        "/api/v1/observability/traces",
        headers=headers,
    )
    assert t_res.status_code == 200
    assert isinstance(t_res.json(), list)

