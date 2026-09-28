# AVTAAR — FINAL SECURITY & MULTI-TENANT REVIEW

## Security Posture & Isolation Audit

---

### 1. Tenant Isolation Architecture

- **Database-Level Isolation**:
  - Every relational entity (`AIEmployee`, `KnowledgeBase`, `Document`, `DocumentChunk`, `Conversation`, `Message`, `TraceSummary`, `UsageLedgerEntry`, `UsageBudget`, `AuditEvent`) includes a mandatory foreign key `company_id`.
  - All repository and service queries enforce `WHERE company_id = :tenant_company_id`.
  - Automated cross-tenant tests (`test_chat_tenant_isolation.py`, `test_knowledge_tenant_isolation.py`) verify that Company A cannot read, query, or mutate Company B's data under any circumstance.

- **Vector Store Isolation**:
  - Qdrant points are filtered on `must: [{ key: "company_id", match: { value: company_id } }]` and `must: [{ key: "knowledge_base_id", match: { value: kb_id } }]`.
  - Cross-tenant vector retrieval leakage is mathematically impossible at the query filter level.

---

### 2. Authentication & Authorization

- **JWT Tokens**:
  - Signed with cryptographic secret keys using SHA-256 HMAC (`HS256`).
  - Contains user ID, company ID, and role claim (`OWNER`, `ADMIN`, `MEMBER`).
- **Role Scoping**:
  - `OWNER` / `ADMIN`: Allowed to manage budgets, invite members, modify company configuration, and register tools.
  - `MEMBER`: Allowed to test AI employees, upload knowledge docs, view traces, and run evaluations.
  - Public anonymous users: Limited to public preview and chat widget sessions, restricted by allowed CORS domains and rate limiters.

---

### 3. Agent Tool Safety & Action Governance

- **Two-Phase Write Protection**:
  - Write actions (`CREATE_ORDER`, `CANCEL_ORDER`, `CREATE_TICKET`, `CREATE_LEAD`) can NEVER be executed autonomously by LLM tool hallucination or prompt injection.
  - LLM invocation of a write tool produces a `PendingToolAction` record in status `PENDING` with an expiration timestamp (default 15 minutes).
  - Explicit POST confirmation by an authorized user session is required to execute the action.
- **Input Validation & Sanitization**:
  - Tool arguments are validated against strict Pydantic JSON schemas.
  - Arguments with script tags, SQL injection payloads, or unexpected data types are rejected immediately.

---

### 4. Distributed Rate Limiting & Denial of Service Protection

- **Sliding Window Token Bucket**:
  - Redis Lua script executes atomic check-and-decrement.
  - Tenant rate limits (default 100 req/min) and IP burst limits (default 30 req/min) prevent API exhaustion.
- **Fail-Secure Local Fallback**:
  - If Redis is unavailable or unconfigured in development, the in-memory rate limiter strictly maintains tenant burst protection.

---

### 5. PII Redaction & Data Sanitization

- **Audit & Tracing Redaction**:
  - Sensitive parameters (passwords, auth headers, API secrets, email tokens) are automatically redacted using `AuditService.sanitize_metadata()`.
  - Public chat endpoints return clean customer-facing payloads without internal DB keys or API credentials.
