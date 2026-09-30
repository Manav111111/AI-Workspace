# 10 — Resume and Portfolio Content

This document provides verified, high-impact resume bullet points, GitHub README descriptions, portfolio summaries, and safe-claim guidelines based strictly on the verified Avtaar codebase.

---

## 1. Resume Project Description

**Avtaar — Enterprise Multi-Tenant AI Employee Platform** | *Next.js 14, TypeScript, FastAPI, Python, PostgreSQL, Qdrant, Redis, OpenTelemetry*
- Built an enterprise control plane for deploying autonomous, action-capable AI Employees with hybrid RAG retrieval, bounded agent tool execution, and multi-tenant data isolation.

---

## 2. Five Technically Rigorous Resume Bullets

- **Multi-Stage Hybrid RAG Architecture:** Designed an asynchronous retrieval pipeline integrating Qdrant dense vector search (Gemini 768d), pure Python BM25 sparse lexical search, Reciprocal Rank Fusion ($k=60$), and Cross-Encoder neural reranking to optimize domain-specific document retrieval.
- **Bounded Agent Orchestration & Safety:** Implemented a ReAct-style tool execution engine featuring Pydantic schema validation, permission checks, and a database-backed `PendingToolAction` lifecycle requiring explicit human confirmation for state-mutating operations.
- **Multi-Tenant Security & Invariant Hardening:** Enforced strict tenant boundaries across SQL repositories, Qdrant vector payload filters, and in-memory caches, verified with automated cross-tenant security probing and startup vector-dimension invariant checks.
- **AI Evaluation & Automated Benchmarking:** Created an automated benchmarking framework evaluating IR and generation metrics (Recall@K, Precision@K, MRR, NDCG@K, Faithfulness) across golden datasets with baseline regression detection.
- **Enterprise Governance & Observability:** Implemented dynamic token cost metering with soft/hard monthly budget limits, distributed OpenTelemetry request tracing, and automated PII/credential sanitization.

---

## 3. GitHub README Project Overview

```markdown
# Avtaar — Enterprise Control Plane for AI Employees

Avtaar is an enterprise B2B platform for building, governing, and deploying autonomous AI Employees. Unlike basic conversational chatbots, Avtaar combines a multi-stage hybrid RAG pipeline with a bounded agentic execution framework that enforces human-in-the-loop confirmation before executing state-mutating actions.

### 🚀 Key Features
- **Multi-Tenant Isolation:** Complete tenant separation across PostgreSQL queries, Qdrant vector filters, and Redis caches.
- **Hybrid RAG Pipeline:** Dense vector search (Gemini/CPU) + Sparse BM25 + Reciprocal Rank Fusion + Cross-Encoder Reranking.
- **Action-Capable Agents:** Bounded tool calling with human confirmation cards for write operations.
- **Usage & Cost Governance:** Token usage tracking, model pricing registry, and monthly budget limits.
- **Embeddable Runtime:** Zero-dependency vanilla JS widget (`widget.js`) with domain whitelisting and session JWT security.
- **Comprehensive Observability:** OpenTelemetry distributed tracing and automated credential redaction.
```

---

## 4. Short Portfolio Project Summary (150 Words)

> *"Avtaar is a production-grade enterprise platform designed to deploy autonomous, action-capable AI Employees. Built with FastAPI, Next.js 14, PostgreSQL, and Qdrant, Avtaar solves the three primary enterprise barriers to AI adoption: hallucination, unverified tool execution, and lack of governance.*
> 
> *The platform features a multi-stage hybrid RAG pipeline that combines dense vector search with BM25 lexical keyword matching and Cross-Encoder neural reranking to ensure citation-backed factual grounding. To safeguard critical business data, our agent execution engine requires explicit human-in-the-loop confirmation before executing any state-mutating action.*
> 
> *Backed by 131 automated unit and integration tests, Avtaar incorporates strict multi-tenant isolation, dynamic token cost governance, and OpenTelemetry distributed tracing."*

---

## 5. Claims Matrix: Safe Claims vs Claims to Avoid

### ✅ Claims You Can Safely Make (Verified in Code)
- *"I built a hybrid RAG pipeline using Dense Qdrant search, BM25 sparse search, RRF fusion, and Cross-Encoder reranking."* (Proven by `app/services/retrieval/`).
- *"I implemented a human-in-the-loop confirmation lifecycle for state-mutating agent actions."* (Proven by `app/services/agent/tool_executor.py` and `PendingToolAction`).
- *"I enforced multi-tenant data isolation across the database, vector search, and rate limiting."* (Proven by `TenantContext` and `test_tenant_isolation.py`).
- *"The test suite passes 131 automated unit and integration tests."* (Proven by `pytest -v` output).
- *"The system tracks token usage and enforces monthly dollar budget limits."* (Proven by `BudgetService` and `UsageBudget`).

### ❌ Claims to Avoid Making Until Built
- 🚫 *"We process millions of enterprise users in production."* (Avoid: It is a functional MVP/portfolio platform, not yet deployed to commercial enterprise scale).
- 🚫 *"Our system uses 3D photorealistic neural video avatars."* (Avoid: The avatar layer is a reactive 2D SVG/Canvas state machine).
- 🚫 *"We use distributed Celery queues across AWS."* (Avoid: Local mode runs async worker in-process; Celery is on the P1 roadmap).
