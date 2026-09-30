# 02 — Complete Feature Audit

This document provides a comprehensive, file-by-file, end-to-end audit of every implemented feature across all development phases (Phases 0–13) in the **Avtaar AI Employee Platform**.

---

## Phase 0 — Platform Foundation & Multi-Tenancy

### 1. What It Does
Provides the core multi-tenant architectural backbone: secure company workspaces, user management with role-based memberships (OWNER, ADMIN, MEMBER), JWT-based stateless authentication, and AI Employee provisioning and configuration.

### 2. Why Avtaar Needs It
In an enterprise B2B SaaS platform, strict logical data separation is non-negotiable. No organization should ever be able to view, query, or mutate another organization's AI Employees, documents, or conversation records.

### 3. How It Is Implemented
- Authentication utilizes bcrypt password hashing with signed HS256 JWT access tokens.
- FastAPI dependency injection (`app/api/deps.py:get_current_tenant`) intercepts every incoming HTTP request, extracts the `Authorization: Bearer <token>` header, verifies the active membership, and produces an immutable `TenantContext` containing `company_id`, `user_id`, and `role`.
- Every SQLAlchemy query filters explicitly with `.where(Model.company_id == tenant.company_id)`.

### 4. Implementation Files & Classes
- **Models:** [`app/models/company.py:Company`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/models/company.py), [`app/models/user.py:User`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/models/user.py), [`app/models/membership.py:Membership`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/models/membership.py), [`app/models/ai_employee.py:AIEmployee`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/models/ai_employee.py)
- **Dependencies:** [`app/api/deps.py:get_current_tenant`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/api/deps.py), `get_db`
- **Endpoints:** [`app/api/v1/auth.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/api/v1/auth.py) (`/login`, `/signup`, `/me`), [`app/api/v1/companies.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/api/v1/companies.py), [`app/api/v1/ai_employees.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/api/v1/ai_employees.py)
- **Services:** [`app/services/auth.py:AuthService`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/auth.py), [`app/services/ai_employee.py:AIEmployeeService`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/ai_employee.py)

### 5. Data Flow
`Client Request` ➔ `StructuredLoggingMiddleware` ➔ `get_current_tenant` (Auth Token Decode & DB Membership lookup) ➔ `TenantContext` ➔ `AIEmployeeRepository` (Scoped DB Query) ➔ `JSON Response`.

### 6. Test Coverage
- `tests/test_auth.py`, `tests/test_ai_employees.py`, `tests/test_tenant_isolation.py`

### 7. End-to-End Status: ✅ **Fully Functional & Verified**

### 8. Limitations & Risks
- Refresh tokens are not currently implemented (tokens are single access tokens with configurable expiration).
- MFA/SSO (SAML/OIDC) is not yet supported.

---

## Phase 1 — Knowledge Ingestion & Vector Storage

### 1. What It Does
Handles the upload, validation, parsing, semantic chunking, embedding generation, and vector database indexing of unstructured business documents (PDF, DOCX, CSV, MD, TXT).

### 2. Why Avtaar Needs It
AI Employees require accurate, domain-specific organizational knowledge to answer customer queries without hallucinating generic web knowledge.

### 3. How It Is Implemented
- Uploaded files are validated against allowed MIME types and size limits ($<25\text{ MB}$).
- Document parsers extract clean, standardized text:
  - `pypdf` for PDF documents.
  - `python-docx` for Word documents.
  - `csv` / `pandas` tabular streaming for CSVs.
  - Native UTF-8 normalization for Markdown and TXT.
- The `ChunkingService` splits text recursively using configurable chunk sizes (default 500 characters) and overlap (50 characters) with paragraph/sentence boundary awareness.
- Embeddings are generated via `EmbeddingService` (Google Gemini `text-embedding-004` or CPU fallback).
- Invariants are verified before insertion (`validate_vectors_before_insert`), ensuring zero vector dimension mismatches.
- Points are indexed in Qdrant with payload metadata containing `company_id`, `knowledge_base_id`, `document_id`, `chunk_id`, and `text`.

### 4. Implementation Files & Classes
- **Parsers:** [`app/services/parsers/`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/parsers) (`pdf.py`, `docx.py`, `csv.py`, `text.py`, `markdown.py`)
- **Services:** [`app/services/ingestion.py:IngestionService`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/ingestion.py), [`app/services/chunking.py:ChunkingService`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/chunking.py), [`app/services/embeddings.py:EmbeddingService`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/embeddings.py), [`app/services/qdrant_service.py:QdrantService`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/qdrant_service.py)
- **Invariants:** [`app/services/invariants.py:validate_vectors_before_insert`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/invariants.py)
- **Endpoints:** [`app/api/v1/documents.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/api/v1/documents.py)

### 5. Data Flow
`File Upload` ➔ `StorageService.save` ➔ `get_parser_for_file` ➔ `ChunkingService.chunk_text` ➔ `EmbeddingService.generate_embeddings` ➔ `validate_vectors_before_insert` ➔ `Qdrant.upsert_points` (Filtered by `company_id`) ➔ `DocumentStatus.COMPLETED`.

### 6. Test Coverage
- `tests/test_document_ingestion.py`, `tests/test_chunking.py`, `tests/test_parsers.py`, `tests/test_invariants.py`

### 7. End-to-End Status: ✅ **Fully Functional & Verified**

### 8. Limitations & Risks
- OCR for scanned image-only PDFs is not enabled (requires Tesseract integration).
- Default file storage writes to local filesystem disk (`app/services/storage.py:LocalStorageService`) rather than AWS S3 / Google Cloud Storage.

---

## Phase 2 — RAG & Conversation Engine

### 1. What It Does
Coordinates conversational turns between users and AI Employees: manages conversation sessions, retrieves relevant knowledge base chunks, constructs injection-resistant system prompts, queries LLM providers, and synthesizes answers with source citations.

### 2. Why Avtaar Needs It
Provides grounded, truthful, and citation-backed conversational responses while strictly preventing prompt injection and data hallucination.

### 3. How It Is Implemented
- `ConversationEngine` loads active conversation history from PostgreSQL/SQLite.
- `RetrievalService` executes multi-tenant search across assigned knowledge bases.
- `PromptBuilder` wraps retrieved context chunks inside XML-tagged delimiters (`<context><chunk id="1">...</chunk></context>`) with strict instructions forbidding the model from answering outside the provided context.
- Fallback instructions ensure that if no relevant chunks are found or the query is unsupported, the AI Employee outputs a courteous no-answer response rather than fabricating information.
- Response citations are extracted and mapped to chunk source metadata (`page_number`, `source_filename`, `chunk_id`).

### 4. Implementation Files & Classes
- **Engine:** [`app/services/conversation_engine.py:ConversationEngine`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/conversation_engine.py)
- **Prompting:** [`app/services/prompt_builder.py:PromptBuilder`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/prompt_builder.py)
- **LLM Abstraction:** [`app/services/llm/`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/llm) (`gemini_provider.py`, `openai_provider.py`, `mock_provider.py`)
- **Endpoints:** [`app/api/v1/conversations.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/api/v1/conversations.py)

### 5. Data Flow
`User Message` ➔ `ConversationEngine.process_message` ➔ `RetrievalService.retrieve` ➔ `PromptBuilder.build_messages` ➔ `LLMProvider.generate` ➔ `Response Formatting & Citations` ➔ `DB Message Persistence` ➔ `Client Response`.

### 6. Test Coverage
- `tests/test_conversation_engine.py`, `tests/test_prompt_builder.py`, `tests/test_rag_pipeline.py`

### 7. End-to-End Status: ✅ **Fully Functional & Verified**

### 8. Limitations & Risks
- Multi-query expansion (generating 3-5 query variants) is not yet active in the default single-turn retrieval flow.

---

## Phase 3 — Agents & Tool Execution Engine

### 1. What It Does
Empowers AI Employees to take real-world actions by executing structured business tools (e.g., `create_lead`, `create_support_ticket`, `order_lookup`, `product_search`). Provides a secure sandbox with permission checks, parameter validation, idempotent execution, and human-in-the-loop confirmation for state-mutating operations.

### 2. Why Avtaar Needs It
An AI Employee is not just a passive knowledge retrieval system; it must be able to resolve business workflows autonomously while safeguarding critical systems from accidental or malicious mutations.

### 3. How It Is Implemented
- `ToolRegistry` registers tools with strict JSON schemas and permission tags (`READ_ONLY` vs `REQUIRES_CONFIRMATION`).
- `AgentOrchestrator` runs a bounded ReAct reasoning loop (maximum 5 iterations).
- When a tool requiring confirmation is invoked, `ToolExecutor` pauses execution, persists a `PendingToolAction` in the database, and returns a confirmation card payload to the user.
- Upon explicit user confirmation via `/api/v1/tools/confirm/{id}`, execution resumes with `bypass_confirmation=True`.
- Every tool call produces an immutable `ToolExecution` audit log record with input arguments, output results, execution duration, and status.

### 4. Implementation Files & Classes
- **Registry & Execution:** [`app/services/agent/tool_registry.py:ToolRegistry`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/agent/tool_registry.py), [`app/services/agent/tool_executor.py:ToolExecutor`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/agent/tool_executor.py), [`app/services/agent/orchestrator.py:AgentOrchestrator`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/agent/orchestrator.py)
- **Business Tools:** [`app/services/agent/tools/`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/agent/tools) (`create_lead.py`, `create_support_ticket.py`, `order_lookup.py`, `product_search.py`)
- **Models:** [`app/models/pending_tool_action.py:PendingToolAction`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/models/pending_tool_action.py), [`app/models/business_entities.py:ToolExecution`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/models/business_entities.py)
- **Endpoints:** [`app/api/v1/tools.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/api/v1/tools.py)

### 5. Data Flow
`LLM Tool Call Request` ➔ `ToolRegistry.get_tool` ➔ `AI Employee Permission Verification` ➔ If write action: `Create PendingToolAction (PENDING)` ➔ `Return Confirmation Request to User` ➔ `User Clicks Confirm` ➔ `ToolExecutor.execute_confirmed_action` ➔ `Audit Log Recorded` ➔ `Result Returned`.

### 6. Test Coverage
- `tests/test_agent_tools.py`, `tests/test_tool_execution.py`, `tests/test_pending_actions.py`

### 7. End-to-End Status: ✅ **Fully Functional & Verified**

### 8. Limitations & Risks
- Dynamic third-party tool integrations (e.g. arbitrary OpenAPI spec import or Zapier webhooks) require manual tool wrapper registration.

---

## Phase 4 — Public AI Employee Runtime & Embeddable Widget

### 1. What It Does
Allows published AI Employees to be embedded on external websites via a single JavaScript tag (`<script src=".../widget.js" data-employee-id="..."></script>`). Manages anonymous visitor sessions, token authentication, and domain whitelisting.

### 2. Why Avtaar Needs It
Enables businesses to deploy their AI Employees directly on customer-facing websites, helpdesks, and portals without requiring end-users to authenticate with Avtaar accounts.

### 3. How It Is Implemented
- Employees have a publishing toggle and an immutable `public_id`.
- `app/api/v1/public.py:create_public_session` validates origin domain headers against the AI Employee's `allowed_domains` configuration.
- Issues a signed, short-lived session JWT scoped strictly to that public session.
- `frontend/public/widget.js` is a standalone, lightweight (zero external dependencies) script providing a responsive chat floating bubble, message streaming, interactive confirmation cards, and SVG avatar animations.

### 4. Implementation Files & Classes
- **Backend Service:** [`app/services/public_runtime/`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/public_runtime) (`security.py`, `session_manager.py`)
- **Endpoints:** [`app/api/v1/public.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/api/v1/public.py)
- **Frontend Asset:** [`frontend/public/widget.js`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/frontend/public/widget.js), [`frontend/src/app/preview/[public_id]/page.tsx`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/frontend/src/app/preview/%5Bpublic_id%5D/page.tsx)

### 5. Data Flow
`Website loads widget.js` ➔ `POST /api/v1/public/sessions` (with Origin check) ➔ `Session JWT Issued` ➔ `POST /api/v1/public/chat` (Scoped conversation) ➔ `Widget renders response`.

### 6. Test Coverage
- `tests/test_public_runtime.py`, `tests/test_widget_security.py`

### 7. End-to-End Status: ✅ **Fully Functional & Verified**

### 8. Limitations & Risks
- When `allowed_domains` is set to `["*"]`, widget can be loaded from any origin; enterprise deployments must configure exact domains.

---

## Phases 5–7 — Voice & Avatar Presentation Layer

### 1. What It Does
Provides speech-to-text (STT), text-to-speech (TTS), real-time bi-directional audio WebSocket streaming, and visual avatar emotion/gesture state orchestration.

### 2. Why Avtaar Needs It
Enables voice-first and avatar-assisted conversational experiences for customer service kiosks and hands-free interaction.

### 3. How It Is Implemented
- **Voice Runtime:** [`app/services/voice/runtime.py:VoiceRuntime`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/voice/runtime.py) manages WebSocket sessions with audio chunk buffering, silence detection / segmentation, OpenAI Whisper STT transcription, conversation engine invocation, and OpenAI TTS audio generation.
- **Avatar State Engine:** [`app/schemas/avatar.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/schemas/avatar.py) defines a validated state machine (`AvatarEmotion`, `AvatarGesture`, `AvatarState`, `AvatarGaze`) synchronized with conversation phases (`LISTENING`, `THINKING`, `SPEAKING`).

### 4. Implementation Files & Classes
- **Voice Services:** [`app/services/voice/`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/voice) (`runtime.py`, `stt_openai.py`, `tts_openai.py`, `segmentation.py`, `factory.py`, `mock_providers.py`)
- **Endpoints:** [`app/api/v1/voice.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/api/v1/voice.py)
- **Schemas:** [`app/schemas/avatar.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/schemas/avatar.py)

### 5. Data Flow
`Browser Audio Stream` ➔ `WebSocket /api/v1/voice/ws/{session_id}` ➔ `AudioSegmenter` ➔ `STTProvider.transcribe` ➔ `ConversationEngine.process_message` ➔ `TTSProvider.synthesize` ➔ `Audio Chunks & Avatar State Events Streamed to Client`.

### 6. Test Coverage
- `tests/test_voice_service.py`, `tests/test_avatar_presentation.py`

### 7. End-to-End Status: ⚠️ **Voice Audio: Functional; Avatar: Visual State Machine (Not 3D Neural Video)**

### 8. Limitations & Risks
- Avatar is a client-side reactive SVG/Canvas animation controller, not a deep-learning photorealistic video generator (e.g. SadTalker or HeyGen).

---

## Phase 8 — Evaluation Framework & Benchmarking

### 1. What It Does
Executes automated, reproducible evaluation suites against golden datasets to quantitatively benchmark RAG retrieval performance and answer quality.

### 2. Why Avtaar Needs It
Guarantees that prompt modifications, chunking strategy updates, or embedding changes do not cause silent regressions in RAG accuracy.

### 3. How It Is Implemented
- Standardized test suites evaluate:
  - **Retrieval Metrics:** Recall@K, Precision@K, Mean Reciprocal Rank (MRR), and NDCG@K.
  - **Answer Quality Metrics:** Faithfulness score (context grounding) and Answer Relevance.
  - **Negative Query Accuracy:** Verifying proper refusal when context is missing.
- Evaluation runs are persisted in the database (`app/models/evaluation.py:EvaluationRun`, `EvaluationItem`) with full baseline tracking and metric comparisons.

### 4. Implementation Files & Classes
- **Runner:** [`app/services/evaluation/runner.py:EvaluationRunner`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/evaluation/runner.py), [`backend/run_evaluation.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/run_evaluation.py)
- **Models:** [`app/models/evaluation.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/models/evaluation.py)
- **Endpoints:** [`app/api/v1/evaluations.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/api/v1/evaluations.py)
- **UI:** [`frontend/src/app/(dashboard)/evaluations/page.tsx`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/frontend/src/app/%28dashboard%29/evaluations/page.tsx)

### 5. Data Flow
`Golden QA Dataset` ➔ `EvaluationRunner` ➔ `Retrieval & Generation` ➔ `Score Calculation (MRR, Recall, Faithfulness)` ➔ `Persist EvaluationRun` ➔ `Dashboard Visual Trend Display`.

### 6. Test Coverage
- `tests/test_evaluation_framework.py`, `tests/test_evaluation_metrics.py`

### 7. End-to-End Status: ✅ **Fully Functional & Verified**

### 8. Limitations & Risks
- LLM-as-a-judge evaluation calls incur API token costs; local heuristic evaluation fallback is provided for fast unit testing.

---

## Phase 9 — Hybrid Retrieval & Reranking Pipeline

### 1. What It Does
Combines dense semantic vector search with sparse lexical keyword search (BM25) and applies Reciprocal Rank Fusion (RRF) and Cross-Encoder neural reranking.

### 2. Why Avtaar Needs It
Pure vector search frequently misses exact part numbers, product SKUs, acronyms, and specific names. Pure keyword search misses semantic synonyms. Hybrid search provides optimal accuracy across both types of queries.

### 3. How It Is Implemented
- **Dense:** Vector search against Qdrant collection with `company_id` payload filter.
- **Sparse:** In-memory BM25 index built over tenant document chunks (`app/services/retrieval/sparse.py`, `bm25.py`).
- **Fusion:** `ReciprocalRankFusion.fuse` calculates RRF score $S_{\text{RRF}}(d) = \sum \frac{1}{k + r(d)}$ with default constant $k=60$.
- **Reranker:** `CrossEncoderReranker` (or `HeuristicReranker` fallback) scores and sorts top-$K$ candidate chunks.

### 4. Implementation Files & Classes
- **Retrieval Engine:** [`app/services/retrieval/`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/retrieval) (`__init__.py:RetrievalService`, `dense.py`, `sparse.py`, `bm25.py`, `fusion.py`, `reranker.py`)

### 5. Data Flow
`User Query` ➔ Parallel (`DenseRetriever.search` + `SparseRetriever.search`) ➔ `ReciprocalRankFusion.fuse` ➔ `Reranker.rerank` ➔ `Top-K Chunks with Telemetry Timings`.

### 6. Test Coverage
- `tests/test_hybrid_retrieval.py`, `tests/test_bm25.py`, `tests/test_fusion.py`, `tests/test_reranker.py`

### 7. End-to-End Status: ✅ **Fully Functional & Verified**

### 8. Limitations & Risks
- In-memory BM25 cache requires invalidation when documents are added/deleted; handled by `global_bm25_cache.invalidate_tenant(company_id)`.

---

## Phase 10 — Async Ingestion & Distributed Rate Limiting

### 1. What It Does
Executes long-running document ingestion jobs asynchronously in the background and enforces multi-tier distributed rate limits across API endpoints.

### 2. Why Avtaar Needs It
Large PDF/DOCX ingestion blocks HTTP worker threads if processed synchronously. Public chat endpoints must be protected against brute-force DoS attacks.

### 3. How It Is Implemented
- `IngestionWorker` manages bounded concurrency (`asyncio.Semaphore`) with retry logic and database status updates (`PENDING` ➔ `PROCESSING` ➔ `COMPLETED` / `FAILED`).
- `RateLimiter` uses Redis Lua sliding token bucket scripts (`app/services/rate_limit/`).
- Fallback: If Redis is unreachable, degrades gracefully to per-instance in-memory rate limiting.

### 4. Implementation Files & Classes
- **Worker:** [`app/workers/ingestion_worker.py:IngestionWorker`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/workers/ingestion_worker.py)
- **Rate Limiting:** [`app/services/rate_limit/`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/rate_limit) (`limiter.py`, `redis_client.py`, `memory_fallback.py`)
- **Models:** [`app/models/ingestion_job.py:IngestionJob`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/models/ingestion_job.py)

### 5. Data Flow
`Upload Endpoint` ➔ `Create IngestionJob (PENDING)` ➔ `Background IngestionWorker.enqueue` ➔ `Process Chunking/Embeddings` ➔ `Job COMPLETED`.

### 6. Test Coverage
- `tests/test_async_ingestion.py`, `tests/test_rate_limiter.py`, `tests/test_watchdog.py`

### 7. End-to-End Status: ✅ **Fully Functional & Verified**

### 8. Limitations & Risks
- In-memory rate limiting fallback is per-instance, not globally synchronized across multiple servers without Redis.

---

## Phase 11 — Observability & Audit Trail

### 1. What It Does
Provides end-to-end distributed tracing, structured request logging with timing headers, tamper-evident audit logging for tool executions, and automated PII/credential redaction.

### 2. Why Avtaar Needs It
Enterprise compliance requires complete visibility into AI decisions, execution latencies, and security events without leaking sensitive keys in logs.

### 3. How It Is Implemented
- `StructuredLoggingMiddleware` assigns every request an `X-Request-ID` and logs structured JSON with latency measurements (`X-Process-Time-Ms`).
- `ObservabilityTracer` creates OpenTelemetry-compliant spans for RAG retrieval, LLM calls, and tool actions.
- `app/services/observability/redactor.py` scrubs API keys, auth tokens, passwords, and emails before writing to logs or DB.
- `AuditService` records all user actions and tool mutations.

### 4. Implementation Files & Classes
- **Tracing & Redaction:** [`app/services/observability/`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/observability) (`tracer.py`, `redactor.py`, `audit_service.py`, `metrics.py`)
- **Middleware:** [`app/middleware/logging.py:StructuredLoggingMiddleware`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/middleware/logging.py)
- **Endpoints:** [`app/api/v1/observability.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/api/v1/observability.py)
- **UI:** [`frontend/src/app/(dashboard)/observability/page.tsx`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/frontend/src/app/%28dashboard%29/observability/page.tsx)

### 5. Data Flow
`Incoming HTTP Request` ➔ `Assign X-Request-ID` ➔ `OpenTelemetry Span Creation` ➔ `Redactor Filter` ➔ `Structured JSON Log & DB Span Persistence`.

### 6. Test Coverage
- `tests/test_observability.py`, `tests/test_redactor.py`, `tests/test_audit_service.py`

### 7. End-to-End Status: ✅ **Fully Functional & Verified**

### 8. Limitations & Risks
- Jaeger / OTLP gRPC collector exporter is configured via OpenTelemetry standard env vars; defaults to in-memory/DB trace storage when external collector is absent.

---

## Phase 12 — AI Playground & Prompt Debugger

### 1. What It Does
Provides an interactive sandbox environment for developers and administrators to test prompt configurations, inspect raw retrieved chunks, tune retrieval modes (Dense/Sparse/Hybrid), and debug AI Employee outputs with live execution trace telemetry.

### 2. Why Avtaar Needs It
Developers and AI engineers need rapid prototyping tools to iterate on prompts and inspect context ranking without having to trigger public chat widgets.

### 3. How It Is Implemented
- Backend endpoint `/api/v1/playground/run` executes a one-off run returning full debug payloads: assembled prompt, system instructions, raw chunk scores, token usage, and step timings.
- Supports configuration snapshotting and comparison.

### 4. Implementation Files & Classes
- **Service:** [`app/services/playground/playground_service.py:PlaygroundService`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/playground/playground_service.py)
- **Models:** [`app/models/playground.py:PlaygroundSession`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/models/playground.py)
- **Endpoints:** [`app/api/v1/playground.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/api/v1/playground.py)
- **UI:** [`frontend/src/app/(dashboard)/playground/page.tsx`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/frontend/src/app/%28dashboard%29/playground/page.tsx)

### 5. Data Flow
`Developer tweaks Prompt & Mode in UI` ➔ `POST /api/v1/playground/run` ➔ `PlaygroundService` ➔ `Returns Full Telemetry & Retrieved Chunks` ➔ `UI Renders Side-by-Side Prompt/Context Inspector`.

### 6. Test Coverage
- `tests/test_playground.py`

### 7. End-to-End Status: ✅ **Fully Functional & Verified**

### 8. Limitations & Risks
- Playground executions count toward company token usage ledgers; configured to track playground usage separately.

---

## Phase 13 — Usage & Cost Governance

### 1. What It Does
Tracks token consumption across all models, computes exact dollar costs using a dynamic pricing registry, manages monthly company and employee budgets, and enforces soft warning thresholds (80%) and hard blocking limits (100%).

### 2. Why Avtaar Needs It
Protects companies from runaway LLM API expenses, malicious token drain attacks, and unexpected billing spikes.

### 3. How It Is Implemented
- `PricingRegistry` maintains exact per-million token pricing for Gemini, OpenAI, and custom models.
- `BudgetService` enforces atomic budget checks before LLM execution:
  - If usage $\ge 100\%$, raises `BudgetExceededException` ($429\text{ HTTP}$).
  - If usage $\ge 80\%$, flags warning status.
- Every LLM response usage metadata is persisted into a granular `UsageRecord` ledger.

### 4. Implementation Files & Classes
- **Services:** [`app/services/billing/budget_service.py:BudgetService`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/billing/budget_service.py), [`app/services/billing/pricing_registry.py:PricingRegistry`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/services/billing/pricing_registry.py)
- **Models:** [`app/models/usage_budget.py:UsageBudget, UsageRecord`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/models/usage_budget.py)
- **Endpoints:** [`app/api/v1/usage.py`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/backend/app/api/v1/usage.py)
- **UI:** [`frontend/src/app/(dashboard)/usage/page.tsx`](file:///d:/c%20drive/OneDrive/Desktop/Avtaar/frontend/src/app/%28dashboard%29/usage/page.tsx)

### 5. Data Flow
`Before LLM Call` ➔ `BudgetService.check_budget(company_id)` ➔ If ok: `LLM Call` ➔ `Record Token Usage & Compute Cost` ➔ `Persist UsageRecord` ➔ `Update Aggregate Monthly Spend`.

### 6. Test Coverage
- `tests/test_budget_service.py`, `tests/test_usage_metering.py`, `tests/test_pricing_registry.py`

### 7. End-to-End Status: ✅ **Fully Functional & Verified**

### 8. Limitations & Risks
- Automated credit card processing / payment gateway webhook integration (e.g. Stripe Customer Portal) is not yet wired to auto-refill credits.
