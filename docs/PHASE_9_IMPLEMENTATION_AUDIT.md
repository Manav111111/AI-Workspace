# Phase 9 — Hybrid Retrieval + Reranking Engine: Implementation Audit

## 1. Executive Summary & Objective
This audit examines Avtaar's current retrieval and RAG architecture following the completion and verification of Phase 8.

Phase 8 established an empirical baseline against live Qdrant Cloud and Gemini:
- **Recall@5**: 45.0%
- **Recall@1**: 16.7%
- **MRR**: 0.5267
- **NDCG@5**: 0.3767
- **Faithfulness**: 99.3%
- **Answer Relevance**: 60.5%
- **Negative Refusal Accuracy**: 100%
- **Avg Latency**: ~7,194 ms

The objective of Phase 9 is to implement:
1. **Dense Semantic Retrieval** (preserving Qdrant vector search).
2. **Sparse Lexical Retrieval** (BM25 keyword search capturing exact identifiers, policy names, and terms).
3. **Hybrid Result Fusion** (Reciprocal Rank Fusion - RRF).
4. **Pluggable Reranking Layer** (`NoOpReranker`, lightweight `CrossEncoderReranker`, and LLM/heuristic reranker with failure-safe fallback).
5. **Configurable Retrieval Pipeline** (`RETRIEVAL_MODE`: `dense`, `sparse`, `hybrid`, `reranker_enabled`).
6. **Benchmark Comparison**: Benchmarking all four configurations (`DENSE_ONLY`, `SPARSE_ONLY`, `HYBRID`, `HYBRID + RERANKER`) against the fixed Phase 8 golden dataset to measure empirical quality and latency tradeoffs.

---

## 2. Files Inspected

1. `backend/app/services/retrieval.py`:
   - `RetrievalService` currently accepts `company_id`, `query`, `knowledge_base_ids`, `top_k`, `score_threshold`.
   - Already defines `RetrievedChunk` dataclass and placeholder `Reranker` / `NoOpReranker` abstractions.
2. `backend/app/models/document_chunk.py`:
   - Contains `content` (full text), `chunk_metadata`, `company_id`, `knowledge_base_id`, `document_id`.
   - Chunks are relational records in PostgreSQL/SQLite and points in Qdrant.
3. `backend/app/repositories/document_chunk.py`:
   - Tenant-scoped repository for document chunks. Needs `list_by_knowledge_bases()` to query tenant chunks for sparse indexing.
4. `backend/app/services/qdrant_service.py`:
   - Handles dense vector search with payload filters (`company_id`, `knowledge_base_id`).
5. `backend/app/core/config.py`:
   - Contains `RAG_TOP_K`, `RAG_SCORE_THRESHOLD`. Needs Phase 9 retrieval and reranking configuration keys.
6. `backend/app/services/conversation_engine.py`:
   - Production entry point for chat; instantiates and calls `RetrievalService.retrieve()`.
7. `backend/app/services/evaluation/runner.py`:
   - Phase 8 evaluation runner; directly invokes `RetrievalService.retrieve()`.
8. `backend/data/golden_eval_dataset_hr.jsonl` & `backend/data/baseline.json`:
   - Golden test dataset and empirical Phase 8 baseline.

---

## 3. Current Retrieval Architecture & Integration Point

### Current Flow:
```
ConversationEngine / EvaluationRunner
       ↓
RetrievalService.retrieve(company_id, query, knowledge_base_ids, top_k)
       ↓
EmbeddingService (embed query)
       ↓
QdrantService.search (dense vector similarity)
       ↓
Score thresholding & truncation
       ↓
RetrievedChunk[]
```

### Proposed Phase 9 Pipeline Architecture:
```
ConversationEngine / EvaluationRunner / Tool
       ↓
RetrievalService.retrieve(...)  <-- SINGLE PUBLIC ENTRY POINT (Unchanged interface)
       ↓
RetrievalPipeline
       ├── DenseRetriever (Qdrant semantic search)
       ├── SparseRetriever (BM25 lexical search over tenant chunks)
       └── HybridFusion (Reciprocal Rank Fusion - RRF)
       ↓
Reranker (NoOp / CrossEncoder / LLM fallback)
       ↓
RetrievedChunk[] (top-K final candidates)
```

The rest of the system (`ConversationEngine`, Phase 8 `EvaluationRunner`, Agent tools) will interact strictly with `RetrievalService`, preserving total backward compatibility.

---

## 4. Sparse (BM25) Strategy & Lifecycle

### 4.1 Indexing & Storage
- Document chunks reside in the primary relational database (`document_chunks` table).
- We implement `BM25Index`:
  - Mathematical implementation of Okapi BM25 ($k_1=1.5, b=0.75$) with regex tokenization (lowercasing, preserving alphanumeric tokens, hyphenated terms, policy identifiers).
  - Also integrates `rank-bm25` if available, with built-in pure-Python fallback.
- **Tenant & KB Boundary**: The BM25 index is **never global**. Each index instance is scoped strictly to `(company_id, tuple(knowledge_base_ids))`. Chunks from other tenants are never loaded or scored.
- **Lifecycle & Cache Invalidation**:
  - `TenantBM25Cache`: In-memory cache keyed by `(company_id, knowledge_base_scope)`.
  - Automatically invalidated on document chunk insertion or deletion.
  - On-demand rebuild capability via internal service call.

---

## 5. Hybrid Fusion (RRF) Formulation
Reciprocal Rank Fusion is applied across dense and sparse ranked lists:
$$RRF(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{k_{rrf} + \text{rank}_m(d)}$$
where $k_{rrf} = 60$ by default.
- If a chunk appears in both dense and sparse results, its fusion score is boosted.
- If a chunk appears in only one list, it still receives a fractional rank score.
- The fused result set is sorted by descending $RRF(d)$ and truncated to `candidate_k` (default: 20) before passing to the reranker.

---

## 6. Reranking Architecture & Failure Handling
- **`Reranker` Abstract Base Class**:
  - `NoOpReranker`: Passes fused candidates through based on RRF score.
  - `CrossEncoderReranker`: Lightweight cross-encoder scoring pairs `(query, chunk.text)` when dependencies are present.
  - `LLMReranker` / Heuristic Reranker: Uses prompt/token-overlap relevance scoring.
- **Failure-Safe Fallback**: If reranking raises an exception or times out, the system automatically falls back to RRF candidate order with a structured warning log. The user chat or evaluation run never crashes.

---

## 7. Multi-Tenant Security & Cache Invariant
- Dense search filter: `{ company_id: <tenant_id>, knowledge_base_id: { in: <assigned_kbs> } }`.
- Sparse search filter: `SELECT ... FROM document_chunks WHERE company_id = :cid AND knowledge_base_id IN (:kb_ids)`.
- Reranker candidate set: Strictly bounded to the union of dense and sparse candidates already verified for the tenant.

---

## 8. Dependencies & Environment
- Added `rank-bm25>=0.2.2` to `backend/requirements.txt`.
- Built-in pure-Python BM25 fallback guarantees zero system crash if an external package is missing.
- Default CPU compatibility preserved (no mandatory GPU/CUDA requirements).
