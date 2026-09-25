# PHASE 10 — DISTRIBUTED RATE LIMITING POLICY & FAIL-SAFE MATRIX
**Avtaar Enterprise Multi-Tenant AI Employee SaaS Platform**
**Author:** Principal AI Engineer

---

## 1. Overview

Rate limiting in a multi-tenant AI Employee platform serves two critical purposes:
1. **Security & Abuse Prevention**: Protects public runtimes and chat widgets against automated credential stuffing, session enumeration, and message flooding.
2. **Resource & Cost Protection**: Prevents tenants or rogue actors from exhausting GPU/LLM quotas, Qdrant vectors, disk storage, or backend worker threads.

Avtaar employs a **Redis-backed distributed sliding-window counter** with atomic Lua/sorted-set execution. When Redis is unavailable or times out, the system applies an explicit **Fail-Open vs. Fail-Closed policy** per endpoint category.

---

## 2. Policy & Fail-Safe Matrix

| Category | Endpoint / Action | Limit | Scoped Key Structure | Failure Behavior (Redis Down) | Rationale |
|---|---|---|---|---|---|
| **Public Config** | `GET /public/employees/{id}/config` | 60 req / min | `rl:pub:cfg:{ip}` | **Fail-Open with local fallback** | Widget configuration is low-overhead; failing closed breaks widget rendering for legitimate visitors during transient Redis blips. |
| **Public Session Creation** | `POST /public/employees/{id}/sessions` | 20 req / min | `rl:pub:sess:{ip}` | **Fail-Closed** | High abuse surface; unauthenticated bot floods creating hundreds of public sessions fill database storage and bypass employee licensing. |
| **Public Chat Messaging** | `POST /public/chat/{id}/message` | 30 req / min | `rl:pub:msg:{session_id}:{ip}` | **Fail-Closed** | High cost endpoint; each message invokes Gemini LLM generation and Qdrant retrieval. Failing open allows costly denial-of-wallet attacks. |
| **Voice AI WebSockets** | `WS /voice/stream` (Handshake) | 10 conns / min per IP | `rl:voice:conn:{ip}` | **Fail-Closed** | WebSockets consume persistent server threads and audio streaming buffers; strictly bounded. |
| **Voice Active Sessions** | `WS /voice/stream` (Concurrent) | 5 concurrent per tenant | `rl:voice:active:{company_id}` | **Fail-Open with local fallback** | Authenticated tenant voice calls must not be interrupted if Redis restarts during a call. Local fallback maintains process-level safety. |
| **Document Uploads** | `POST /documents/upload`, `POST /knowledge-bases/{id}/documents` | 10 uploads / min per tenant | `rl:ingest:upl:{company_id}` | **Fail-Open with local fallback** | Authenticated admin/owner action. Local memory fallback restricts upload flooding; failing open allows business document uploads to proceed. |
| **Concurrent Ingestion** | Worker processing queue | Max 3 concurrent per tenant | `rl:ingest:act:{company_id}` | **Fail-Open (DB guarded)** | Database state machine (`IngestionJob.status == 'PROCESSING'`) acts as secondary distributed invariant. |
| **RAG Evaluation Runs** | `POST /evaluations/run` | 5 runs / hour per tenant | `rl:eval:run:{company_id}` | **Fail-Closed** | Expensive LLM benchmarking operation running up to 80 LLM calls per dataset; failing closed prevents accidental quota drainage. |
| **Internal / Health** | `GET /health`, `GET /ready` | Unlimited | None | **Bypass** | Infrastructure liveness probes must never be rate limited. |

---

## 3. Scoped Key Design Rules

1. **Multi-Tenant Isolation**: Authenticated keys MUST include `company_id`. Never allow Company A's activity to increment Company B's counter.
2. **Compound Public Scope**: Public endpoints without company authentication MUST combine the action, client IP, and target `ai_employee_id` or `session_id` to prevent IP spoofing attacks from blocking entire subnets.
3. **Structured Namespace Prefix**: All rate-limiting keys begin with `rl:` followed by the domain (`pub`, `ingest`, `eval`, `voice`) and metric type.

---

## 4. HTTP 429 Response Specification

When an endpoint denies a request due to rate limiting, it returns `HTTP 429 Too Many Requests` with RFC 6585 compliance:

### HTTP Headers:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 15
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1727189430
Content-Type: application/json
```

### JSON Body:
```json
{
  "error": "RATE_LIMITED",
  "message": "Too many requests. Please wait a moment before trying again.",
  "retry_after_seconds": 15,
  "scope": "public_message"
}
```

---

## 5. Redis Failure Resilience & Fallback Engine

1. **Connection Timeout**: Redis commands use a strict `socket_timeout = 0.5s` and `connect_timeout = 0.5s`.
2. **Local Sliding Window Fallback**: If Redis raises `ConnectionError`, `TimeoutError`, or `ResponseError`:
   - If the endpoint policy is **Fail-Open with local fallback**, the request is checked against the local in-process `SlidingWindowCounter`.
   - If the endpoint policy is **Fail-Closed**, an `HTTP 429` (or `HTTP 503 Service Unavailable` with `Service Degraded` header) is raised with a warning logged.
3. **Structured Alerting**:
   Every fallback event emits a structured log:
   `[WARNING] app.services.rate_limit: Redis unreachable for key 'rl:pub:msg:...'. Applying policy 'FAIL_CLOSED'.`
