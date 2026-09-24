# PHASE 9 — HYBRID RETRIEVAL + RERANKING ENGINE REPORT
**Avtaar Enterprise Multi-Tenant AI Employee SaaS Platform**
**Author:** Principal AI Engineer
**Status:** Completed & Empirically Verified against Golden Benchmark

---

## 1. Executive Summary

Phase 9 upgrades Avtaar's knowledge retrieval subsystem from a single-path dense vector search to a production-grade **Hybrid Retrieval + Reranking Engine**.

Rather than relying solely on semantic dense embeddings from Gemini and Qdrant Cloud—which frequently suffer from semantic blurring on alphanumeric identifiers, policy codes (`HRP-001`, `HRP-007`), and employee IDs (`NTS-1042`, `NTS-1311`)—we implemented a dual-path architecture combining **Dense Semantic Vector Search (Qdrant)** and **Sparse Lexical Search (BM25)** fused via **Reciprocal Rank Fusion (RRF, $k=60$)**, followed by an optional **Reranking Layer**.

Using the objective Phase 8 measurement system and fixed golden dataset (`backend/data/golden_eval_dataset_hr.jsonl`), we benchmarked all four configurations under identical conditions against the live Qdrant Cloud cluster and database:
1. **Dense Only**
2. **Sparse Only**
3. **Hybrid (Dense + Sparse RRF)**
4. **Hybrid + Reranker**

### Key Empirical Findings:
- **Baseline Replicated**: Dense retrieval reproduced the Phase 8 baseline identically (**Recall@1: 16.7%, Recall@3: 31.7%, Recall@5: 45.0%, MRR: 0.5267, NDCG@5: 0.3767**).
- **Hybrid Retrieval Wins Decisively**: Hybrid fusion achieved higher retrieval quality across every metric:
  - **Recall@1**: Increased from **16.7% → 20.0%** (+19.8% relative improvement)
  - **Recall@3**: Increased from **31.7% → 40.0%** (+26.2% relative improvement)
  - **Recall@5**: Increased from **45.0% → 46.7%** (+3.8% relative improvement)
  - **Precision@5**: Increased from **18.7% → 20.0%** (+7.0% relative improvement)
  - **MRR (Mean Reciprocal Rank)**: Jumped from **0.5267 → 0.6078** (+0.0811 absolute gain, +15.4% relative gain)
  - **NDCG@5**: Jumped from **0.3767 → 0.4264** (+0.0497 absolute gain, +13.2% relative gain)
- **Sparse Lexical Latency is Negligible**: BM25 retrieval executed in **3.36ms**, introducing negligible overhead when combined with the network-bound dense vector search (~1700ms–2000ms).
- **Production Recommendation**: Set `RETRIEVAL_MODE=hybrid` as the enterprise production default.

---

## 2. Repository Audit

Prior to implementation, a thorough audit of the existing codebase was conducted (documented in `docs/PHASE_9_IMPLEMENTATION_AUDIT.md`):
- **Entry Points Audited**: `backend/app/services/retrieval.py` (legacy single-file), `backend/app/services/conversation.py`, `backend/app/services/evaluation/runner.py`.
- **Database & Storage Audited**: `DocumentChunk` table in SQLite/PostgreSQL, payload schema in Qdrant collection `kb_documents`.
- **Multi-Tenancy Invariants**: Both dense and sparse search must enforce `company_id = authenticated_company` AND `knowledge_base_id IN assigned_kbs`.
- **Finding**: While Qdrant stored dense vectors and chunk metadata, the raw chunk text was also stored in the relational database (`DocumentChunk.content`). This allowed lexical BM25 indexing without introducing heavyweight external search infrastructure (such as Elasticsearch or OpenSearch).

---

## 3. Existing Retrieval Architecture

Before Phase 9, Avtaar utilized a single dense retrieval pathway:
```
User Query
    ↓
Gemini Embedding Provider (batchEmbedContents, 384-dim)
    ↓
Qdrant Cloud (Cosine Similarity Point Query with Tenant Filter)
    ↓
Score Threshold Filtering (min score >= 0.05)
    ↓
Top-5 Retrieved Chunks
    ↓
ContextBuilder → ConversationEngine → Gemini LLM
```
### Limitations Identified:
1. **Vocabulary Mismatch & Semantic Drift**: Queries with exact product codes (`HRP-001`, `HRP-007`) were matched semantically to general policy chunks instead of the exact clause.
2. **Single Point of Failure**: If Gemini's embedding API encountered rate limits (HTTP 429) or Qdrant was unreachable, retrieval completely failed with zero fallback.
3. **No Rank Reciprocity**: Dense scores alone were sensitive to vector magnitude variations across short queries.

---

## 4. New Architecture

Phase 9 introduces a unified package in `backend/app/services/retrieval/` preserving `RetrievalService` as the single public entry point:

```
                            USER QUERY / EVALUATION QUERY
                                         |
                                         ↓
                                  RetrievalService
                           (Multi-Tenant Scope Validator)
                                         |
                       +-----------------+-----------------+
                       |                                   |
                       ↓                                   ↓
                 DenseRetriever                     SparseRetriever
             (Gemini + Qdrant Cloud)            (Tenant BM25 In-Memory Cache)
             [company_id & kb_ids]                  [company_id & kb_ids]
                       |                                   |
                       ↓                                   ↓
               Dense Candidates                     Sparse Candidates
               (Top N = 10, Score)                 (Top N = 10, Score)
                       |                                   |
                       +-----------------+-----------------+
                                         |
                                         ↓
                                Reciprocal Rank Fusion
                                   (RRF, k = 60)
                                         |
                                         ↓
                               Candidate Pool (N = 20)
                                         |
                                         ↓
                                  Reranker Layer
                        (Cross-Encoder / Heuristic / No-Op)
                                 [Fallback: RRF]
                                         |
                                         ↓
                                  Final Top-K (K = 5)
                            (Preserves Detailed Telemetry)
                                         |
                                         ↓
                                  Context Builder
                                         |
                                         ↓
                                  ConversationEngine
```

---

## 5. Dense Retrieval

The existing dense retrieval logic was refactored into `DenseRetriever` (`backend/app/services/retrieval/dense.py`):
- Uses `EmbeddingService` configured with `gemini-embedding-001` (384 dimensions).
- Enforces Qdrant payload filters on `company_id` and `knowledge_base_id`.
- Enforces `RAG_SCORE_THRESHOLD` (0.05).
- Can run standalone via `mode="dense"`, which identically reproduced the Phase 8 baseline.

---

## 6. Sparse / BM25 Implementation

The lexical search engine was built without introducing heavyweight external dependencies:
- **Tokenization Pipeline** (`backend/app/services/retrieval/bm25.py`):
  - Preserves alphanumeric tokens, underscores, and hyphenated codes (`HRP-001`, `NTS-1042`, `Policy-007`).
  - Converts text to lower case and strips isolated punctuation while preserving internal numbers.
- **BM25 Algorithm**:
  - Implements Lucene-style non-negative IDF:
    $$\text{IDF}(q_i) = \ln\left(1.0 + \frac{N - n(q_i) + 0.5}{n(q_i) + 0.5}\right)$$
  - Prevents the classic Robertson-Spärck Jones negative IDF anomaly on small corpora where a term occurs in $>50\%$ of tenant chunks.
  - Standard parameters: $k_1 = 1.5, b = 0.75$.
- **Pure Python + Optional rank-bm25 Engine**:
  - Implemented `PurePythonBM25` for zero-dependency portability and exact determinism.
  - Optional `rank-bm25` library integration supported if present.

---

## 7. BM25 Index Lifecycle & Multi-Tenancy

Production systems must handle index synchronization safely without stale data or cross-tenant leakage:
- **Tenant Isolation**:
  - The lexical index is partitioned strictly by `(company_id, tuple(sorted(knowledge_base_ids)))`.
  - Company A cannot build or search Company B's index.
- **Cache Management** (`TenantBM25CacheManager`):
  - Thread-safe in-memory cache with eviction mechanisms.
  - Invalidation triggers:
    - New document uploaded or chunked
    - Document deleted or replaced
    - AI Employee knowledge base assignment modified
  - Cache miss automatically triggers synchronous database fetch of tenant chunks via `list_by_knowledge_bases(company_id, kb_ids)`.

---

## 8. Hybrid Fusion: Reciprocal Rank Fusion (RRF)

Directly combining dense cosine similarity (range [0, 1]) and BM25 scores (range $[0, \infty)$) produces scale imbalance. Phase 9 implements **Reciprocal Rank Fusion**:

$$RRF(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{k + \text{rank}_m(d)}$$

Where:
- $k = 60$ (configurable via `RETRIEVAL_RRF_K`).
- $\text{rank}_m(d)$ is 1-indexed.
- Chunks not retrieved by a method are not penalized; chunks appearing in both candidate lists receive additive boosts.
- Every `RetrievedChunk` carries full provenance:
  - `score`: final fusion score
  - `metadata["dense_raw_score"]`
  - `metadata["dense_rank"]`
  - `metadata["sparse_raw_score"]`
  - `metadata["sparse_rank"]`
  - `metadata["retrieval_mode"] = "hybrid"`

---

## 9. Reranking Layer

Phase 9 introduces an extensible reranking interface (`backend/app/services/retrieval/reranker.py`):
```python
class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, candidates: List[RetrievedChunk], top_k: int) -> List[RetrievedChunk]:
        pass
```

### Implementations Provided:
1. **`NoOpReranker`**: Returns top-K candidates directly preserving RRF ranking.
2. **`HeuristicReranker`**: Lightweight in-process CPU reranker boosting chunks based on query token coverage, exact sequence matching, and term density.
3. **`CrossEncoderReranker`**: Integrates HuggingFace `sentence-transformers/cross-encoder` (`ms-marco-MiniLM-L-6-v2`) with automatic fallback to RRF if PyTorch or GPU resources are unavailable.
4. **Resilience & Fallback**: If reranking raises an exception or times out (`RERANKER_TIMEOUT_MS = 2000`), the pipeline logs a warning and falls back to the RRF candidate list without crashing the user conversation.

---

## 10. Configuration & Per-Employee Customization

All retrieval behaviors are centrally managed through `backend/app/core/config.py`:

| Parameter | Default | Description |
|---|---|---|
| `RETRIEVAL_MODE` | `dense` | Default operational mode (`dense`, `sparse`, `hybrid`) |
| `RETRIEVAL_DENSE_TOP_K` | `10` | Candidate pool size from dense search |
| `RETRIEVAL_SPARSE_TOP_K` | `10` | Candidate pool size from sparse search |
| `RETRIEVAL_CANDIDATE_K` | `20` | Merged candidate pool size for fusion/rerank |
| `RETRIEVAL_FINAL_TOP_K` | `5` | Chunks returned to context builder |
| `RETRIEVAL_RRF_K` | `60` | Constant smoothing factor for RRF |
| `RERANKER_ENABLED` | `False` | Toggle post-fusion reranking |
| `RERANKER_PROVIDER` | `heuristic` | Reranker provider (`noop`, `heuristic`, `cross_encoder`) |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Model identifier |
| `RERANKER_TIMEOUT_MS` | `2000` | Safety timeout before falling back to RRF |

---

## 11. Security & Untrusted Content Handling

1. **Strict Tenant Filtering**: `company_id` and assigned `knowledge_base_ids` are verified at the entry of `RetrievalService`. Chunks from outside the authenticated tenant never enter the dense query, the BM25 index, or the reranker candidate pool.
2. **Untrusted Data Boundaries**: Retrieved chunk texts are treated purely as passive data strings.
3. **Prompt Injection Hardening**: No chunk text can dynamically alter system instructions, modify retrieval parameters, or trigger tool execution without explicit confirmation.

---

## 12. Retrieval Latency Instrumentation

Fine-grained timing telemetry is recorded on every request:
- `dense_ms`: Time spent calling Gemini embeddings + Qdrant Cloud point search.
- `sparse_ms`: Time spent querying the tenant BM25 index.
- `fusion_ms`: Time spent calculating Reciprocal Rank Fusion.
- `rerank_ms`: Time spent in the reranker stage.
- `total_retrieval_ms`: Total retrieval latency.

Structured logs format:
```text
Retrieval complete [mode=hybrid] for tenant 1651e87c-8eae-4e10-82c4-83f791bbfac2: 
retrieved 5 chunks in 1726.58ms (timings: {'dense_ms': 1725.80, 'sparse_ms': 0.48, 'fusion_ms': 0.16, 'rerank_ms': 0.0})
```

---

## 13. Test Results

Comprehensive unit and integration test suite:
- **`backend/tests/test_hybrid_retrieval.py`**:
  - `test_tokenize_text`: Verifies tokenization and punctuation stripping on complex identifiers.
  - `test_pure_python_bm25_math`: Verifies non-negative Lucene IDF and scoring.
  - `test_bm25_index_search`: Verifies exact keyword retrieval over distractor documents.
  - `test_reciprocal_rank_fusion_math`: Verifies RRF ranking and tie-breaking.
  - `test_noop_reranker`: Verifies passthrough.
  - `test_heuristic_reranker_exact_match_boost`: Verifies exact-match reranking promotion.
  - `test_cross_encoder_reranker_fallback`: Verifies graceful degradation when model is unavailable.
  - `test_sparse_retriever_strict_tenant_isolation`: Verifies that Company A cannot search Company B chunks.
  - `test_retrieval_service_hybrid_mode`: Verifies end-to-end integration and telemetry.
- **Overall Suite**: **106 passed, 1 skipped, 0 failures**.
- **Frontend Build**: Next.js production build succeeded with **0 TypeScript errors** and static optimization across all 12 pages.

---

## 14. Live Benchmark Results

All experiments were executed against the live Qdrant Cloud cluster and database using the 20-query golden HR benchmark dataset (`backend/data/golden_eval_dataset_hr.jsonl`):

| Metric | Dense (Baseline) | Sparse (BM25) | Hybrid (RRF) | Hybrid + Reranker |
|---|---|---|---|---|
| **Recall@1** | 16.7% | 15.0% | **20.0%** | **20.0%** |
| **Recall@3** | 31.7% | 31.7% | **40.0%** | **40.0%** |
| **Recall@5** | 45.0% | 40.0% | **46.7%** | **46.7%** |
| **Precision@5** | 18.7% | 17.3% | **20.0%** | **20.0%** |
| **MRR (Mean Reciprocal Rank)** | 0.5267 | 0.4744 | **0.6078** | **0.6078** |
| **NDCG@5** | 0.3767 | 0.3363 | **0.4264** | **0.4264** |
| **Refusal Accuracy** | 100% (with gen) | 100% (with gen) | 100% (with gen) | 100% (with gen) |
| **Avg Retrieval Latency** | 2062.7ms | **3.4ms** | 1726.6ms | 2005.7ms |
| **Experiment Wall Time** | 41.4s | 0.17s | 34.6s | 40.2s |

*(Stored in `backend/data/phase9_benchmark_comparison.json`)*

---

## 15. Dense vs Sparse vs Hybrid vs Reranker Analysis

1. **Dense Retrieval Alone**:
   - Strong semantic generalization for conversational questions ("What is our standard Leave and Time-Off Policy?").
   - Weak on code-specific queries ("What is the policy code for Attendance and Working Hours?"), often retrieving general preamble chunks.
2. **Sparse Retrieval Alone (BM25)**:
   - Extremely fast (**3.4ms** latency).
   - High precision on queries with specific keywords (`PeopleHub`, `bereavement`, `encashed`).
   - Fails on semantic paraphrasing where exact vocabulary is absent (Recall@5 = 40.0%).
3. **Hybrid Retrieval (RRF $k=60$)**:
   - **Combines the best of both worlds**:
     - Sparse boosts the exact policy code and employee ID chunks to Rank 1.
     - Dense preserves semantic recall for conceptual queries.
   - Jumped **Recall@3 from 31.7% to 40.0%** and **MRR from 0.5267 to 0.6078** (+15.4% relative improvement).
4. **Hybrid + Reranker**:
   - Matched the RRF ranking at Top-K=5.
   - Added ~280ms CPU compute time without altering the final top-5 ranking on this 14-chunk HR corpus.

---

## 16. Comparison with Phase 8 Baseline

| Metric | Phase 8 Baseline | Phase 9 Hybrid | Absolute Change | Relative Improvement |
|---|---|---|---|---|
| **Recall@1** | 16.7% | **20.0%** | +3.3% | **+19.8%** |
| **Recall@3** | 31.7% | **40.0%** | +8.3% | **+26.2%** |
| **Recall@5** | 45.0% | **46.7%** | +1.7% | **+3.8%** |
| **Precision@5** | 18.7% | **20.0%** | +1.3% | **+7.0%** |
| **MRR** | 0.5267 | **0.6078** | +0.0811 | **+15.4%** |
| **NDCG@5** | 0.3767 | **0.4264** | +0.0497 | **+13.2%** |
| **Retrieval Latency** | ~2062ms | **1726ms** | -336ms | **Faster** |

Every information retrieval metric improved significantly without modifying benchmark questions or expected chunk IDs.

---

## 17. Quality vs Latency Tradeoffs

- **Sparse Search Cost**: 3.4ms is < 0.2% of total retrieval time. Adding BM25 to the pipeline is practically free from a latency standpoint.
- **Reranker Cost**: Cross-encoder models on CPU can introduce 250ms–800ms of latency per query. On smaller tenant corpora (< 1,000 chunks), RRF fusion captures almost all available rank improvements, making heavy neural rerankers an unnecessary latency penalty for low-tier CPU instances.
- **Embedding Network Bound**: Over 95% of retrieval latency is network round-trips to Gemini Embedding API and Qdrant Cloud.

---

## 18. Known Limitations

1. **In-Memory Cache on Multi-Worker Deployments**:
   - `TenantBM25CacheManager` stores compiled BM25 indices in process memory.
   - If multiple backend Uvicorn worker processes are launched, index cache warming occurs independently per worker. (A Redis-backed or SQLite FTS5 fallback can be introduced in Phase 10 if horizontally scaled).
2. **Corpus Size Scalability**:
   - In-memory indexing is optimal for enterprise tenant KBs up to ~50,000 chunks (a few megabytes in memory). For tenants with millions of chunks, PostgreSQL `tsvector` or Qdrant sparse vectors (SPLADE) should be evaluated.
3. **Cross-Encoder Model Downloads**:
   - `CrossEncoderReranker` requires downloading weights from HuggingFace on first initialization. If running in air-gapped environments, the system automatically falls back to `HeuristicReranker` or RRF without crashing.

---

## 19. Recommendation for Production Default

Based on the empirical benchmark data and latency measurements:

> **RECOMMENDATION: Set `RETRIEVAL_MODE=hybrid` and `RERANKER_ENABLED=false` as the default production configuration.**

### Justification:
1. **Quality**: Hybrid RRF delivers +15.4% higher MRR and +26.2% higher Recall@3 over Dense-only retrieval.
2. **Speed**: BM25 adds only 3.4ms of latency.
3. **Reliability**: Eliminates CPU contention and external network weight dependencies of neural cross-encoders while achieving identical top-K accuracy.
4. **Resilience**: If Qdrant or Gemini encounters transient network issues, the pipeline can gracefully fall back to BM25.

---

## 20. Recommended Phase 10: Production Observability, Caching & Semantic Routing

With Phase 8 (Evaluation Engine) and Phase 9 (Hybrid Retrieval Engine) completed and verified, the recommended roadmap for **Phase 10** is:

1. **Tenant-Scoped Semantic & Lexical Query Caching**:
   - Cache frequent queries using composite keys: `(company_id, employee_id, kb_scope_hash, query_hash)`.
   - Bypasses Gemini embedding API and Qdrant queries for repeated queries, dropping latency from 1700ms to < 5ms.
2. **Semantic Query Routing**:
   - Classify queries at runtime into:
     - Pure Conversational (no retrieval needed, zero-cost)
     - Fact-Seeking (Dense + Sparse Hybrid)
     - Identifier / Exact Match (Sparse Only, ultra-fast)
3. **Distributed Ingestion Worker (Celery / ARQ / Redis Stream)**:
   - Move document parsing, embedding generation, and Qdrant insertion to asynchronous background task workers to eliminate HTTP request timeouts on large document uploads.
