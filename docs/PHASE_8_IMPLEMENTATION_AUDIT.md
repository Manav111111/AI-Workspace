# Phase 8 — RAG Evaluation & Benchmarking Implementation Audit

## 1. Executive Summary
This document records the architectural audit and implementation strategy conducted prior to building **Phase 8: RAG Evaluation & Benchmarking Engine** for the Avtaar AI Employee platform.

The core objective of Phase 8 is to transform Avtaar from an unmeasured RAG chatbot into a quantitatively evaluated, observable, and regression-tested enterprise AI platform without duplicating retrieval or generation logic.

---

## 2. Inspection of Existing Production Services (Phases 0–7)

### 2.1 Retrieval Pipeline & Qdrant Integration
- **`RetrievalService` (`backend/app/services/retrieval.py`)**:
  - Implements dense vector similarity search via `qdrant_service.search_chunks()`.
  - Enforces tenant isolation by embedding `company_id` filter into every Qdrant query filter.
  - Resolves knowledge base scoping by restricting search to `knowledge_base_ids` assigned to the AI Employee.
  - Returns a list of `RetrievedChunk` dataclass objects exposing:
    - `chunk_id` (`UUID`)
    - `document_id` (`UUID`)
    - `knowledge_base_id` (`UUID`)
    - `text` (`str`)
    - `score` (`float` cosine similarity score)
    - `source` / `page_number`
- **`EmbeddingService` (`backend/app/services/embedding.py`)**:
  - Routes embeddings to Google Gemini (`text-embedding-004` or `gemini-embedding-exp`) with fallback to local CPU MiniLM (`all-MiniLM-L6-v2`) or Mock.
- **`ConversationEngine` (`backend/app/services/conversation.py`)**:
  - Orchestrates:
    1. Employee lookup and assignment validation.
    2. Context retrieval via `RetrievalService`.
    3. Grounded prompt assembly via `PromptBuilder`.
    4. LLM generation with tool calling and citation formatting.

### 2.2 Scoping & Tenant Isolation
- **Tenant Context (`backend/app/api/deps.py`)**:
  - Resolves `TenantContext` containing `user`, `company`, and `membership`.
  - Guaranteed `company_id` verification prevents cross-tenant access.
- **Knowledge Base Scoping (`backend/app/models/ai_employee_knowledge_base.py`)**:
  - Join table `ai_employee_knowledge_bases` guarantees that an AI Employee can ONLY retrieve chunks from assigned KBs.

---

## 3. Non-Negotiable Architectural Invariant: Production Code Reuse

```
                    EXISTING AVTAAR PRODUCTION RAG
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
               User Chat                Evaluation Runner
                    │                           │
                    └─────────────┬─────────────┘
                                  ↓
                        SAME RetrievalService
                                  ↓
                        SAME ContextBuilder
                                  ↓
                        SAME PromptBuilder
                                  ↓
                        Quantitative Metrics
```

The evaluation runner **never builds a mock or parallel retrieval pipeline**. It instantiates and invokes the existing `RetrievalService`, passing the employee's assigned knowledge bases, capturing real latency, scores, and chunk UUIDs directly from Qdrant.

---

## 4. Components Implemented for Phase 8

| Component | File Path | Description |
| :--- | :--- | :--- |
| **Database Models** | `backend/app/models/evaluation.py` | `EvaluationRun` and `EvaluationResultItem` with full tenant scoping. |
| **Dataset Schema & Validator** | `backend/app/services/evaluation/dataset.py` | Pydantic schema for JSONL test cases (positive + negative) and validation. |
| **Pure IR Metrics** | `backend/app/services/evaluation/metrics.py` | Standalone math engine for Recall@1/3/5, Precision@1/3/5, MRR, and NDCG@K. |
| **NLG Generation Judge** | `backend/app/services/evaluation/judge.py` | LLM-as-a-judge for Faithfulness, token-overlap relevance, and structured refusal detection. |
| **Evaluation Runner** | `backend/app/services/evaluation/runner.py` | Async runner with bounded concurrency (`asyncio.Semaphore(3)`). |
| **Baseline & Regression Gate** | `backend/app/services/evaluation/baseline.py` | Baseline persistence in `backend/data/baseline.json` with 5% drop tolerance checks. |
| **REST APIs** | `backend/app/api/v1/evaluations.py` | Endpoints: `POST /run`, `GET /`, `GET /baseline`, `GET /{id}`, `GET /{id}/report`, `POST /{id}/set-baseline`. |
| **Golden HR Dataset** | `backend/data/golden_eval_dataset_hr.jsonl` | 20 curated queries (15 positive HR policy questions + 5 negative out-of-scope). |
| **Pytest Suite** | `backend/tests/test_rag_evaluation.py` | 12 automated unit/integration tests verifying math, schemas, runner, and regression gates. |
| **Frontend UI** | `frontend/src/app/(dashboard)/evaluations/page.tsx` | Dashboard displaying KPI cards, regression status, history table, and query inspection modal. |

---

## 5. Architectural Limitations & Assumptions Discovered
1. **No Reranker in Production Currently**: Retrieval is pure dense vector search against Qdrant (`top_k=5`). When dense similarity retrieves suboptimal chunks, Precision@5 drops. (Phase 9 recommendation: implement reciprocal rank fusion / cross-encoder reranker).
2. **Deterministic Baseline Creation**: As requested, no fabricated metrics (such as 92% Recall or 0.79 MRR) were hard-coded. The first run establishes the empirical baseline, and all subsequent runs are evaluated against it.
3. **Multi-Tenant Isolation**: Evaluation runs are strictly keyed by `company_id`. A tenant cannot query or view another tenant's evaluation history or query breakdown.
