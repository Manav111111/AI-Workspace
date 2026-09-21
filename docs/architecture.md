# Architecture Specification — AI Employee Platform

This document outlines the architectural foundation established in **Phase 0**, as well as the detailed technical blueprints for upcoming phases (**Phase 1: Ingestion & RAG**, **Phase 2: Agents & Tools**, **Phase 3: Real-Time Voice**, and **Phase 4: 3D Avatar Presentation**).

---

## 1. Phase 0 Architecture: Modular Monolith

The core platform is architected as a **Modular Monolith** using strict layer separation. This prevents spaghetti code and ensures that future AI, vector, and agent services can be incorporated cleanly without redesigning the core application.

```
┌───────────────────────────────────────────────────────────┐
│                    Next.js Frontend                       │
│           (React 18, TypeScript, Tailwind CSS)            │
└─────────────────────────────┬─────────────────────────────┘
                              │ HTTP / REST / JSON
                              ▼
┌───────────────────────────────────────────────────────────┐
│                     FastAPI Backend                       │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                    API Router                       │  │
│  │     (/api/v1/auth, /companies, /ai-employees)       │  │
│  └──────────────────────────┬──────────────────────────┘  │
│                             │                             │
│  ┌──────────────────────────▼──────────────────────────┐  │
│  │          Auth & Tenant Security Boundary            │  │
│  │  (JWT sub -> User -> Membership -> TenantContext)   │  │
│  └──────────────────────────┬──────────────────────────┘  │
│                             │                             │
│  ┌──────────────────────────▼──────────────────────────┐  │
│  │                    Service Layer                    │  │
│  │    (AuthService, CompanyService, AIEmployeeService) │  │
│  └──────────────────────────┬──────────────────────────┘  │
│                             │                             │
│  ┌──────────────────────────▼──────────────────────────┐  │
│  │                  Repository Layer                   │  │
│  │ (AIEmployeeRepo, CompanyRepo, UserRepo: company_id) │  │
│  └──────────────────────────┬──────────────────────────┘  │
└─────────────────────────────┼─────────────────────────────┘
                              │ Asyncpg / SQLAlchemy 2.0
                              ▼
┌───────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                     │
│    (users, companies, memberships, ai_employees)          │
└───────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

1. **API Router (`app/api/v1/`)**: Handles request routing, Pydantic schema validation, and status codes. Contains **no business logic** or direct database queries.
2. **Security & Tenant Boundary (`app/api/deps.py`)**: Intercepts requests, validates JWT claims (`sub`), resolves the active company from the authenticated user's memberships, and produces a strongly-typed `TenantContext`. Rejects unverified company IDs.
3. **Service Layer (`app/services/`)**: Implements business transactions, coordinate multiple repositories, enforces business invariants.
4. **Repository Layer (`app/repositories/`)**: Encapsulates SQLAlchemy 2.0 database queries. **Every tenant-owned entity repository method mandates `company_id`** in its query filters.
5. **Database Models (`app/models/`)**: Declarative SQLAlchemy models with UUIDv4 primary keys and UTC timezone-aware timestamps.

---

## 2. Multi-Tenancy & Security Isolation Model

Multi-tenancy is treated as a **strict security boundary** from Day 1.

### Tenant Hierarchy

```
User (Global Account)
  └── Membership (Role: OWNER | ADMIN | MEMBER)
        └── Company (Tenant Boundary)
              ├── AIEmployee(s)
              ├── [Future] Document(s) & Chunk(s)
              ├── [Future] Vector Collection (company_id payload filter)
              ├── [Future] Conversation(s) & Message(s)
              └── [Future] Widget & Integration Config
```

### The Golden Rule of Tenant Isolation
> **Never trust a `company_id` supplied blindly by the frontend.**

1. An incoming request provides a Bearer token in the `Authorization` header.
2. The `get_tenant_context` dependency validates the token signature and extracts `user_id`.
3. If the request provides an `X-Company-ID` header or `{company_id}` URL parameter, the backend verifies that a `Membership` record exists in the database linking that `user_id` to that `company_id`.
4. If the user does not belong to that company, the request is immediately aborted with `403 Forbidden` or `404 Not Found`.
5. Every database query executed on behalf of that request must include `.where(Model.company_id == tenant.company_id)`.

---

## 3. Database Schema

### Core Tables

| Table | Primary Key | Key Columns | Relationships / Constraints |
| :--- | :--- | :--- | :--- |
| `users` | `id` (UUID) | `email`, `hashed_password`, `full_name`, `is_active`, `is_superuser` | Unique index on `email` |
| `companies` | `id` (UUID) | `name`, `slug`, `is_active` | Unique index on `slug` |
| `memberships` | `id` (UUID) | `user_id`, `company_id`, `role` (`OWNER`, `ADMIN`, `MEMBER`) | Unique constraint `(user_id, company_id)`. Foreign keys cascade delete. |
| `ai_employees` | `id` (UUID) | `company_id`, `name`, `role`, `description`, `personality`, `system_prompt`, `language`, `status`, `avatar_config`, `voice_config` | Foreign key to `companies.id` (cascade). Indexed by `company_id`. |

### Extensible AI Employee Model
The `ai_employees` table includes structured `avatar_config` and `voice_config` JSON fields. This allows future phases to configure 3D models, textures, animations, voice IDs, and speech rates without altering the underlying database schema.

---

## 4. Phase 1 Architecture: Knowledge Base, Document Ingestion & Vector Pipeline (Implemented)

In Phase 1, the platform enables multi-tenant document upload, storage, parsing, normalization, semantic chunking, embedding generation, and isolated vector indexing in Qdrant.

```
Incoming Document (PDF, DOCX, MD, TXT, CSV)
                  │
                  ▼
         Storage Abstraction (LocalStorageService / S3-ready)
                  │
                  ▼
         Document Parser Registry
         (PyMuPDF, python-docx, Markdown, Plaintext, CSV)
                  │
                  ▼
         Text Cleaner & Normalizer
         (Unicode, whitespace, control characters, null bytes)
                  │
                  ▼
         Semantic Chunking Service
         (Configurable chunk_size=500, overlap=50 tokens, boundary-aware)
                  │
                  ▼
         Relational Chunk Storage (PostgreSQL: document_chunks)
                  │
                  ▼
         CPU-Friendly Embedding Engine
         (384-d normalized dense embeddings, fastembed/sentence-transformers)
                  │
                  ▼
         Qdrant Vector Database
         (Payload Filter: company_id, document_id, chunk_id)
```

### Ingestion Components & Design Patterns

1. **Storage Abstraction (`app/services/storage.py`)**:
   - `StorageService` interface with `LocalStorageService` implementation.
   - Enforces company isolation via path partitioning: `storage/{company_id}/{document_id}/{filename}`.
   - Path traversal defenses prevent directory escape attacks.

2. **Parser Registry (`app/services/parsers/`)**:
   - Extensible `BaseParser` interface.
   - `PDFParser`: PyMuPDF (`fitz`) page-by-page extraction with metadata.
   - `DOCXParser`: `python-docx` structured paragraph & table text extraction.
   - `MarkdownParser`: Clean markdown extraction with header preservation.
   - `TXTParser`: Multi-encoding fallback (UTF-8, Latin-1, CP1252).
   - `CSVParser`: Converts tabular data into semantic key-value records (`Col: Val | Col: Val`) with row indices.

3. **Cleaning & Chunking (`app/services/cleaning.py`, `app/services/chunking.py`)**:
   - Cleans formatting artifacts, replaces null bytes, collapses redundant whitespace.
   - Recursive character chunking respecting paragraph (`\n\n`), sentence (`. `), and word (` `) boundaries.

4. **CPU-Friendly Embeddings (`app/services/embeddings.py`)**:
   - Generates 384-dimensional dense vectors using lightweight, CPU-optimized models (`BAAI/bge-small-en-v1.5` / `all-MiniLM-L6-v2`).
   - Deterministic unit-length normalization enables exact cosine distance computation via dot product.
   - Operates on standard developer laptops without GPU requirements.

5. **Multi-Tenant Vector Partitioning in Qdrant (`app/services/qdrant_service.py`)**:
   - Every vector point payload contains: `company_id`, `knowledge_base_id`, `document_id`, `chunk_id`, `chunk_index`, and `text`.
   - Hard tenant filtering is enforced at the query level. Even in a shared collection, vectors from Company A are mathematically unreachable by Company B:
     ```json
     {
       "filter": {
         "must": [
           { "key": "company_id", "match": { "value": "<active_company_id>" } }
         ]
       }
     }
     ```

6. **Idempotent Ingestion Orchestration (`app/services/ingestion.py`)**:
   - Atomic re-processing: deletes prior chunks from PostgreSQL and prior vector points from Qdrant before ingesting updated documents.
   - Transitions document status: `UPLOADED` → `PROCESSING` → `PROCESSED` (or `FAILED` with stored error message).

---

## 5. Phase 2 Architecture: Grounded Conversational Brain & RAG Chat Engine (Implemented)

In Phase 2, the platform transforms the knowledge infrastructure into a real, grounded conversational AI Employee.

### Architectural Principle: Decoupled Conversational Brain
The conversational engine is strictly presentation-agnostic. It does not contain any avatar or voice-specific code, enabling direct re-use across text chat widgets, real-time voice streaming (Phase 3), and 3D avatars (Phase 4):

```
                         FRONTEND / CLIENT
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
          Company Dashboard               Chat Console
                 │                             │
                 └──────────────┬──────────────┘
                                │ (HTTP / REST / JSON)
                                ▼
                           FastAPI API
                                │
                          TenantContext (Verified X-Company-ID / sub)
                                │
                                ▼
                       Conversation Engine
                                │
      ┌─────────────────────────┼─────────────────────────┐
      ↓                         ↓                         ↓
Conversation               Retrieval                 AI Employee
  Memory                    Service                    Config
(PostgreSQL)                   │                    (Name, Role,
                               ▼                     Personality,
                           Embedding                 Prompt)
                           (384-d)
                               │
                               ▼
                            Qdrant
                     (company_id filter)
                               │
                               ▼
                    Bounded Context Builder
                               │
                               ▼
                     Prompt Builder Engine
               (Prompt Injection Defenses &
                  Zero-Retrieval Notice)
                               │
                               ▼
                    LLM Provider Abstraction
                 (OpenAI / Compatible / Mock)
                               │
                               ▼
                       Grounded Response
                               │
                               ▼
                      Citations & Metrics
                               │
                               ▼
                       Frontend Chat UI
```

### Key Components & Design Patterns

1. **Decoupled LLM Provider Abstraction (`app/services/llm/`)**:
   - `LLMProvider` (ABC) defining `generate(messages, temperature, max_tokens) -> LLMResponse` and future-ready `generate_stream(...)`.
   - `OpenAIProvider`: Implements client-side timeout (`LLM_TIMEOUT_SECONDS`) and a controlled 1-attempt retry for transient network/server errors (5xx/timeouts), while **never retrying authentication (401/403) or validation (422) errors**. Compatible with Ollama, vLLM, and local OpenAI-compatible endpoints.
   - `MockLLMProvider`: Deterministic offline provider for automated testing, local development, and prompt-injection defense validation without external API keys.

2. **Tenant-Scoped Retrieval Service (`app/services/retrieval.py`)**:
   - Mandates `company_id` on every query.
   - Encodes user query into 384-d normalized vector.
   - Searches Qdrant with hard tenant filter (`company_id == tenant.company_id`).
   - Applies score thresholding and pluggable `Reranker` interface (`NoOpReranker`).
   - Captures retrieval metadata (`retrieval_query`, `chunks_retrieved`, `top_score`, `retrieval_latency_ms`).

3. **Safe Context & Prompt Builder (`app/services/context_builder.py`, `app/services/prompt_builder.py`)**:
   - `ContextBuilder`: Formats retrieved chunks into structured reference blocks with source document names, page numbers, and section headers while capping to `RAG_MAX_CONTEXT_CHUNKS`.
   - `PromptBuilder`:
     - Combines AI Employee identity, company custom instructions, conversation history, and user query.
     - **Prompt Injection Defense**: Explicitly instructs the LLM that retrieved company documents are untrusted reference material, forbidding the execution of embedded instructions or overrides.
     - **Zero-Retrieval Policy**: If Qdrant returns zero chunks above threshold, injects an explicit zero-retrieval notice, requiring the assistant to inform the user that information is unavailable and preventing hallucination.

4. **Conversation Engine & Persistence (`app/services/conversation_engine.py`)**:
   - **Persist User Message First**: User messages are committed to PostgreSQL *before* contacting the LLM, ensuring queries are never lost on LLM timeouts or network faults.
   - Saves Assistant response with citation references (`chunk_id`, `document_id`, `document_name`, `page_number`, `score`, `preview`).
   - Records retrieval and LLM latency metrics in `message_metadata` for full RAG observability.

5. **Embedding & Qdrant Dimension Invariant (`app/services/invariants.py`)**:
   - Enforces a fail-fast check at startup and readiness probes: `embedding_dimension == qdrant_collection_dimension (384)`. Mismatches immediately raise `RuntimeError` rather than silently padding or truncating vectors.

---

## 6. Future Voice Architecture (Phase 3)

Phase 3 introduces real-time voice streaming:

```
User Audio (WebRTC / WebSocket)
     │
     ▼
Speech-to-Text (STT Engine)
     │
     ▼
AI Employee Brain (LLM + Context + Tools)
     │
     ▼
Text Stream / Sentence Chunks
     │
     ▼
Text-to-Speech (TTS Engine)
     │
     ▼
Audio Stream & Viseme Alignment
     │
     ▼
Client Audio Playback
```

---

## 7. Future Avatar Architecture: Decoupled Presentation Layer (Phase 4)

The 3D avatar is strictly a **presentation and interface layer**. The avatar **MUST NOT** be tightly coupled to the RAG or core SaaS backend.

```
AI Employee Brain (LLM + Voice Stream)
                   │
                   ▼
     Emotion & Gesture Decision Model
       (Joy, Neutral, Empathy, Thinking)
                   │
                   ▼
       Phoneme & Viseme Extraction
       (Lip-sync timestamp generation)
                   │
                   ▼
     3D Avatar Presentation Layer
    (Three.js / WebGL / Unreal Pixel Stream)
  - Facial Blendshapes
  - Lip Sync Timing
  - Gaze & Blinking
  - Natural Idles & Gestures
```

---

## 8. Decoupled GPU Inference Architecture

### Design Principle: The Web App is CPU-Friendly
The core SaaS application backend (FastAPI + PostgreSQL + Next.js) must **NEVER** require a local GPU to run.

1. **Decoupled Inference Interface**: The backend communicates with model endpoints over standard network protocols (HTTP/gRPC/WebSocket).
2. **Independent GPU Model Services**: Heavy GPU workloads (e.g., local LLM fine-tuning, voice synthesis models, or 3D neural rendering) operate as separate services hosted on dedicated GPU infrastructure or external GPU providers (e.g., RunPod, AWS EC2 G5, external GPU clusters, or external experimentation environments like Kaggle).
3. **CPU Machines for SaaS Development**: Developers can build, test, and deploy the entire SaaS platform, dashboard, multi-tenancy, and RAG logic on standard developer laptops without any GPU hardware requirements.

---

## 9. Phase 7: Advanced Digital Human Behavior & Avatar Orchestration

Phase 7 introduces the production-grade **Digital Human Behavior Engine**, elevating the 3D presentation layer into an intelligent, embodied conversational interface while strictly upholding the core architectural invariant: **The AI Employee Brain remains the single source of truth; the Avatar is strictly a presentation consumer.**

```
                  AI EMPLOYEE BRAIN (Server-side)
                               │
                               ▼
                      CONVERSATION ENGINE
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
      TEXT CHAT                              VOICE RUNTIME
                                                  │
                                                  ▼
                                      AVATAR EVENT PROTOCOL (v2)
                                      - protocol_version: 2
                                      - sequence & generation_id
                                      - speech_start / speech_end
                                      - emotion / gesture / gaze
                                                  │
                                                  ▼
                                    AVATAR BEHAVIOR ENGINE (Client)
                                    ┌────────────────────────────┐
                                    │ Capability Detection       │
                                    │ Emotion Controller         │
                                    │ Gaze & Micro-Saccades      │
                                    │ Natural Double-Blinks      │
                                    │ Head Kinematics            │
                                    │ Priority Scheduler         │
                                    │ Coarticulated Lip Sync     │
                                    └─────────────┬──────────────┘
                                                  │
                                                  ▼
                                          THREE.JS / WEBGL
                                                  │
                                    (Fallback: Honest Fallback UI)
```

### Key Components

1. **Protocol v2 Specification**:
   - Backward-compatible versioning with `protocol_version: 2` header.
   - Strict generation ID tracking (`generation_id`) to discard late packets from superseded turns.
   - Monotonically increasing sequence ordering (`sequence`).
   - Turn-taking markers (`speech_start`, `speech_end`) for smooth mouth return to neutral.

2. **Presentation Metadata Validation**:
   - Strongly typed Pydantic models in `app.schemas.avatar.PresentationMetadata`.
   - Clamps intensity ($0.0 \le \text{intensity} \le 1.0$) and bounds duration ($100\text{ms} \le \text{duration} \le 10000\text{ms}$).
   - Sanitizes and rejects dangerous script injections (`<script>`, `javascript:`, `eval()`).
   - Unrecognized emotions or corrupt payloads fall back safely to `neutral` without interrupting chat.

3. **Behavioral Subsystems**:
   - **Emotion Controller**: Controlled presentation emotions (`happy`, `friendly`, `confident`, `curious`, `thinking`, `concerned`, `excited`, `apologetic`, `serious`).
   - **Gaze Dynamics**: Direct attentive eye contact, thinking glance-away, micro-saccades, and smooth LERP interpolation.
   - **Blinking**: Variable intervals (2.5-5.5s), realistic double-blinks (15% probability), and closed-eye failsafe.
   - **Kinematics**: Attentive listening nods, thinking head tilts, and subtle speech rhythm resonance.
   - **Gestures**: Capability-aware (falls back safely from hand gestures to head nods if skeletal hands are absent).

4. **Priority Scheduler**:
   - Strict priority ordering: `INTERRUPTED (100) > SAFETY (90) > SPEECH (80) > EMOTION (60) > GESTURE (50) > HEAD (40) > IDLE (10)`.
   - Interruption immediately halts speech, cancels gestures, and resets mouth to `viseme_sil`.

5. **Renderer Failure & Telemetry**:
   - If WebGL hardware acceleration is unavailable, the engine does NOT fake 3D with 2D rendering.
   - Activates an honest fallback card while keeping Text Chat and Voice AI 100% operational.
   - Emits telemetry error callback for observability.
