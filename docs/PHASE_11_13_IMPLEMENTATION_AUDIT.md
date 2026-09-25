# Avtaar AI Control Plane: Phase 11–13 Implementation Audit

**Audit Timestamp:** September 2026  
**Repository:** Avtaar AI Employee Platform  
**Target Milestone:** Combined Phase 11–13 — AI Control Plane  
- Phase 11: Production Observability, OpenTelemetry & Distributed Tracing  
- Phase 12: AI Employee Playground & Debugging Environment  
- Phase 13: Tenant Cost Metering, Budgets & Usage Governance  

---

## 1. Existing Architecture

Avtaar is a multi-tenant AI Employee SaaS platform constructed around asynchronous FastAPI (backend) and Next.js 14 App Router (frontend).

### Core Components
- **ConversationEngine (`app/services/conversation_engine.py`)**: Central conversational brain decoupled from any presentation layer. Coordinates multi-tenant security verification, persistence of user messages prior to LLM execution, invocation of the `AgentOrchestrator`, persistence of assistant messages with structured citations, and presentation metadata generation for downstream consumers (Avatar, Voice, Web Chat).
- **AgentOrchestrator (`app/services/agent/orchestrator.py`)**: Executes bounded agent loops (`max_iterations = 5`). Manages scoped RAG retrieval across assigned Knowledge Bases, dynamic function tool extraction, confirmation checking for WRITE actions (`PendingToolAction`), tool invocation via `ToolExecutor`, and citation synthesis.
- **Retrieval Pipeline (`app/services/retrieval/`)**:
  - `DenseRetriever`: Qdrant vector search filtered strictly by tenant `company_id` and assigned `knowledge_base_ids`.
  - `SparseRetriever`: In-memory BM25 index per knowledge base (`RankBM25Index`) with thread-safe async cache and lock-free eviction.
  - `ReciprocalRankFusion`: Parameterized RRF ($k=60$) combining dense and sparse candidate rankings.
  - `CrossEncoderReranker`: Optional scoring via HuggingFace CrossEncoder or heuristic fallback.
- **LLM Provider Abstraction (`app/services/llm/`)**:
  - `LLMProvider` abstract base class defining `generate()` and `generate_stream()`.
  - `GeminiProvider`: Direct Google REST `generateContent` with multi-model failover (`gemini-3.6-flash`, `gemini-2.5-flash-lite`, etc.).
  - `OpenAIProvider`: Async HTTPX client for OpenAI-compatible completions.
  - `MockProvider`: Offline deterministic testing provider.
- **Persistence & Storage**:
  - PostgreSQL 15 via SQLAlchemy 2.0 asyncpg.
  - Redis 7 for distributed sliding-window rate limiting (`DistributedRateLimiter`) and background task queuing.
  - Qdrant vector database for chunk embeddings.
  - Local disk storage (`STORAGE_ROOT = ./uploads`) for raw ingested files.

---

## 2. Existing Observability and Logging

### Current State
1. **Application Logging**: Python's standard `logging` library is used across services (e.g. `logger = logging.getLogger("app.services.conversation_engine")`). Log messages log tenant `company_id`, `employee_id`, and turn latencies to stdout/stderr.
2. **Turn Metrics**:
   - `ConversationEngineResponse.metrics`: Returns `retrieval_latency_ms`, `llm_latency_ms`, `total_latency_ms`, `chunks_retrieved`, `iterations`, `tool_calls_count`.
   - `EvaluationResultItem`: Captures `latency_ms` and raw `token_usage` JSON.
   - `PublicUsageEvent`: Captures `latency_ms`, `input_tokens`, `output_tokens` solely for public chat sessions.
3. **What is Missing**:
   - **No Distributed Tracing**: No OpenTelemetry Tracer, Span, or W3C `traceparent` context propagation. A request cannot be correlated across HTTP handlers, ConversationEngine, retrieval stages, LLM calls, and background jobs.
   - **No Granular Span Lifecycle**: No visibility into sub-phases: dense vs. sparse latency, RRF merge time, reranker latency, prompt assembly duration, tool serialization time.
   - **No Centralized Redaction**: Raw exceptions or error messages risk leaking sensitive configuration, tokens, or customer inputs into application logs.
   - **No Trace Storage**: Production turns do not persist structured trace summaries for tenant inspection.

---

## 3. Existing Token Usage Reporting

### Current State
- `LLMResponse` in `app/services/llm/base.py` contains an optional `usage: Optional[Dict[str, Any]] = None` field.
- `GeminiProvider` extracts `usageMetadata` from Google's response (`promptTokenCount`, `candidatesTokenCount`, `totalTokenCount`, `cachedContentTokenCount`).
- `OpenAIProvider` extracts `data.get("usage")` (`prompt_tokens`, `completion_tokens`, `total_tokens`).
- `MockProvider` returns simulated token dictionaries.
- `PublicUsageEvent` records `input_tokens` and `output_tokens` if present, but **only** for public unauthenticated visitor sessions.

### Gaps
- Authenticated `ConversationEngine.respond()` does **not** persist token usage to any relational ledger or conversation metadata.
- Token counts are not standardized across providers (e.g., camelCase in Gemini vs snake_case in OpenAI).
- Distinctions between authoritative `PROVIDER_REPORTED`, `TOKENIZER_ESTIMATED`, and `UNKNOWN` are not modeled.
- No cached token attribution or audio unit tracking.

---

## 4. Existing Provider Pricing and Usage Metadata

### Current State
- **Zero Pricing Registry**: The repository contains no pricing models or cost tables.
- In Phase 8 (`app/services/evaluation/evaluator.py`), a constant cost multiplier was heuristically used (`0.012` per benchmark run) without dynamic model lookup.
- No currency specification, no versioned pricing, no differentiation between input, output, and cached token rates.

---

## 5. Existing Audit Trail

### Current State
- `ToolExecution` model (`app/models/business_entities.py`) logs executed tool calls with `arguments`, `result`, and `execution_time_ms`.
- `PendingToolAction` model (`app/models/pending_tool_action.py`) tracks approvals and rejections of write actions (`create_lead`, `create_support_ticket`).
- `PublicUsageEvent` tracks visitor message and tool counts.

### Gaps
- No unified `AuditEvent` model or audit trail service for administrative and operational actions:
  - AI Employee lifecycle (create, update, publish, prompt change).
  - Knowledge base assignment/unassignment.
  - Tool permission toggles.
  - Budget definitions and threshold violations.
  - Evaluation execution triggers.
- No tamper-evident, append-only tenant audit log API.

---

## 6. Existing AI Employee Testing Workflow

### Current State
- **Chat Route (`/ai-employees/[id]/chat`)**: Company users can converse with their AI Employee.
- **RAG Evaluation Dashboard (`/evaluations`)**: Company users can trigger golden dataset benchmarks to compute IR metrics (Recall@K, MRR, NDCG) and NLG metrics (Faithfulness, Relevance).

### Gaps
- **No Playground**: Testing currently requires modifying the live AI Employee configuration directly in production.
- **No Configuration Snapshots**: An admin cannot experiment with a modified system prompt, different top-K, alternative retrieval mode (e.g. hybrid vs dense), or alternate model without impacting live customer-facing conversations.
- **No Retrieval Inspector**: Admins cannot see which chunks were retrieved, their individual dense vs sparse scores, rerank scores, or text previews for a test query.
- **No Prompt Inspector**: Admins cannot verify how context, system instructions, and chat history were assembled into the prompt.
- **No Tool Sandbox**: Admins cannot safely test tools with mock sandboxed outcomes without either executing live DB actions or relying on production confirmations.

---

## 7. Existing Budget and Rate-Limit Enforcement

### Current State
- **Distributed Rate Limiting (Phase 10)**: `DistributedRateLimiter` enforces sliding-window rate limits in Redis across public endpoints, evaluation runs, and uploads.
- **Zero Financial Budgeting**:
  - No spend limits (daily, weekly, monthly).
  - No soft-limit alert thresholds.
  - No hard-limit blocking mechanism (`BUDGET_EXCEEDED` HTTP 429).
  - No cost aggregation by company or AI Employee.

---

## 8. Missing Capabilities Summary

| Capability | Current Status | Required in Phase 11–13 |
|---|---|---|
| OpenTelemetry Tracing | Missing | W3C traceparent, Tracer/Span abstraction, Context propagation |
| Span Hierarchy | Partial (turn metrics only) | Request -> Retrieval (Dense/Sparse/RRF/Rerank) -> Prompt -> LLM -> Tool |
| Telemetry Redaction | Missing | Central policy masking API keys, credentials, PII, raw secrets |
| Audit Trail | Fragmented | Unified `AuditEvent` table + API for tenant governance |
| AI Employee Playground | Missing | Tenant-isolated sessions, config snapshots, safe execution |
| Retrieval Inspector | Missing | Chunk scores (dense, sparse, RRF, reranker), source preview |
| Prompt Inspector | Missing | Redacted prompt breakdown (system, persona, context, tools) |
| Tool Sandbox | Missing | Safe test environment for tools |
| Config Comparison | Missing | Side-by-side run of Config A vs Config B via evaluation engine |
| Usage Ledger | Missing (only public events) | `UsageLedgerEntry` with decimal-safe cost, provider tokens |
| Pricing Registry | Missing | Versioned `ModelPricingVersion` table & registry |
| Budget Governance | Missing | `UsageBudget` (soft & hard limits), pre-check & reservation |
| Control Plane UI | Missing | Dedicated Playground, Observability, Cost & Budget dashboards |

---

## 9. Files and Models That Can Be Reused

### Models
- `Company`, `User`, `Membership`: Tenant context and RBAC (`OWNER`, `ADMIN`, `MEMBER`).
- `AIEmployee`: Core entity; can be cloned into playground config snapshots.
- `KnowledgeBase`, `Document`, `DocumentChunk`: Used directly by Playground retrieval inspector.
- `Message`, `Conversation`: Retains production chat; playground sessions will use isolated playground conversation models.
- `EvaluationRun`, `EvaluationResultItem`: Reused for configuration comparison benchmarks.

### Services & Components
- `ConversationEngine`: Invoked directly by playground sessions using snapshot overrides.
- `RetrievalService`: Reused for scoped retrieval in both production and playground.
- `PromptBuilder`: Reused for assembling prompts and rendering prompt inspection.
- `ToolRegistry` & `ToolExecutor`: Reused for tool sandbox execution and permission validation.
- `DistributedRateLimiter`: Extends rate limiting to control plane APIs.

---

## 10. Proposed Architecture

```
                          API GATEWAY / FASTAPI
                                    │
                         AUTHENTICATION & TENANT
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
OBSERVABILITY SERVICE        BUDGET SERVICE              PLAYGROUND SERVICE
- OpenTelemetry Context      - Budget Pre-Check          - Session Isolation
- Spans: Retrieval, LLM      - Hard/Soft Limit Checks    - Config Snapshots
- Telemetry Redaction        - Usage Ledger Recording    - Retrieval Inspector
- Trace Summary Storage      - Decimal-safe Costing      - Safe Prompt Inspector
- Audit Event Logging        - Pricing Registry          - Tool Sandbox
       │                            │                            │
       └────────────────────────────┼────────────────────────────┘
                                    │
                           CONVERSATION ENGINE
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
      RETRIEVAL SERVICE        LLM PROVIDERS        TOOL EXECUTOR
      - Dense (Qdrant)         - Gemini Provider    - Tool Registry
      - Sparse (BM25)          - OpenAI Provider    - Sandbox Mode
      - RRF + Reranker         - Usage Extraction   - Confirmations
```

### Relational Schema Additions
1. **Observability**:
   - `TraceSummary`: Persists completed request traces with latency breakdowns, status, and tenant metadata.
   - `AuditEvent`: Append-only tenant audit log.
2. **Playground**:
   - `PlaygroundSession`: Tenant-isolated test session with immutable configuration snapshot.
   - `PlaygroundMessage`: Isolated messages within a playground session.
3. **Usage & Budgets**:
   - `UsageLedgerEntry`: Authoritative consumption record (`input_tokens`, `output_tokens`, `cached_tokens`, `estimated_cost`, `cost_status`, `usage_source`).
   - `ModelPricingVersion`: Versioned pricing rules per provider/model.
   - `UsageBudget`: Company- and employee-level financial caps with soft/hard thresholds.

---

## 11. Migration Strategy

1. **Alembic Migration**:
   - Create tables `trace_summaries`, `audit_events`, `playground_sessions`, `playground_messages`, `model_pricing_versions`, `usage_ledger_entries`, `usage_budgets`.
   - Seed default pricing versions for Gemini (`gemini-3.6-flash`, `gemini-2.5-flash-lite`, etc.) and OpenAI (`gpt-4o`, `gpt-4o-mini`).
2. **Backward Compatibility**:
   - Zero changes to existing table schemas.
   - All new foreign keys reference existing `companies.id` and `ai_employees.id` with `CASCADE` deletes.
   - Existing conversation APIs continue operating without breaking changes.
   - Observability and Budget checks integrate non-intrusively into `ConversationEngine`.

---

## 12. Security and Compatibility Risks

1. **Cross-Tenant Data Leakage**:
   - *Risk*: A tenant accesses another tenant's trace summaries, playground sessions, or usage figures.
   - *Mitigation*: Every query, service call, and API endpoint filters strictly on `company_id` from the authenticated JWT session.
2. **Secret & Credential Exposure in Telemetry**:
   - *Risk*: API keys, bearer tokens, passwords, or customer PII get recorded in span attributes or trace payloads.
   - *Mitigation*: Implement a strict regex-based and key-based `TelemetryRedactor` that masks authorization headers, API keys, passwords, and sensitive keys before serialization.
3. **Double Spending / Concurrency in Budget Limits**:
   - *Risk*: Parallel requests exceed a hard budget simultaneously.
   - *Mitigation*: Centralized atomic checks with Redis or PostgreSQL transaction reservations for high-concurrency requests.
4. **Playground Side-Effects**:
   - *Risk*: A user tests a WRITE tool in playground and updates live production data.
   - *Mitigation*: Sandbox mode flags execution context; WRITE actions are either simulated in-memory or require explicit sandbox approvals.

---

## 13. Dependencies Required

- **OpenTelemetry Standard**: We will provide a clean, native OpenTelemetry-compatible tracing layer implementing W3C TraceContext (`traceparent`, `tracestate`), standard span attributes, and span hierarchy. If `opentelemetry-api` is present, it binds directly; otherwise our built-in zero-dependency telemetry engine provides identical trace summaries and spans without introducing external runtime failure modes.
- **Python Standard Library**: `dataclasses`, `time`, `uuid`, `re`, `decimal`, `typing`, `enum`.
- **Existing Packages**: `pydantic`, `fastapi`, `sqlalchemy`, `redis`, `httpx`.
- No heavy external APM agents or Kubernetes dependencies required.
