# Phase 8 — RAG Evaluation & Benchmarking Report

## 1. Overview
In Phase 8, we engineered and deployed a production-grade, internal **RAG Evaluation and Benchmarking Engine** for the Avtaar AI Employee platform. 

Rather than relying on ungrounded claims or simulated pipelines, the evaluation engine evaluates the **exact production RAG system**—calling the same `RetrievalService`, Qdrant Cloud vector search, `PromptBuilder`, and LLM generation pipelines used in live user chat.

---

## 2. Architecture & Invariants

```
                         EXISTING AVTAAR PRODUCTION RAG
                                        │
                         ┌──────────────┴──────────────┐
                         │                             │
                     User Chat                 Evaluation Runner
                         │                             │
                         └──────────────┬──────────────┘
                                        ↓
                              SAME RetrievalService
                                        ↓
                              SAME Qdrant Cloud
                                        ↓
                              SAME PromptBuilder
                                        ↓
                              SAME Gemini LLM
                                        ↓
                        ┌───────────────┴───────────────┐
                        ↓                               ↓
                 Pure IR Engine                  NLG Judge
               • Recall@1/3/5                  • Faithfulness (LLM)
               • Precision@1/3/5               • Relevance (Cosine)
               • MRR                           • Refusal Accuracy
               • NDCG@5
```

### Invariants Enforced:
1. **Zero Greenfield Duplication**: Normal chat and evaluation runners execute the same retrieval and prompt logic.
2. **Empirical Baselines (Zero Hardcoded Claims)**: Benchmark metrics are derived strictly from running the golden dataset. The first live execution creates `baseline.json`; all subsequent runs enforce regression gates against this baseline.
3. **Multi-Tenant Scoping**: All benchmark runs and per-query evaluation results are strictly bound to `company_id` and the evaluated employee's assigned knowledge bases.

---

## 3. Files Implemented & Modified

### Backend Additions & Updates:
- `backend/app/models/evaluation.py`: SQLAlchemy models for `EvaluationRun` and `EvaluationResultItem`.
- `backend/app/models/__init__.py`: Registered evaluation models.
- `backend/app/services/evaluation/dataset.py`: `GoldenQueryItem` schema and `DatasetValidator` with JSONL support.
- `backend/app/services/evaluation/metrics.py`: Pure Python IR metrics calculator (Recall@1/3/5, Precision@1/3/5, MRR, NDCG@K).
- `backend/app/services/evaluation/judge.py`: Generation evaluator (LLM-as-a-judge for Faithfulness, semantic Answer Relevance, Negative Refusal evaluator).
- `backend/app/services/evaluation/runner.py`: Asynchronous evaluation runner with bounded concurrency (`asyncio.Semaphore(3)`) and Markdown/JSON report generator.
- `backend/app/services/evaluation/baseline.py`: Baseline manager and regression gate comparator with configurable tolerances.
- `backend/app/api/v1/evaluations.py`: REST API router for managing evaluation runs, baselines, and reports.
- `backend/app/schemas/evaluation.py`: Pydantic V2 schemas for API requests and responses.
- `backend/data/golden_eval_dataset_hr.jsonl`: Curated 20-query golden dataset (15 positive HR questions + 5 negative out-of-scope questions).
- `backend/data/baseline.json`: Active production baseline persistence.
- `backend/tests/test_rag_evaluation.py`: Automated test suite containing 12 unit/integration tests covering metrics, judges, baseline regression, and runner.

### Frontend Additions & Updates:
- `frontend/src/app/(dashboard)/evaluations/page.tsx`: Complete evaluation dashboard featuring:
  - Active Regression Gate status card.
  - 7 KPI metric cards (Recall@5, Recall@1, MRR, NDCG@5, Faithfulness, Answer Relevance, Latency).
  - Historical Evaluation Runs table with report generation and baseline promotion.
  - Query-by-Query Performance Breakdown with category filters and search.
  - Modal drawer inspecting query text, ground-truth expected chunks vs. retrieved chunks with cosine scores, and generated vs. reference answers.
  - "Run Benchmark" trigger modal with employee selector, dataset choices, and generation toggle.
- `frontend/src/components/layout/Sidebar.tsx`: Added "RAG Evaluations" tab with Phase 8 badge.
- `frontend/src/types/index.ts`: TypeScript interfaces for `EvaluationRun`, `EvaluationResultItem`, and `EvaluationBaseline`.
- `frontend/src/lib/api.ts`: API client methods for evaluation endpoints.

---

## 4. Live Production Baseline Results

Executed on the live production environment against Qdrant Cloud and Google Gemini:

- **Run ID**: `aaaa5f70-53f8-4522-b44c-9470c85cbe2b`
- **AI Employee**: Maya (HR Specialist)
- **Dataset**: `golden_eval_dataset_hr` (20 queries: 15 answerable, 5 negative)
- **Baseline Date**: 2026-09-24

### Metrics Summary:
| Metric | Baseline Score | Description |
| :--- | :--- | :--- |
| **Recall@5** | **45.0%** (0.4500) | Ratio of expected ground-truth chunks appearing in top 5 retrieved results. |
| **Recall@3** | **31.7%** (0.3167) | Ratio of expected ground-truth chunks appearing in top 3 retrieved results. |
| **Recall@1** | **16.7%** (0.1667) | Top-1 retrieval accuracy. |
| **Precision@5** | **18.7%** (0.1867) | Fraction of retrieved top-5 chunks that are relevant. |
| **MRR** | **0.5267** | Mean Reciprocal Rank (harmonic mean of the rank of the first relevant chunk). |
| **NDCG@5** | **0.3767** | Normalized Discounted Cumulative Gain at rank 5. |
| **Faithfulness** | **99.3%** (0.9933) | LLM-as-a-judge score: percentage of claims in the generated response grounded in retrieved context. |
| **Answer Relevance** | **60.5%** (0.6053) | Semantic token overlap and alignment with ground-truth reference answers. |
| **Negative Refusal Accuracy** | **100.0%** (1.0000) | Successfully refused 5 out of 5 out-of-scope/unanswerable queries without hallucinations. |
| **Avg Latency** | **7,194 ms** | End-to-end retrieval (Qdrant Cloud) + generation (Gemini) + judge evaluation. |

---

## 5. Regression Gate Policy

Stored in `backend/data/baseline.json`, the regression gate enforces the following CI/CD rules:
- **Recall@5 drop tolerance**: $\le 0.05$ (5 percentage points)
- **MRR drop tolerance**: $\le 0.05$
- **Faithfulness drop tolerance**: $\le 0.05$
- **Refusal accuracy drop tolerance**: $0.00$ (**Zero tolerance** for hallucinating on unanswerable/negative queries)

---

## 6. Verification & Test Suite Summary

1. **Pytest Regression Suite**:
   ```
   backend/tests/test_rag_evaluation.py (12 passed in 0.29s)
   ```
2. **Full Backend Test Suite**:
   ```
   ================= 97 passed, 1 skipped in 14.61s =================
   ```
3. **Frontend Compilation**:
   ```
   npx tsc --noEmit (0 errors)
   ```
4. **End-to-End API Verification**:
   - `GET /api/v1/evaluations/baseline` $\rightarrow$ `200 OK`
   - `GET /api/v1/evaluations` $\rightarrow$ `200 OK` (Tenant isolation verified)
   - `GET /api/v1/evaluations/{id}` $\rightarrow$ `200 OK` (20 items with scores & latencies)
   - `GET /api/v1/evaluations/{id}/report` $\rightarrow$ `200 OK` (Formatted markdown report generated)

---

## 7. Known Observations & Recommendations for Next Phase
1. **Precision@5 and Recall@5 Optimization (Phase 9 Recommendation)**:
   - Pure dense vector retrieval achieved 45.0% Recall@5.
   - Introducing hybrid sparse-dense search (BM25 + Dense) with reciprocal rank fusion (RRF) and a cross-encoder reranker (e.g. `bge-reranker-base`) is recommended to lift Recall@5 above 75%.
2. **Latency Optimization**:
   - Remote Qdrant Cloud network round-trips plus Gemini generation took an average of 7.2s.
   - In production, running evaluation asynchronously in a background Celery/Redis worker or pre-caching vector embeddings will streamline execution.
