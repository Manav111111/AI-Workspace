# AVTAAR — PLAYGROUND & RAG EVALUATION ARCHITECTURE

## 1. Overview & Architectural Alignment
The **Playground** and **Evaluation Benchmark Engine** are AI engineering debugging and quality assurance interfaces built directly on top of the **Canonical Production AI Runtime**.

They do NOT use mock pipelines or fake retrievals. They execute real Qdrant vector retrieval, real BM25 lexical search, real PromptBuilder XML assembly, real LLM calls, and real usage metering.

---

## 2. AI Employee Playground Lifecycle

### Session Isolation & Configuration Snapshots
When an engineer tests in the Playground:
1. `PlaygroundService.create_session()` creates an immutable snapshot of the AI Employee's configuration (`system_prompt`, `personality`, `model`, `temperature`, `top_k`, `assigned_kb_ids`, `assigned_tools`).
2. Overrides can be applied in real-time to test prompt adjustments or hyperparameter changes without modifying the live production AI Employee.
3. Each turn executes against `RetrievalService` and `PromptBuilder`, returning detailed debug trees:
   - **Retrieval Inspector:** Displays dense scores, BM25 rank, chunk IDs, source document names, and page numbers.
   - **Prompt Inspector:** Displays assembled XML context, system instructions, and token metrics.
   - **Trace Inspector:** Displays latency breakdown (`retrieval_ms`, `llm_ms`, `total_ms`) and token consumption.

### Session Resilience & Self-Healing
- The frontend holds the active `PlaygroundSessionResponse` and persists the session ID.
- If a session is deleted or expired on the backend, the frontend automatically re-initializes a fresh snapshot session and retries seamlessly, eliminating "session not found" errors.

---

## 3. Automated RAG Evaluation Benchmark Engine

### Benchmark Execution Flow
```
1. Admin / Owner triggers evaluation (`POST /api/v1/evaluations/run`)
    ↓
2. Rate Limiter checks quota (30 runs/hour, fail_open_with_local fallback)
    ↓
3. EvaluationRunner loads golden test dataset (e.g. 50-item enterprise dataset)
    ↓
4. For each test query:
   ├─ Executes Canonical RetrievalService (Dense + Sparse + RRF)
   ├─ Computes Retrieval Metrics: Recall@1, Recall@3, Recall@5, MRR, Precision, NDCG
   ├─ Runs LLM Generation & Judge (Faithfulness, Answer Relevance, Groundedness)
   └─ Measures per-case latency and token cost
    ↓
5. BaselineManager computes regression against baseline run
    ↓
6. Persists EvaluationRun & EvaluationResultItem records in PostgreSQL
    ↓
7. Returns complete aggregate metrics summary and case-by-case evaluation table
```

### Rate Limiting Policy Distinction
- **Interactive Chat Traffic:** User-facing sliding window (30 requests/minute).
- **Evaluation Workloads:** Dedicated evaluation rate limit (30 benchmark runs/hour), isolated from chat traffic to prevent benchmark runs from blocking end-user conversations.
- **Fail-Open Fallback:** When Redis is offline, rate limiter seamlessly uses thread-safe in-memory sliding windows instead of hard-rejecting requests.
