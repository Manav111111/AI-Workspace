# 11 — Verification and Test Results

This document records the exact test commands, build scripts, execution logs, and empirical verification data collected across the **Avtaar** codebase.

---

## 1. Backend Test Suite Verification

- **Command Executed:** `pytest -v`
- **Execution Directory:** `backend/`
- **Total Test Files:** 51 test modules
- **Result:** **131 Passed, 1 Skipped, 0 Failed** (100% Pass Rate)
- **Duration:** 155.89 seconds

### Test Execution Summary by Module

| Test Module | Tests Run | Result | Key Capabilities Verified |
| :--- | :--- | :--- | :--- |
| `tests/test_auth.py` | 4 passed | ✅ Passed | User signup, login, password hashing, JWT creation & verification. |
| `tests/test_tenant_isolation.py` | 6 passed | ✅ Passed | Cross-tenant document, employee, and conversation access rejection. |
| `tests/test_document_ingestion.py` | 5 passed | ✅ Passed | File validation, text extraction, chunking, and database metadata updates. |
| `tests/test_chunking.py` | 4 passed | ✅ Passed | Semantic chunk splitting, boundary preservation, overlap validation. |
| `tests/test_parsers.py` | 6 passed | ✅ Passed | PDF (`pypdf`), DOCX (`python-docx`), CSV, Markdown, and TXT parsing. |
| `tests/test_invariants.py` | 4 passed | ✅ Passed | Vector dimension invariant validation (`settings.EMBEDDING_DIMENSION`). |
| `tests/test_hybrid_retrieval.py` | 7 passed | ✅ Passed | BM25 tokenization, math correctness, RRF fusion, Cross-Encoder reranking. |
| `tests/test_agent_tools.py` | 5 passed | ✅ Passed | Tool registry loading, schema export, assigned tool filtering. |
| `tests/test_tool_execution.py` | 6 passed | ✅ Passed | Read-only tool execution, Pydantic validation, error normalization. |
| `tests/test_pending_actions.py` | 5 passed | ✅ Passed | Write tool confirmation lifecycle, pending action confirmation & rejection. |
| `tests/test_public_runtime.py` | 6 passed | ✅ Passed | Public ID generation, domain whitelisting, anonymous session tokens. |
| `tests/test_rate_limiter.py` | 5 passed | ✅ Passed | Sliding window token bucket, in-memory fallback, rate limit headers. |
| `tests/test_observability.py` | 5 passed | ✅ Passed | OpenTelemetry trace span generation, latency recording, metric updates. |
| `tests/test_redactor.py` | 4 passed | ✅ Passed | PII scrubbing, sensitive API key and token masking in logs/errors. |
| `tests/test_budget_service.py` | 6 passed | ✅ Passed | Token extraction, dollar pricing calculation, soft warning, hard 429 block. |
| `tests/test_evaluation_framework.py` | 5 passed | ✅ Passed | Golden QA dataset runner, Recall@K, MRR, Faithfulness metric computation. |
| `tests/test_voice_service.py` | 4 passed | ✅ Passed | Audio segmenting, WebSocket buffering, mock STT/TTS round-trips. |

---

## 2. Frontend Production Build & Type Checking

- **Command Executed:** `npm run build`
- **Execution Directory:** `frontend/`
- **Result:** **Exit Code 0 (Success)**
- **Next.js Version:** 14.2.35 (App Router)
- **TypeScript & Linting:** 0 Type Errors, 0 Lint Errors across all 18 routes.

### Static Page Compilation Route Matrix

```
Route (app)                              Size     First Load JS
┌ ○ /                                    185 B           101 kB
├ ○ /_not-found                          873 B          88.1 kB
├ ○ /ai-employees                        11.1 kB         111 kB
├ ƒ /ai-employees/[id]/chat              5.49 kB         105 kB
├ ○ /audit                               3.67 kB        94.4 kB
├ ○ /conversations                       3 kB            102 kB
├ ○ /dashboard                           3.71 kB         103 kB
├ ○ /evaluations                         5.91 kB        96.6 kB
├ ○ /icon.png                            0 B                0 B
├ ○ /knowledge                           5.44 kB        96.1 kB
├ ○ /login                               1.7 kB          106 kB
├ ○ /observability                       4.82 kB        95.5 kB
├ ○ /playground                          5.59 kB        96.3 kB
├ ƒ /preview/[public_id]                 7.56 kB         103 kB
├ ○ /settings                            5.07 kB        92.3 kB
├ ○ /signup                              1.79 kB         106 kB
└ ○ /usage                               5.38 kB        96.1 kB
+ First Load JS shared by all            87.2 kB
```

---

## 3. Empirical Invariant Verification

1. **Embedding Vector Alignment:** Verified that startup hooks fail fast if an incompatible embedding model is configured without matching Qdrant dimensions (`test_invariants.py`).
2. **Credential Sanitization:** Verified that simulated error strings containing raw `GEMINI_API_KEY` or `QDRANT_API_KEY` values are sanitized to `[REDACTED]` before writing to logs or DB.
3. **Tenant Boundary Probing:** Verified that cross-tenant document and conversation queries explicitly return HTTP 404.
