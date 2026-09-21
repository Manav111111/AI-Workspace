# AI Employee Platform (Phases 0-7 Complete)

An enterprise-ready, multi-tenant SaaS platform that enables companies to create, train, and deploy autonomous, company-specific AI employees.

---

## 1. Product Vision & Roadmap

The long-term vision of this platform is to provide an end-to-end operational AI workforce:
1. **Company Onboarding (Phase 0 - Complete)**: A company signs up, creates its isolated workspace, and invites team members.
2. **Knowledge Ingestion (Phase 1 - Complete)**: The company uploads documents (PDF, DOCX, Markdown, TXT, CSV), automatically parsed, cleaned, chunked, embedded, and indexed into isolated vector search (Qdrant).
3. **Conversations & Grounded RAG Chat (Phase 2 - Complete)**: Decoupled conversational brain, prompt injection defenses, grounded answering with citations, conversation persistence, and interactive testing console.
4. **Autonomous Agent Capabilities & Tool Lifecycle (Phase 3 - Complete)**: Action boundaries, scoped product search, order lookup, and write-tool human-in-the-loop confirmation lifecycles.
5. **Public AI Employee Website Widget Runtime (Phase 4 - Complete)**: Standalone embeddable `widget.js` (Shadow DOM isolated, zero React runtime required on host site), anonymous session security, bearer token auth, rate limiting, domain restriction integration boundaries, and dashboard embed customizer.
6. **Real-Time Voice AI (Phase 5 - Complete)**: Low-latency bidirectional speech-to-text (STT) and text-to-speech (TTS) streaming via WebSocket, barge-in / interruption support, dual-mode STT abstraction, smart sentence segmentation, voice widget interface, and telemetry/billing tracking reusing the identical conversational AI brain.
7. **Digital Human & 3D Avatar (Phase 6 - Complete)**: Embodied conversational avatar consuming the unified AI Employee Brain, Text Chat, and Voice AI runtime.
8. **Advanced Digital Human Behavior & Intelligent Avatar Orchestration (Phase 7 - Complete)**: Production-grade behavioral engine featuring controlled presentation emotions, conversational gaze dynamics, capability-aware gestures, natural non-deterministic blinking, head kinematics, animation priority scheduling, coarticulation-smoothed lip sync, Protocol v2 event validation, and graceful renderer failure fallback.


---

## 2. Tech Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0 (Async), Alembic, Pydantic v2, PyJWT, Bcrypt, HTTPX.
- **Conversational Brain & LLM**: Decoupled `LLMProvider` abstraction (OpenAI, Ollama, vLLM, DeepSeek, LocalAI), `ConversationEngine`, `ContextBuilder`, `PromptBuilder` with prompt injection defense.
- **Document Ingestion & Parsing**: PyMuPDF (fitz), python-docx, CSV parser, Markdown & Text normalizer.
- **Embeddings & Vector Store**: CPU-friendly 384-d dense embeddings (fastembed / sentence-transformers), Qdrant vector database with mandatory `company_id` tenant filter.
- **Frontend**: Next.js 14+ (App Router), React 18, TypeScript, Tailwind CSS, Lucide Icons.
- **Database**: PostgreSQL 16 (with asyncpg & psycopg2 drivers).
- **Caching & Future Queue**: Redis 7.
- **Infrastructure**: Docker & Docker Compose.
- **Testing**: Pytest & pytest-asyncio with HTTPX test client (22 automated test suites).

---

## 3. Repository Structure

```text
/
├── .env.example               # Template environment configuration
├── .gitignore                 # Git ignore rules for Python, Node, Docker
├── docker-compose.yml         # Local orchestration for Postgres, Redis, App
├── README.md                  # Project overview & documentation
├── /docs
│   └── architecture.md        # In-depth architectural specification & future roadmaps
├── /infra
│   ├── /docker
│   │   ├── backend.Dockerfile # Python 3.12 backend container
│   │   └── frontend.Dockerfile# Node 20 frontend container
│   └── /postgres
│       └── init.sql           # Database initialization script
├── /backend
│   ├── pyproject.toml / requirements.txt
│   ├── alembic.ini            # Alembic migration configuration
│   ├── pytest.ini             # Pytest test configuration
│   ├── alembic/               # Database migrations directory
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_tables.py
│   ├── app/
│   │   ├── main.py            # Application entrypoint & health checks
│   │   ├── api/               # API routers & dependency injection
│   │   │   ├── deps.py        # TenantContext and authentication dependencies
│   │   │   └── v1/            # Versioned API routes (auth, companies, ai-employees)
│   │   ├── core/              # Config, exceptions, logging, security
│   │   ├── db/                # Database engines & session lifecycle
│   │   ├── models/            # SQLAlchemy 2.0 declarative models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── repositories/      # Tenant-scoped data access layer
│   │   ├── services/          # Business logic layer
│   │   ├── middleware/        # Logging & standardized error handling
│   │   ├── workers/           # Placeholder for future Celery/Redis tasks
│   │   └── integrations/      # Placeholder for future third-party integrations
│   └── tests/                 # Automated test suite (health, auth, tenant isolation)
└── /frontend
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.ts
    └── src/
        ├── app/               # Next.js App Router pages
        ├── components/        # Reusable UI & layout components
        ├── lib/               # Typed API client with tenant headers
        └── types/             # TypeScript definitions
```

---

## 4. Multi-Tenancy & Security Model

Tenant isolation is enforced as a **hard security boundary**:

1. **Authentication**: Users receive a JWT access token containing their user ID (`sub`).
2. **Membership Check**: The `get_tenant_context` dependency resolves the user's active company membership. If an unverified `X-Company-ID` or foreign company ID is sent, the request is rejected with `403 Forbidden` or `404 Not Found`.
3. **Repository Scoping**: Every database query on company-owned resources explicitly filters by `company_id`.
4. **Roles**: Supports `OWNER`, `ADMIN`, and `MEMBER` roles with dependency factories (`require_roles`).

---

## 5. Getting Started Locally

### Prerequisites
- Python 3.12+
- Node.js 18+ & npm
- Docker and Docker Compose

### Option A: Running via Docker Compose (Recommended)
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Build and launch all services
docker-compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API Docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Readiness check: `http://localhost:8000/ready`

---

### Option B: Running Manually on Host

#### 1. Start PostgreSQL & Redis
```bash
docker-compose up -d postgres redis
```

#### 2. Backend Setup
```bash
cd backend
python -m venv .venv

# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 6. Running Automated Tests

To execute the backend test suite (including the mandatory tenant isolation tests across PostgreSQL & Qdrant):
```bash
cd backend
.\.venv\Scripts\pytest -v
```

### Verified Test Suites (54/54 Passing)
- `test_health.py`: Liveness (`/health`) and readiness (`/ready`) probes.
- `test_auth.py`: Registration, login, JWT issuance, bcrypt hashing verification, `/me` profile.
- `test_companies.py`: Company workspace creation, creator assigned as `OWNER`, inviting members.
- `test_ai_employees.py`: Full CRUD lifecycle for AI Employees within a tenant workspace.
- `test_tenant_isolation.py`: Cross-tenant access isolation, URL manipulation, and header spoofing defense.
- `test_knowledge_bases.py`: Knowledge base creation, listing, detail, update, deletion scoped by tenant.
- `test_documents.py`: Document registration, metadata tracking, status updates, and soft deletion.
- `test_document_ingestion.py`: End-to-end ingestion pipeline (parsing, cleaning, chunking, embedding, vector indexing, re-ingestion idempotency).
- `test_embeddings.py`: Deterministic 384-d vector generation, unit normalization, and fallback.
- `test_qdrant.py`: Qdrant collection initialization, vector upsert, payload filtering, and deletion.
- `test_knowledge_tenant_isolation.py`: Cross-tenant isolation verification across document storage, relational chunks, and Qdrant vector retrieval.
- `test_dimension_invariant.py`: Validation that embedding dimension matches Qdrant collection (384), failing fast on mismatch.
- `test_retrieval.py`: Retrieval service, score thresholding, top-k ranking, and source metadata preservation.
- `test_prompt_injection.py`: Resistance to document-embedded malicious prompt injections and system instruction extraction.
- `test_conversations.py`: Conversation CRUD, chronological message history ordering, and tenant scoping.
- `test_conversation_engine.py`: Grounded RAG conversation lifecycle, citation attribution, latency metrics, and fallback on unanswerable questions.
- `test_chat_tenant_isolation.py`: Cross-tenant security proving Company B cannot read Company A conversations, use Company A AI Employees, or retrieve Company A documents.
- `test_agent_orchestrator.py`: Multi-turn conversational planning and execution lifecycle.
- `test_tool_registry.py`: Dynamic tool registry, argument validation, and parameter sanitization.
- `test_tool_permissions.py`: Enforcing READ (automatic) vs WRITE (approval required) permission boundaries.
- `test_pending_tool_confirmation.py`: Server-managed pending action state transitions and expiry.
- `test_tool_execution.py`: Execution of permitted tools against business entities (orders, leads).
- `test_scoped_product_search.py`: Knowledge-base bounded semantic catalog search.
- `test_malicious_tool_arguments.py`: Sanitization and protection against tool parameter injection.
- `test_tool_tenant_isolation.py`: Strict isolation preventing cross-tenant tool execution or data tampering.
- `test_tool_idempotency.py`: Replay protection ensuring write actions execute exactly once.
- `test_public_employee.py`: Sanitized public config bootstrap (zero prompt/UUID leakage).
- `test_public_session.py`: Ephemeral bearer session generation and resumption.
- `test_public_chat.py`: Public website widget chat messaging and telemetry.
- `test_public_rate_limit.py`: IP-based session creation and message rate limiting.
- `test_public_domain_restrictions.py`: Origin/referer integration boundary enforcement.
- `test_public_tenant_isolation.py`: Cross-tenant security across public visitor sessions.
- `test_public_tool_security.py`: Human confirmation enforcement for public write tools.
- `test_public_e2e_flow.py`: Full end-to-end acceptance flow for Phase 4 website widget.

---

## 7. API Endpoints Overview

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness health check | No |
| `GET` | `/ready` | Readiness check (verifies database) | No |
| `POST` | `/api/v1/auth/signup` | Register user & optional company | No |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT | No |
| `GET` | `/api/v1/auth/me` | Current user profile & companies | Yes |
| `POST` | `/api/v1/companies/` | Create new company workspace | Yes |
| `GET` | `/api/v1/companies/` | List user's company memberships | Yes |
| `GET` | `/api/v1/companies/{id}`| Get company details | Yes (Member) |
| `POST` | `/api/v1/companies/{id}/members` | Add member to company | Yes (Owner/Admin) |
| `POST` | `/api/v1/ai-employees/` | Create AI Employee in active tenant | Yes (Owner/Admin) |
| `GET` | `/api/v1/ai-employees/` | List AI Employees in active tenant | Yes (Member) |
| `GET` | `/api/v1/ai-employees/{id}` | Get specific AI Employee | Yes (Tenant Scoped) |
| `PATCH`| `/api/v1/ai-employees/{id}` | Update AI Employee prompt/status | Yes (Owner/Admin) |
| `DELETE`| `/api/v1/ai-employees/{id}` | Delete AI Employee | Yes (Owner/Admin) |
| `POST` | `/api/v1/knowledge-bases/` | Create a company knowledge base | Yes (Owner/Admin) |
| `GET` | `/api/v1/knowledge-bases/` | List company knowledge bases | Yes (Member) |
| `GET` | `/api/v1/knowledge-bases/{id}` | Get specific knowledge base | Yes (Tenant Scoped) |
| `PATCH`| `/api/v1/knowledge-bases/{id}` | Update knowledge base metadata | Yes (Owner/Admin) |
| `DELETE`| `/api/v1/knowledge-bases/{id}` | Delete knowledge base and documents | Yes (Owner/Admin) |
| `POST` | `/api/v1/documents/upload` | Upload & ingest document directly | Yes (Owner/Admin) |
| `POST` | `/api/v1/knowledge-bases/{kb_id}/documents` | Upload document to specific KB | Yes (Owner/Admin) |
| `GET` | `/api/v1/documents/{id}` | Get document status & metadata | Yes (Tenant Scoped) |
| `GET` | `/api/v1/documents/{id}/chunks` | Inspect document chunks & metadata | Yes (Tenant Scoped) |
| `POST` | `/api/v1/documents/{id}/reprocess` | Re-trigger ingestion pipeline idempotently | Yes (Owner/Admin) |
| `DELETE`| `/api/v1/documents/{id}` | Delete document, chunks, and vectors | Yes (Owner/Admin) |
| `POST` | `/api/v1/conversations/` | Create new conversation with an AI Employee | Yes (Member) |
| `GET` | `/api/v1/conversations/` | List conversations in active tenant | Yes (Member) |
| `GET` | `/api/v1/conversations/{id}` | Get conversation details | Yes (Tenant Scoped) |
| `DELETE`| `/api/v1/conversations/{id}` | Delete conversation | Yes (Tenant Scoped) |
| `GET` | `/api/v1/conversations/{id}/messages` | Get chronological message history | Yes (Tenant Scoped) |
| `POST` | `/api/v1/conversations/{id}/messages` | Send message & get grounded RAG response + citations | Yes (Tenant Scoped) |
