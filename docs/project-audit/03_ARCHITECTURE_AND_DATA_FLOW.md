# 03 — Architecture and Data Flow

## 1. System Architecture Overview

**Avtaar** is structured around a decoupled, service-oriented architecture comprising four primary layers:
1. **Client / Presentation Layer:** Next.js 14 App Router dashboard, Embeddable Vanilla JS Widget (`widget.js`), and WebSocket Voice/Avatar client.
2. **API & Security Gateway Layer:** FastAPI application running on Uvicorn with structured JSON logging, token-based rate limiting, JWT authentication, and tenant context resolution.
3. **Core AI Engine & Execution Layer:** `ConversationEngine`, `AgentOrchestrator`, `ToolExecutor`, `PromptBuilder`, and `BudgetService`.
4. **Data & Storage Persistence Layer:** PostgreSQL / SQLite (via Async SQLAlchemy ORM), Qdrant Vector Database, and Redis Distributed Cache.

---

## 2. Platform Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        A1["Next.js 14 Web App<br/>(Admin & Dev Dashboard)"]
        A2["Embeddable JavaScript Widget<br/>(public/widget.js)"]
        A3["Real-Time Voice Client<br/>(WebSocket Audio)"]
    end

    subgraph "API Gateway & Middleware"
        B1["FastAPI Application (Uvicorn)"]
        B2["StructuredLoggingMiddleware<br/>(X-Request-ID, Latency)"]
        B3["RateLimiterMiddleware<br/>(Redis Token Bucket / In-Memory)"]
        B4["Auth & TenantContext Resolver<br/>(JWT HS256 / Bearer)"]
    end

    subgraph "Core AI Services"
        C1["ConversationEngine<br/>(Orchestration Hub)"]
        C2["AgentOrchestrator<br/>(Bounded ReAct Loop)"]
        C3["ToolExecutor<br/>(Permission & Confirmation Safeguards)"]
        C4["PromptBuilder<br/>(Injection-Resistant XML Formatting)"]
        C5["BudgetService<br/>(Cost Ledger & Soft/Hard Limits)"]
    end

    subgraph "Hybrid RAG Pipeline"
        D1["RetrievalService<br/>(Multi-Tenant Dispatcher)"]
        D2["DenseRetriever<br/>(Qdrant Semantic Vectors)"]
        D3["SparseRetriever<br/>(BM25 Lexical Index)"]
        D4["ReciprocalRankFusion (k=60)"]
        D5["Reranker<br/>(CrossEncoder / Heuristic)"]
    end

    subgraph "Ingestion Subsystem"
        E1["IngestionWorker<br/>(Async Bounded Semaphore)"]
        E2["Multi-Format Document Parsers<br/>(PDF, DOCX, CSV, MD, TXT)"]
        E3["ChunkingService<br/>(Semantic Recursive Overlap)"]
        E4["EmbeddingService<br/>(Gemini 768d / CPU Fallback)"]
    end

    subgraph "Persistence & Infrastructure"
        F1[("PostgreSQL / SQLite<br/>23 Relational Tables")]
        F2[("Qdrant Vector Database<br/>Cosine Distance Index")]
        F3[("Redis Cache<br/>Rate Limiting & BM25 State")]
        F4["Local / S3 Storage<br/>Raw Document Store"]
    end

    %% Client to Gateway
    A1 -->|"REST /api/v1/*"| B1
    A2 -->|"REST /api/v1/public/*"| B1
    A3 -->|"WS /api/v1/voice/ws/*"| B1

    %% Gateway Flow
    B1 --> B2 --> B3 --> B4

    %% Gateway to Services
    B4 -->|"Authenticated Context"| C1
    B1 -->|"Ingest API"| E1

    %% Ingestion Flow
    E1 --> E2 --> E3 --> E4
    E4 -->|"Upsert Vectors"| F2
    E1 -->|"Update IngestionJob"| F1

    %% Conversation & RAG Flow
    C1 --> C5
    C1 --> D1
    D1 --> D2 --> F2
    D1 --> D3 --> F3
    D1 --> D4 --> D5
    D5 -->|"Top-K Ranked Chunks"| C1

    %% Conversation to Agent & Tools
    C1 --> C4
    C1 --> C2
    C2 --> C3
    C3 -->|"Read/Write Business Data"| F1
    C3 -->|"Record Audit Trail"| F1
    C1 -->|"Save Messages & Traces"| F1
```

---

## 3. Detailed Component Interactions & Data Flows

### A. End-to-End Chat & RAG Retrieval Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Client / User
    participant GW as FastAPI Gateway
    participant CE as ConversationEngine
    participant BG as BudgetService
    participant RS as RetrievalService
    participant QD as Qdrant Vector DB
    participant BM as BM25 Sparse Index
    participant PB as PromptBuilder
    participant LLM as Gemini / OpenAI LLM
    participant DB as Relational DB

    User->>GW: POST /api/v1/conversations/{id}/messages (prompt)
    GW->>GW: Verify JWT & Resolve TenantContext (company_id)
    GW->>CE: process_message(prompt, company_id, employee_id)
    
    CE->>BG: check_budget(company_id)
    Note over BG: Verifies monthly spend < hard_limit

    CE->>RS: retrieve(query, company_id, mode="hybrid")
    par Parallel Vector & Lexical Search
        RS->>QD: Vector Similarity (filter: company_id)
        RS->>BM: Lexical BM25 Search (company_id chunks)
    end
    RS->>RS: Reciprocal Rank Fusion (RRF k=60)
    RS->>RS: Neural Rerank (CrossEncoder)
    RS-->>CE: Top-K Retrieved Chunks + Timings

    CE->>PB: build_messages(history, chunks, tools_schema)
    PB-->>CE: XML-Delimited Grounded Prompt

    CE->>LLM: generate(messages, tools)
    LLM-->>CE: LLMResponse (content / tool_calls, token_usage)

    CE->>BG: record_usage(company_id, tokens, cost)
    CE->>DB: Persist User & Assistant Messages
    CE-->>GW: Formatted Answer + Citations + Telemetry
    GW-->>User: HTTP 200 JSON Response
```

---

### B. Tool Execution & Human Confirmation Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant GW as FastAPI Gateway
    participant AO as AgentOrchestrator
    participant TE as ToolExecutor
    participant TR as ToolRegistry
    participant DB as Relational Database

    User->>GW: Send message requiring state change (e.g. "Create a support ticket for order #123")
    GW->>AO: Execute reasoning cycle
    AO->>TR: Inspect tool: create_support_ticket
    Note over TR: Tool Policy: REQUIRES_CONFIRMATION

    AO->>TE: execute_tool(create_support_ticket, args, bypass_confirmation=False)
    TE->>DB: Insert PendingToolAction (status=PENDING, validated_args)
    TE-->>AO: ToolResult(requires_confirmation=True, action_id=UUID)
    AO-->>GW: Return Confirmation Card Payload
    GW-->>User: Display interactive confirmation UI

    Note over User: User reviews parameters & clicks "Confirm"
    User->>GW: POST /api/v1/tools/confirm/{action_id}
    GW->>TE: execute_confirmed_action(action_id, company_id)
    TE->>TE: Verify tenant ownership & status == PENDING
    TE->>DB: Execute business write operation
    TE->>DB: Update PendingToolAction (status=CONFIRMED)
    TE->>DB: Insert immutable ToolExecution audit log
    TE-->>GW: ToolResult(success=True, result_data)
    GW-->>User: Display success confirmation
```

---

### C. Async Document Ingestion Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Admin / User
    participant API as Documents API
    participant DB as Relational DB
    participant IW as IngestionWorker (Async)
    participant PS as Document Parsers
    participant CS as ChunkingService
    participant ES as EmbeddingService
    participant INV as Invariant Validator
    participant QD as Qdrant Vector DB

    Admin->>API: POST /api/v1/documents/upload (PDF/DOCX/CSV)
    API->>API: Validate MIME type & file size (<25MB)
    API->>DB: Create Document (status=PENDING)
    API->>DB: Create IngestionJob (status=QUEUED)
    API->>IW: enqueue(document_id, company_id)
    API-->>Admin: HTTP 202 Accepted (job_id)

    Note over IW: Worker picks job from queue
    IW->>DB: Update Document (status=PROCESSING)
    IW->>PS: Parse raw file bytes to text
    PS-->>IW: Clean normalized text string
    IW->>CS: chunk_text(text, chunk_size=500, overlap=50)
    CS-->>IW: List of text chunks with position metadata
    
    IW->>ES: generate_embeddings(chunks)
    ES-->>IW: 768-dimensional float vectors
    
    IW->>INV: validate_vectors_before_insert(embeddings)
    Note over INV: Asserts vector dimension == Qdrant collection dimension
    
    IW->>QD: upsert_points(vectors + payload: company_id, doc_id)
    IW->>DB: Persist DocumentChunk records
    IW->>DB: Update Document & IngestionJob (status=COMPLETED)
```

---

## 4. Database Schema & Multi-Tenant Relational Model

The relational schema comprises **23 tables** managed by Alembic migrations:

```mermaid
erDiagram
    COMPANIES ||--o{ USERS : "has"
    COMPANIES ||--o{ MEMBERSHIPS : "scopes"
    USERS ||--o{ MEMBERSHIPS : "participates"
    COMPANIES ||--o{ AI_EMPLOYEES : "owns"
    COMPANIES ||--o{ KNOWLEDGE_BASES : "owns"
    KNOWLEDGE_BASES ||--o{ DOCUMENTS : "contains"
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : "split_into"
    DOCUMENTS ||--o{ INGESTION_JOBS : "tracks"
    AI_EMPLOYEES ||--o{ CONVERSATIONS : "engages"
    CONVERSATIONS ||--o{ MESSAGES : "contains"
    CONVERSATIONS ||--o{ PENDING_TOOL_ACTIONS : "triggers"
    AI_EMPLOYEES ||--o{ TOOL_EXECUTIONS : "logs"
    COMPANIES ||--o{ USAGE_BUDGETS : "governs"
    COMPANIES ||--o{ USAGE_RECORDS : "meters"
    COMPANIES ||--o{ EVALUATION_RUNS : "evaluates"
    EVALUATION_RUNS ||--o{ EVALUATION_ITEMS : "details"

    COMPANIES {
        uuid id PK
        string name
        string domain
        datetime created_at
    }

    AI_EMPLOYEES {
        uuid id PK
        uuid company_id FK
        string name
        string role
        text system_prompt
        string public_id UK
        boolean is_published
        json allowed_domains
    }

    DOCUMENTS {
        uuid id PK
        uuid company_id FK
        uuid knowledge_base_id FK
        string title
        string file_type
        string status
        int chunk_count
    }

    DOCUMENT_CHUNKS {
        uuid id PK
        uuid company_id FK
        uuid document_id FK
        text content
        int chunk_index
        json metadata
    }

    USAGE_BUDGETS {
        uuid id PK
        uuid company_id FK
        float monthly_budget_usd
        float soft_limit_percent
        float hard_limit_percent
        float current_spend_usd
    }
```

---

## 5. Architectural Quality Attributes & Design Principles

1. **Defense in Depth:** Tenant isolation is enforced at HTTP gateway, repository query construction, vector database filtering, and in-memory caching.
2. **Fail-Fast Invariants:** Incompatible vector dimensions, missing provider keys, or corrupt configurations raise immediate, clear runtime exceptions rather than silently degrading.
3. **Pluggable Architecture:** Embedding providers, LLM providers, storage backends, and rerankers implement strict abstract base classes (`EmbeddingProvider`, `LLMProvider`, `StorageService`, `Reranker`), allowing seamless swapping between Google Gemini, OpenAI, CPU mock engines, and cloud storage providers.
