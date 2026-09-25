# Avtaar AI Control Plane — Phase 11–13 Architecture Specification

## 1. Executive Summary

The **Avtaar AI Control Plane** establishes a comprehensive enterprise management layer across all AI Employee operations in the multi-tenant SaaS platform. Rather than treating conversational AI employees as opaque black boxes, the Control Plane delivers:

1. **Phase 11 — Production Observability, OpenTelemetry & Distributed Tracing**:
   - W3C `traceparent` compliant distributed tracing context propagation across async boundaries.
   - Microsecond-accurate hierarchical span trees covering hybrid retrieval, prompt assembly, LLM generation, and agent tool execution.
   - Bounded-cardinality in-memory operational metrics collector (Avg, P50, P95, P99 latency percentiles and throughput).
   - Immutable, append-only tenant audit trail with automated secret and PII redaction.
2. **Phase 12 — AI Employee Playground & Debugging Environment**:
   - Safe sandbox testing harness strictly isolated from customer-facing conversational histories.
   - Ephemeral configuration snapshot overrides (system prompt, personality, model, temperature, top-k retrieval, retrieval strategy).
   - Deep inspection drawers exposing retrieved knowledge chunks with relevance scores, exact assembled prompts, and sub-second execution waterfall spans.
   - Side-by-side comparative evaluation matrix allowing dual-configuration validation against identical queries.
3. **Phase 13 — Tenant Cost Metering, Budgets & Usage Governance**:
   - Authoritative, append-only usage ledger persisting exact token counts (prompt, completion, cached) and calculated costs.
   - Standardized `UsageAdapter` normalizing token counts across Google Gemini SDK, OpenAI SDK, and Tiktoken tokenizer fallbacks.
   - Decimal-safe `ModelPricingRegistry` guaranteeing exact financial arithmetic without binary floating-point roundoff errors.
   - Proactive pre-flight budget governance enforcing soft-warning thresholds and hard-limit blocking (`HTTP 429 BUDGET_EXCEEDED`).

---

## 2. End-to-End System Architecture

```mermaid
graph TD
    subgraph ClientLayer [Client & Web Dashboard]
        FE[Next.js Dashboard]
        FE_Playground[Playground Sandbox UI]
        FE_Obs[Observability & Trace Explorer]
        FE_Usage[Usage & Budget Guardrails]
        FE_Audit[Enterprise Audit Trail]
    end

    subgraph APILayer [FastAPI Gateway & Routers]
        AuthMiddleware[TenantContext & Auth Middleware]
        ConvRouter[/api/v1/conversations]
        PlayRouter[/api/v1/playground]
        ObsRouter[/api/v1/observability]
        UsageRouter[/api/v1/usage]
    end

    subgraph ControlPlane [AI Control Plane Engine]
        BudgetService[BudgetService Guardrails]
        Tracer[Tracer & ContextVars Root Span]
        MetricsCollector[OperationalMetricsCollector]
        Redactor[TelemetryRedactor]
        PricingRegistry[ModelPricingRegistry]
        UsageAdapter[UsageAdapter Normalizer]
    end

    subgraph CoreEngine [Core Execution Pipeline]
        ConvEngine[ConversationEngine]
        AgentOrch[AgentOrchestrator]
        HybridRetriever[HybridRetriever / BM25 / Qdrant]
        LLMProvider[LLM Provider / Gemini / OpenAI]
        ToolRegistry[Tool Execution Registry]
    end

    subgraph DataStorage [PostgreSQL Persistence]
        DB_Traces[(trace_summaries)]
        DB_Audit[(audit_events)]
        DB_Playground[(playground_sessions & messages)]
        DB_Ledger[(usage_ledger_entries)]
        DB_Budgets[(usage_budgets)]
        DB_Pricing[(model_pricing_versions)]
    end

    %% Flow connections
    FE --> AuthMiddleware
    AuthMiddleware --> ConvRouter
    AuthMiddleware --> PlayRouter
    AuthMiddleware --> ObsRouter
    AuthMiddleware --> UsageRouter

    ConvRouter --> ConvEngine
    PlayRouter --> ConvEngine

    ConvEngine -->|1. Pre-check Budget| BudgetService
    BudgetService -->|Verify Spend < Limit| DB_Budgets
    BudgetService -->|Hard limit reached?| BudgetDenied[Throw 429 BUDGET_EXCEEDED]

    ConvEngine -->|2. Start Root Span| Tracer
    ConvEngine --> AgentOrch

    AgentOrch -->|Span: retrieval.hybrid| HybridRetriever
    AgentOrch -->|Span: prompt.assemble| Redactor
    AgentOrch -->|Span: llm.generate| LLMProvider
    AgentOrch -->|Span: tool.execute| ToolRegistry

    AgentOrch -->|3. Normalize Usage| UsageAdapter
    UsageAdapter -->|4. Calculate Cost| PricingRegistry
    UsageAdapter -->|5. Record Entry| DB_Ledger

    ConvEngine -->|6. Record Latency & Throughput| MetricsCollector
    ConvEngine -->|7. Persist Sanitized Summary| DB_Traces
    ConvEngine -->|8. Audit Tool / Auth Event| DB_Audit
```

---

## 3. Workstream Deep Dive

### 3.1 Workstream 1: OpenTelemetry-Compatible Distributed Tracing & Observability

#### W3C Distributed Context Propagation
Trace contexts are initialized with 128-bit trace IDs and 64-bit span IDs formatted according to the W3C `traceparent` specification:
$$\text{traceparent} = \text{version-trace\_id-parent\_id-trace\_flags}$$
For example: `00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01`.
Propagation across asynchronous asyncio coroutines is managed seamlessly via `contextvars.ContextVar`, ensuring that concurrent chat turns, background indexing workers, and evaluation runs never contaminate each other's execution contexts.

#### Execution Span Taxonomy
The core pipeline instruments every subsystem with fine-grained child spans:
- `conversation_turn` (Root Span): Measures end-to-end execution from HTTP request reception to final response delivery.
- `retrieval.hybrid`: Captures dense Qdrant vector retrieval, sparse BM25 indexing, Reciprocal Rank Fusion (RRF), and cross-encoder/heuristic reranking. Attributes record `query`, `retrieved_chunks_count`, and top candidate scores.
- `prompt.assemble`: Measures system prompt, personality, conversation history, and context grounding assembly.
- `llm.generate`: Measures raw model inference time, tokens consumed, and temperature/model configurations.
- `tool.execute`: Encapsulates tool parameter validation, execution sandboxing, and output formatting.

#### Automated Telemetry Redaction (`TelemetryRedactor`)
Prior to persisting spans into `trace_summaries` or audit events into `audit_events`, all payloads pass through `TelemetryRedactor`:
- Case-insensitive regex masking for API keys (`AIza...`, `sk-...`), bearer tokens, passwords, secrets, authorization headers, and credit card numbers.
- Recursive key inspection: keys matching sensitive patterns (`authorization`, `api_key`, `token`, `password`, `secret`, `cookie`) have their values replaced with `[REDACTED]`.

---

### 3.2 Workstream 2: AI Employee Playground & Debugging Environment

#### Isolation Invariants
The AI Employee Playground operates in strict functional isolation from customer-facing channels:
- Dedicated database models: `playground_sessions` and `playground_messages`.
- Playground turns are tagged with `usage_source = "PLAYGROUND"` in the usage ledger.
- Playground sessions do NOT affect production conversation threads, customer analytics, or live avatar interaction history.

#### Dynamic Configuration Overrides
Tenants can instantiate playground sessions with custom configuration snapshots without modifying the underlying `AIEmployee` entity:
```json
{
  "system_prompt": "You are Maya, an ultra-concise technical assistant...",
  "personality": "Direct, technical, objective",
  "model": "gemini-1.5-flash",
  "temperature": 0.1,
  "top_k": 5,
  "retrieval_mode": "hybrid"
}
```

#### Dual-Configuration Comparative Engine
The `/api/v1/playground/compare` endpoint accepts two distinct configuration snapshots ($A$ and $B$) and evaluates an array of test queries against both configurations concurrently. The response delivers side-by-side retrieved chunks, assembled prompts, generated responses, execution latencies, and token costs.

---

### 3.3 Workstream 3: Tenant Cost Metering, Budgets & Usage Governance

#### Decimal-Safe Financial Precision
All financial metrics are computed using Python's `decimal.Decimal` with 6 decimal places ($0.000001) to eliminate binary floating point drift:
$$\text{Cost} = \left(\frac{\text{Input Tokens}}{1,000,000} \times \text{Input Rate}\right) + \left(\frac{\text{Output Tokens}}{1,000,000} \times \text{Output Rate}\right) + \left(\frac{\text{Cached Tokens}}{1,000,000} \times \text{Cached Rate}\right)$$

#### Base Model Pricing Catalog
| Provider | Model Identifier | Input Cost / 1M Tokens | Output Cost / 1M Tokens | Cached Cost / 1M Tokens |
| :--- | :--- | :--- | :--- | :--- |
| Google | `gemini-1.5-flash` | $0.0750 | $0.3000 | $0.01875 |
| Google | `gemini-1.5-pro` | $1.2500 | $5.0000 | $0.31250 |
| Google | `gemini-2.0-flash` | $0.1000 | $0.4000 | $0.02500 |
| OpenAI | `gpt-4o` | $2.5000 | $10.0000 | $1.25000 |
| OpenAI | `gpt-4o-mini` | $0.1500 | $0.6000 | $0.07500 |

#### Usage Normalization Adapter (`UsageAdapter`)
Different LLM providers emit token telemetry through wildly divergent schemas:
- Google GenAI SDK: `response.usage_metadata.prompt_token_count`, `candidates_token_count`, `cached_content_token_count`.
- OpenAI SDK: `response.usage.prompt_tokens`, `completion_tokens`, `prompt_tokens_details.cached_tokens`.
- Fallback / Mock: Exact tokenizer calculation via `tiktoken` with character-length fallback ($4\text{ chars} \approx 1\text{ token}$).

#### Two-Tier Budget Governance Lifecycle
1. **Pre-Invocation Balance Verification**: Before dispatching an inference turn, `BudgetService.check_budget(...)` sums active tenant ledger expenditures for the current billing cycle ($D$, $W$, or $M$).
2. **Soft Limit Warning**: If utilization reaches $\ge \text{soft\_limit\_percent}$ (e.g. 80%), a non-blocking warning notification is attached to the response metadata and emitted in audit logs.
3. **Hard Limit Enforcement**: If current spend $\ge \text{limit\_amount}$ and `hard_limit_enabled = True`, the request is rejected immediately with an HTTP 429 `BUDGET_EXCEEDED` error without consuming upstream provider tokens.

---

## 4. Multi-Tenant Isolation & Database Schema

All newly added entities enforce strict `company_id` foreign keys indexed with tenant scoping:
- `trace_summaries`: Scoped by `company_id`, indexed on `(company_id, created_at)` and `(company_id, trace_id)`.
- `audit_events`: Scoped by `company_id`, indexed on `(company_id, event_type, created_at)`.
- `playground_sessions` & `playground_messages`: Scoped by `(company_id, ai_employee_id)`.
- `usage_ledger_entries`: Scoped by `company_id`, indexed on `(company_id, created_at)` and `(company_id, ai_employee_id)`.
- `usage_budgets`: Scoped by `company_id`, unique on active policies.
- `model_pricing_versions`: Version-controlled global and tenant-customizable pricing catalog.
