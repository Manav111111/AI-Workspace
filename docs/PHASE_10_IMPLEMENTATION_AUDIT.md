# PHASE 10 — IMPLEMENTATION AUDIT
**Asynchronous Document Ingestion + Distributed Rate Limiting**
**Avtaar Enterprise Multi-Tenant AI Employee SaaS Platform**
**Author:** Principal AI Engineer

---

## 1. Executive Summary

Phase 9 established Avtaar's hybrid retrieval engine (`RETRIEVAL_MODE=hybrid`) as the measured production standard (+15.4% MRR improvement, +26.2% Recall@3 improvement over dense-only baseline). However, the Phase 9 audit and implementation revealed two major production infrastructure gaps:
1. **Synchronous Ingestion Bottleneck**: Document uploads (`POST /knowledge-bases/{kb_id}/documents` and `POST /documents/upload`) block the FastAPI HTTP worker while synchronously reading files, parsing (`pdf`, `docx`, `csv`, `markdown`), chunking, calling Gemini embedding APIs in batches, and upserting points to Qdrant Cloud. Large documents (> 1 MB or > 50 pages) cause request timeouts (504 Gateway Timeout) and tie up API workers.
2. **In-Memory Volatile State**:
   - Rate limiting in `backend/app/services/public_runtime/rate_limit.py` uses an in-memory `defaultdict(list)`.
   - Voice runtime active session tracking in `backend/app/api/v1/voice.py` uses an in-process dictionary (`ACTIVE_VOICE_SESSIONS`).
   - BM25 tenant lexical index caching in `backend/app/services/retrieval/sparse.py` uses an in-process `TenantBM25CacheManager`.
   - Crucially, `ingestion.py` currently **never invalidates** `global_bm25_cache`, meaning newly ingested chunks are invisible to lexical search until the 30-minute cache TTL expires.
   - When scaling Avtaar to multiple Uvicorn worker processes or Docker containers, process-local memory is not shared, breaking rate limiting and causing index inconsistencies.

Phase 10 solves both problems by implementing:
- An asynchronous, idempotent, recoverable **Ingestion Job & Worker Pipeline** with stage-based progress tracking and automatic BM25 index invalidation.
- A **Redis-Backed Distributed Rate Limiter** with atomic sliding-window operations, per-endpoint policy enforcement, and resilient fallback handling.

---

## 2. Answers to Specific Repository Audit Questions

### Q1: Is Redis already available?
- **Configuration**: `REDIS_URL: str = "redis://localhost:6379/0"` is defined in `backend/app/core/config.py`.
- **Packages**: `redis>=5.0.3` is installed in `backend/requirements.txt` and `.venv`.
- **Infrastructure**: `docker-compose.yml` specifies a `redis:7-alpine` container on port `6379` with volume persistence and health checks.
- **Local Dev State**: In local Windows development outside Docker, port `6379` is closed by default unless Docker is launched. Therefore, the implementation must be resilient to Redis connection drops and provide local fallback for tests and standalone mode.

### Q2: Is Redis currently used only as an abstraction or actually connected?
- **Finding**: Redis is currently **not connected anywhere** in runtime code. All existing rate limiters, session trackers, and caches use process-local Python dictionaries (`dict`, `defaultdict`). Redis was only defined in `config.py` and `docker-compose.yml`.

### Q3: Is there an existing job/task abstraction?
- **Finding**: None. `backend/app/workers/__init__.py` contains only a docstring placeholder: *"Workers Module (Placeholder for Phase 1+) This module is reserved for background tasks, async ingestion pipelines, and Celery / Redis task runners."*
- There is no `IngestionJob` model in the database.

### Q4: How is ingestion currently triggered?
- Ingestion is triggered directly inside the HTTP request handlers:
  - `POST /api/v1/knowledge-bases/{kb_id}/documents` (`upload_document` in `backend/app/api/v1/knowledge_bases.py`)
  - `POST /api/v1/documents/upload` (`upload_document_direct` in `backend/app/api/v1/documents.py`)
- Both endpoints call `DocumentService.upload_and_process_document(...)`, which directly invokes `IngestionService.process_document(...)`.

### Q5: Is ingestion synchronous inside the request?
- **YES**. The HTTP request blocks waiting for:
  1. Local storage file write
  2. `Document` DB record insert with `UPLOADED` status
  3. `IngestionService.process_document`:
     - File binary read from disk
     - Parser selection and text extraction (`pdf`, `docx`, `txt`, `csv`, `md`)
     - Text cleaning and normalization
     - Semantic chunking (`ChunkingService`)
     - Gemini dense embedding batch calls (`batchEmbedContents`, 384-dim)
     - Vector dimension validation
     - Chunk deletion and Qdrant vector deletion (for idempotency)
     - `DocumentChunk` records inserted into database
     - Qdrant Cloud point upserts
     - `Document` status updated to `PROCESSED`
- Average synchronous upload duration observed: **3.5s to 18.2s** per document.

### Q6: How is document status represented?
- In `backend/app/models/document.py`, `DocumentStatus` enum:
  - `UPLOADED`
  - `PROCESSING`
  - `PROCESSED`
  - `FAILED`
  - `DELETED`
- Status transitions are currently coarse: `UPLOADED` → `PROCESSING` → `PROCESSED` (or `FAILED`). There is no `QUEUED` state, no progress percentage, and no current stage indicator.

### Q7: Can duplicate ingestion currently happen?
- **YES**. If a client double-clicks upload or retries a timed-out HTTP request while the first is still running, both requests invoke `process_document` simultaneously. While `chunk_repo.delete_by_document` is called before insertion, concurrent executions interleave, creating race conditions, duplicate `DocumentChunk` records, and redundant Qdrant API calls.
- There is no database lock, unique active job constraint, or idempotency token.

### Q8: How are Qdrant upserts performed?
- Implemented in `backend/app/services/qdrant_service.py`:
  - `upsert_chunks(company_id, knowledge_base_id, document_id, chunk_records, embeddings)`
  - Creates `PointStruct` instances using `uuid.UUID(str(chunk["id"]))`.
  - Attaches payload metadata: `company_id`, `knowledge_base_id`, `document_id`, `chunk_index`, `content`, `metadata`.
  - Vectors are deleted per document via `delete_document_vectors(company_id, document_id)`.
  - Point IDs are tied deterministically to chunk UUIDs, which makes Qdrant upserting idempotent if chunk IDs are deterministic.

### Q9: How are BM25 indexes populated/invalidated?
- In `backend/app/services/retrieval/sparse.py`:
  - `TenantBM25CacheManager` stores in-memory BM25 indices keyed by `(company_id, tuple(sorted(kb_ids)))`.
  - On retrieval queries, if not cached or expired (TTL = 1800s), it loads chunks from the database and compiles the BM25 index.
  - While `TenantBM25CacheManager.invalidate(company_id)` is defined, it is **never called** by `ingestion.py` or `document.py`.
  - When new documents are ingested or deleted, the BM25 index remains stale for up to 30 minutes!

### Q10: How does rate limiting currently work?
- `SlidingWindowRateLimiter` in `backend/app/services/public_runtime/rate_limit.py`:
  - Uses an in-memory `defaultdict(list)` mapping keys to timestamp lists.
  - On each call to `is_allowed`, prunes timestamps older than `now - window_seconds`.
  - Raises `HTTPException(429, ...)` if request count exceeds limit.
  - **Limitations**: Process-local only. No `Retry-After` HTTP header. No structured error schema. Fails completely across multi-worker deployments.

### Q11: Which endpoints are currently rate-limited?
- Only 3 public endpoints in `backend/app/api/v1/public.py`:
  1. `GET /public/employees/{public_id}/config` (60 req/min by IP)
  2. `POST /public/employees/{public_id}/sessions` (20 req/min by IP)
  3. `POST /public/chat/{public_id}/message` (30 req/min by IP)
- In `backend/app/api/v1/voice.py`:
  - Concurrent voice sessions are checked against `VOICE_MAX_CONCURRENT_SESSIONS_PER_TENANT` using a process-local dictionary (`ACTIVE_VOICE_SESSIONS`).
- **Unprotected Endpoints**:
  - `POST /documents/upload` and `POST /knowledge-bases/{kb_id}/documents` (zero rate limits or concurrency limits; vulnerable to resource exhaustion).
  - `POST /evaluations/run` (zero rate limits; vulnerable to runaway LLM judge costs).

### Q12: Are multiple backend workers supported?
- **NO**. If Uvicorn is launched with `--workers 4` or if multiple containers run behind a load balancer:
  - Each worker has its own independent rate limit counters (allowing 4x the intended traffic).
  - Each worker tracks voice connections separately (allowing 4x concurrent voice sessions).
  - BM25 caches remain desynchronized across workers.

### Q13: How does frontend currently poll document status?
- **Finding**: The frontend currently **does not poll**.
  - `frontend/src/app/(dashboard)/knowledge/page.tsx` calls `await api.uploadDocument(...)`, which blocks until completion, then calls `loadDocuments(...)`.
  - If a document is in `PROCESSING` status, the UI renders an amber badge without auto-refreshing, stage info, or retry options.

---

## 3. Proposed Phase 10 Architecture

```
                                  CLIENT
                                    |
               +--------------------+--------------------+
               | (File Upload)                           | (API Request)
               ↓                                         ↓
          POST /documents                        Protected Endpoint
               |                                         |
               ↓                                         ↓
      FastAPI Request Handler                  RedisRateLimiter
    - Validate Tenant & KB                   - Atomic Sliding Window
    - Save File to Storage                   - Evaluate Scope (Tenant/IP)
    - Insert Document (QUEUED)               - Allow or Deny (HTTP 429)
    - Insert IngestionJob (QUEUED)                       |
    - Enqueue Job                                        ↓
               |                                  Execute Handler
               ↓
        HTTP 202 Accepted
     {"document_id": "...",
      "job_id": "...",
      "status": "QUEUED"}
               |
               +-----------------------------------------+
                                                         |
                                                         ↓
                                                Background Worker
                                            (IngestionTaskProcessor)
                                            - Durable DB State Machine
                                            - Redis Queue / Async Loop
                                            - Bounded Concurrency
                                                         |
                   +-------------------------------------+-------------------------------------+
                   |                                                                           |
                   ↓                                                                           ↓
        Stage 1: PARSING (10%)                                                      Failure & Retry Handler
        Stage 2: CLEANING (25%)                                                     - Bounded Retries (max 3)
        Stage 3: CHUNKING (40%)                                                     - Exponential Backoff
        Stage 4: EMBEDDING (60%)                                                    - Stale Job Sweeper
        Stage 5: VECTOR_UPSERT (85%) [Qdrant]                                       - Structured Error Code
        Stage 6: INDEX_INVALIDATE (95%) [BM25]
        Stage 7: COMPLETED (100%)
```

---

## 4. Key Engineering Design Decisions

### 1. IngestionJob Persistence Model
- Create `IngestionJob` table:
  - `id`: UUID primary key
  - `company_id`: UUID foreign key (strict tenant isolation)
  - `knowledge_base_id`: UUID foreign key
  - `document_id`: UUID foreign key
  - `status`: `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`, `CANCELLED`
  - `attempt_count`: integer (default 0)
  - `max_attempts`: integer (default 3)
  - `progress_percent`: integer (0 to 100)
  - `current_stage`: string (`QUEUED`, `PARSING`, `CLEANING`, `CHUNKING`, `EMBEDDING`, `VECTOR_UPSERT`, `INDEX_UPDATE`, `COMPLETED`)
  - `error_code`: string (e.g., `PARSER_ERROR`, `EMBEDDING_PROVIDER_ERROR`, `VECTOR_STORE_ERROR`)
  - `error_message`: text (sanitized)
  - `started_at`, `completed_at`, `created_at`, `updated_at`
- **Database Invariant**: Only one active (`QUEUED` or `PROCESSING`) job may exist per document at any time.

### 2. Document Status Alignment
- Expand `DocumentStatus` in `backend/app/models/document.py` to:
  - `UPLOADED`, `QUEUED`, `PROCESSING`, `PROCESSED`, `FAILED`, `DELETED`.
- Backward compatible with existing records.

### 3. Worker Architecture: Hybrid Durable Queue
- **Source of Truth**: Database (`IngestionJob` records).
- **Notification Transport**: Redis queue (`LPUSH`/`BRPOP`) when Redis is available, with an automatic in-process async loop fallback for local dev / tests.
- This ensures:
  1. Zero job loss even if Redis restarts.
  2. Immediate processing when Redis is available.
  3. Works in pure local SQLite / PostgreSQL dev environments without requiring a standalone Redis service.

### 4. BM25 Cache Invalidation
- Upon successful document ingestion or deletion:
  - Call `global_bm25_cache.invalidate(company_id=job.company_id)`.
  - Next retrieval query dynamically re-indexes the tenant chunks.
  - When Redis is active, publish an index invalidation event across workers.

### 5. Distributed Rate Limiter
- Create `DistributedRateLimiter` (`backend/app/services/rate_limit/`):
  - **Primary**: Redis atomic sliding-window using sorted sets (`ZADD`, `ZREMRANGEBYSCORE`, `ZCARD`, `EXPIRE`) or atomic counter pipelines.
  - **Fallback**: Thread-safe in-memory sliding window when Redis is disconnected.
  - **Headers**: Returns `Retry-After: <seconds>`, `X-RateLimit-Limit`, and `X-RateLimit-Remaining`.
  - **Response**: Standardized HTTP 429 response:
    ```json
    {
      "error": "RATE_LIMITED",
      "message": "Too many requests. Please retry in 12 seconds.",
      "retry_after_seconds": 12
    }
    ```

---

## 5. Files to Inspect, Create, and Modify

| Component | Target File | Action |
|---|---|---|
| Ingestion Job Model | `backend/app/models/ingestion_job.py` | Create model with indexes |
| Models Registry | `backend/app/models/__init__.py` | Export `IngestionJob`, `JobStatus` |
| Document Model | `backend/app/models/document.py` | Add `QUEUED` to `DocumentStatus` |
| Ingestion Job Repository | `backend/app/repositories/ingestion_job.py` | Create CRUD & atomic status transitions |
| Ingestion Worker | `backend/app/workers/ingestion_worker.py` | Create background worker with stages & retry |
| Document Service | `backend/app/services/document.py` | Update `upload_document` to enqueue job |
| Document API | `backend/app/api/v1/documents.py` | Add `GET /{id}/status`, `POST /{id}/retry`, `POST /{id}/cancel` |
| KB Document API | `backend/app/api/v1/knowledge_bases.py` | Return HTTP 202 Accepted on upload |
| Redis Rate Limiter | `backend/app/services/rate_limit/redis_limiter.py` | Create atomic sliding-window limiter |
| Rate Limit Policy | `docs/PHASE_10_RATE_LIMIT_POLICY.md` | Document all endpoint limit policies |
| Public API Rate Limiting | `backend/app/api/v1/public.py` | Use distributed limiter |
| Evaluation API Rate Limiting | `backend/app/api/v1/evaluations.py` | Add concurrency and rate limit checks |
| Voice WebSocket Concurrency | `backend/app/api/v1/voice.py` | Use distributed counter |
| BM25 Invalidation | `backend/app/services/retrieval/sparse.py` | Integrate cache eviction hooks |
| Frontend KB Page | `frontend/src/app/(dashboard)/knowledge/page.tsx` | Add status polling, progress bar, retry button |
| Frontend API Client | `frontend/src/lib/api.ts` | Add `getDocumentStatus`, `retryDocumentIngestion` |
| Tests | `backend/tests/test_async_ingestion.py`, `test_distributed_rate_limit.py` | Comprehensive test suite |
| Report | `docs/PHASE_10_REPORT.md` | Final 20-section report |

---

## 6. Risks & Compatibility Considerations

1. **Database Schema Migration**:
   - Adding `IngestionJob` table and `DocumentStatus.QUEUED` must be backward-compatible with existing SQLite and PostgreSQL tables without requiring table drops.
2. **API Backward Compatibility**:
   - `POST /knowledge-bases/{kb_id}/documents` will return `HTTP 202 Accepted` with `DocumentRead` where `status="QUEUED"`. Clients expecting instant `PROCESSED` must poll or display the `QUEUED` state.
3. **Redis Local Dependency**:
   - The test suite and local environment must pass whether Redis is running or not. The limiter must provide transparent fail-safe fallback.

Audit complete. Proceeding to implementation.
