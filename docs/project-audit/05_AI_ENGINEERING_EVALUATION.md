# 05 — AI Engineering Evaluation

This document evaluates the technical depth, algorithmic rigor, and architectural maturity of the **AI Engineering** implementations within the Avtaar platform.

---

## 1. RAG Engineering & Retrieval Pipeline

Avtaar implements a state-of-the-art **Hybrid Multi-Stage RAG Pipeline** rather than a naive vector look-up:

```
                  ┌──────────────────────┐
                  │   User Query String  │
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌───────────────────────┐         ┌───────────────────────┐
│  Dense Vector Search  │         │  Sparse Lexical Search│
│  - Gemini / CPU Embed │         │  - Pure Python BM25   │
│  - Qdrant Cosine Dist │         │  - Tokenized Inverted │
│  - Tenant ID Filter   │         │    Index Cache        │
└───────────┬───────────┘         └───────────┬───────────┘
            │                                 │
            │   Dense Candidates              │   Sparse Candidates
            │   [(Chunk_A, 0.89)...]          │   [(Chunk_A, 12.4)...]
            └────────────────┬────────────────┘
                             │
                             ▼
            ┌─────────────────────────────────┐
            │  Reciprocal Rank Fusion (RRF)   │
            │  - Constant k = 60              │
            │  - Fused Score Aggregation      │
            └────────────────┬────────────────┘
                             │
                             ▼ Top-K Fused Candidates
            ┌─────────────────────────────────┐
            │  Neural / Heuristic Reranker    │
            │  - CrossEncoder (Bi-Encoder +   │
            │    Cross-Attention Scoring)     │
            │  - Heuristic Exact-Match Boost  │
            └────────────────┬────────────────┘
                             │
                             ▼ Final Top-N Grounded Chunks
            ┌─────────────────────────────────┐
            │  Context Assembly & Prompting   │
            │  - XML Chunk Delimiters         │
            │  - Source Citation Mapping      │
            └─────────────────────────────────┘
```

### Key Engineering Details:
1. **Semantic Chunking:** `ChunkingService` uses character length boundaries with sliding window overlaps, respecting paragraph and sentence boundaries to avoid splitting mid-sentence.
2. **Deterministic Invariant Validation:** `validate_embedding_dimension_invariant` ensures at runtime that the embedding generator dimension (768 for Gemini, 384 for CPU) matches the Qdrant collection vector size before execution proceeds.
3. **Lexical BM25 Algorithm:** Implements the Okapi BM25 ranking function ($k_1=1.5, b=0.75$) with inverse document frequency ($IDF$) normalization to capture rare keywords, SKU numbers, and exact acronyms that dense vectors miss.
4. **Reciprocal Rank Fusion (RRF):** Merges disparate score scales (cosine distance $[-1, 1]$ vs unbounded BM25 scores $[0, \infty)$) into a monotonic rank score:
   $$S_{\text{RRF}}(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{60 + r_m(d)}$$

---

## 2. Retrieval Quality & Benchmarking Metrics

Avtaar includes an automated evaluation benchmark (`app/services/evaluation/runner.py`) computing standard Information Retrieval (IR) and Generation metrics:

| Metric | Definition & Purpose | Mathematical Formulation | Target Threshold |
| :--- | :--- | :--- | :--- |
| **Recall@K** | Fraction of all relevant ground-truth chunks retrieved in top-$K$. | $\text{Recall}@K = \frac{|\text{Retrieved}_K \cap \text{Relevant}|}{|\text{Relevant}|}$ | $\ge 0.85$ |
| **Precision@K** | Fraction of retrieved top-$K$ chunks that are actually relevant. | $\text{Precision}@K = \frac{|\text{Retrieved}_K \cap \text{Relevant}|}{K}$ | $\ge 0.70$ |
| **MRR (Mean Reciprocal Rank)** | How high up in the ranking the first relevant chunk appears. | $\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$ | $\ge 0.80$ |
| **NDCG@K** | Normalized Discounted Cumulative Gain accounting for position decay. | $\text{NDCG}@K = \frac{\text{DCG}@K}{\text{IDCG}@K}$ | $\ge 0.85$ |
| **Faithfulness** | LLM-judged context grounding (answers must derive strictly from context). | $\frac{|\text{Supported Claims}|}{|\text{Total Claims Made}|}$ | $\ge 0.95$ |
| **Answer Relevance** | Semantic alignment between the user question and generated response. | Cosine similarity of question and answer embeddings | $\ge 0.88$ |

---

## 3. LLM Engineering & Provider Abstraction

### A. Provider Decoupling
The core platform does not directly invoke OpenAI or Google SDKs inside business logic. Instead, all completions route through an abstract base class `LLMProvider` (`app/services/llm/base.py`):
- `GeminiProvider`: Native REST integration targeting Google Generative AI v1beta endpoints, handling token streaming, system instructions, and tool calling schemas.
- `OpenAIProvider`: Direct httpx integration for OpenAI GPT-4o / GPT-3.5 models.
- `MockLLMProvider`: Deterministic, zero-cost mock provider for local integration testing.

### B. Prompt Engineering & Injection Resistance
`PromptBuilder` constructs system prompts structured with XML tags:
- Enforces strict persona guidelines and tone.
- Structures conversation history with explicit role markers (`User:`, `Assistant:`).
- Injects retrieved chunks into `<context>` blocks and instructs the model to refuse answers if no evidence is present.

---

## 4. Agentic AI & Tool Orchestration

Avtaar's agent architecture combines deterministic state machine safety with autonomous LLM tool selection:

### A. Bounded ReAct Loop
`AgentOrchestrator` runs a step-limited reasoning cycle (default: max 5 iterations). If the LLM generates a tool call, the orchestrator:
1. Validates the tool name against the employee's assigned permissions.
2. Validates parameters against the Pydantic tool argument schema.
3. Checks whether the action requires human confirmation.
4. Executes the tool or halts for confirmation.
5. Injects the tool result back into the prompt context and re-invokes the LLM for the final conversational synthesis.

### B. Loop Prevention & Failure Recovery
- Hard iteration cap prevents infinite tool calling loops.
- Error normalization catches tool exceptions and formats them as structured JSON strings back to the LLM (e.g. `{"error": "Order #999 not found"}`), allowing the LLM to gracefully explain the issue to the user without crashing the server.

---

## 5. Production AI Engineering & Governance

1. **Token Cost Tracking:** Dynamic model pricing registry computes exact micro-dollar costs per completion turn and records them into a queryable ledger.
2. **Budget Enforcement:** Atomic monthly budget checks prevent runaway API bills by throwing `BudgetExceededException` (HTTP 429) when hard limits are crossed.
3. **OpenTelemetry Tracing:** Custom spans instrument every major phase of AI execution:
   - `span: rag.retrieval` (records dense/sparse search timings and chunk counts).
   - `span: llm.generate` (records prompt tokens, completion tokens, model name, and TTFT).
   - `span: tool.execute` (records tool name, argument types, and execution duration).
4. **Zero-Leak Logging:** Sensitive API keys, JWTs, and PII are redacted before logs are written.
