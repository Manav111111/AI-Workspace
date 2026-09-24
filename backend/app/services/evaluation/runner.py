import datetime
import logging
import time
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.ai_employee import AIEmployee
from app.models.evaluation import EvaluationRun, EvaluationResultItem
from app.services.context_builder import ContextBuilder
from app.services.evaluation.dataset import GoldenQueryItem
from app.services.evaluation.judge import GenerationJudge
from app.services.evaluation.metrics import IRMetricsCalculator
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMProvider
from app.services.prompt_builder import PromptBuilder
from app.services.retrieval import RetrievalService, RetrievedChunk

logger = logging.getLogger("app.services.evaluation.runner")


class EvaluationRunner:
    """Production Evaluation Runner.
    CRITICAL INVARIANT: Reuses the EXACT production RetrievalService, ContextBuilder,
    and PromptBuilder logic to guarantee benchmark results match user runtime experience.
    """

    def __init__(
        self,
        session: AsyncSession,
        retrieval_service: Optional[RetrievalService] = None,
        llm_provider: Optional[LLMProvider] = None,
        judge: Optional[GenerationJudge] = None,
    ):
        self.session = session
        self.retrieval = retrieval_service or RetrievalService()
        self.llm = llm_provider or get_llm_provider()
        self.judge = judge or GenerationJudge(llm_provider=self.llm)
        self.context_builder = ContextBuilder()

    async def run_evaluation(
        self,
        company_id: uuid.UUID,
        ai_employee_id: uuid.UUID,
        dataset: List[GoldenQueryItem],
        dataset_name: str = "golden_dataset",
        run_generation_eval: bool = True,
        retrieval_mode: Optional[str] = None,
        reranker_enabled: Optional[bool] = None,
    ) -> EvaluationRun:
        """Executes a full benchmark run against the active company RAG pipeline."""
        start_time = time.perf_counter()

        # 1. Resolve employee and assigned knowledge bases
        emp_stmt = (
            select(AIEmployee)
            .where(AIEmployee.id == ai_employee_id, AIEmployee.company_id == company_id)
            .options(selectinload(AIEmployee.knowledge_bases))
        )
        emp_res = await self.session.execute(emp_stmt)
        employee = emp_res.scalar_one_or_none()
        if not employee:
            raise ValueError(f"AI Employee {ai_employee_id} not found in company {company_id}")

        assigned_kb_ids = [getattr(kb, "knowledge_base_id", getattr(kb, "id", None)) for kb in employee.knowledge_bases]
        primary_kb_id = assigned_kb_ids[0] if assigned_kb_ids else None

        # 2. Create EvaluationRun record
        eval_run = EvaluationRun(
            company_id=company_id,
            ai_employee_id=ai_employee_id,
            knowledge_base_id=primary_kb_id,
            dataset_name=dataset_name,
            status="RUNNING",
            total_queries=len(dataset),
        )
        self.session.add(eval_run)
        await self.session.flush()
        await self.session.refresh(eval_run)

        item_metrics_list: List[Dict[str, Any]] = []
        result_items: List[EvaluationResultItem] = []

        try:
            for item in dataset:
                query_start = time.perf_counter()

                # --- STEP A: EXACT PRODUCTION RETRIEVAL (Dense / Sparse / Hybrid) ---
                retrieved_chunks: List[RetrievedChunk] = await self.retrieval.retrieve(
                    company_id=company_id,
                    query=item.query,
                    knowledge_base_ids=assigned_kb_ids,
                    top_k=5,
                    mode=retrieval_mode,
                    reranker_enabled=reranker_enabled,
                )


                retrieved_chunk_ids = [str(r.chunk_id) for r in retrieved_chunks]
                retrieval_scores = [round(float(r.score), 4) for r in retrieved_chunks]

                # --- STEP B: PURE IR METRICS ---
                ir_metrics = IRMetricsCalculator.compute_query_ir_metrics(
                    retrieved_ids=retrieved_chunk_ids,
                    expected_ids=item.expected_chunk_ids,
                )

                # --- STEP C: EXACT PRODUCTION CONTEXT & PROMPT ---
                has_context = len(retrieved_chunks) > 0
                context_text = self.context_builder.build_context(retrieved_chunks) if has_context else ""

                messages = PromptBuilder.build_chat_messages(
                    employee_name=employee.name,
                    role=employee.role,
                    personality=employee.personality,
                    custom_system_prompt=employee.system_prompt,
                    context_text=context_text,
                    has_context=has_context,
                    conversation_history=[],
                    current_user_query=item.query,
                )

                # --- STEP D: PRODUCTION GENERATION ---
                generated_answer = ""
                token_usage = None
                citations: List[Dict[str, Any]] = []

                if run_generation_eval:
                    llm_resp = await self.llm.generate(
                        messages=messages,
                        temperature=settings.LLM_TEMPERATURE,
                        max_tokens=500,
                    )
                    generated_answer = llm_resp.content.strip()
                    token_usage = llm_resp.usage

                    if has_context:
                        for c in retrieved_chunks:
                            citations.append({
                                "chunk_id": str(c.chunk_id),
                                "document_id": str(c.document_id),
                                "source": c.source or "Document",
                                "page_number": c.page_number,
                                "score": round(c.score, 3),
                            })

                query_latency = round((time.perf_counter() - query_start) * 1000, 2)

                # --- STEP E: GENERATION EVALUATION ---
                faithfulness = None
                answer_relevance = None
                refusal_correct = None
                judge_reasoning = None

                if run_generation_eval:
                    if not item.answerable:
                        refusal_correct = GenerationJudge.evaluate_refusal(generated_answer)
                        faithfulness = 1.0 if refusal_correct else 0.0
                        answer_relevance = 1.0 if refusal_correct else 0.0
                        judge_reasoning = "Negative test: Refusal evaluated against zero-retrieval refusal policy."
                    else:
                        faithfulness, judge_reasoning = await self.judge.evaluate_faithfulness(
                            context_chunks=[c.text for c in retrieved_chunks],
                            generated_answer=generated_answer,
                        )
                        answer_relevance, _ = GenerationJudge.evaluate_answer_relevance(
                            reference_answer=item.reference_answer,
                            generated_answer=generated_answer,
                        )

                # --- STEP F: RECORD RESULT ITEM ---
                result_item = EvaluationResultItem(
                    evaluation_run_id=eval_run.id,
                    query_id=item.id,
                    query=item.query,
                    category=item.category,
                    answerable=item.answerable,
                    expected_chunk_ids=item.expected_chunk_ids,
                    reference_answer=item.reference_answer,
                    retrieved_chunk_ids=retrieved_chunk_ids,
                    retrieval_scores=retrieval_scores,
                    generated_answer=generated_answer,
                    citations=citations,
                    recall_at_1=ir_metrics["recall_at_1"],
                    recall_at_3=ir_metrics["recall_at_3"],
                    recall_at_5=ir_metrics["recall_at_5"],
                    precision_at_1=ir_metrics["precision_at_1"],
                    precision_at_3=ir_metrics["precision_at_3"],
                    precision_at_5=ir_metrics["precision_at_5"],
                    reciprocal_rank=ir_metrics["reciprocal_rank"],
                    ndcg_at_5=ir_metrics["ndcg_at_5"],
                    faithfulness=faithfulness,
                    answer_relevance=answer_relevance,
                    refusal_correct=refusal_correct,
                    latency_ms=query_latency,
                    token_usage=token_usage,
                    judge_reasoning=judge_reasoning,
                )
                self.session.add(result_item)
                result_items.append(result_item)

                # Item summary for aggregation
                metric_row = {
                    "answerable": item.answerable,
                    "recall_at_1": ir_metrics["recall_at_1"],
                    "recall_at_3": ir_metrics["recall_at_3"],
                    "recall_at_5": ir_metrics["recall_at_5"],
                    "precision_at_1": ir_metrics["precision_at_1"],
                    "precision_at_3": ir_metrics["precision_at_3"],
                    "precision_at_5": ir_metrics["precision_at_5"],
                    "reciprocal_rank": ir_metrics["reciprocal_rank"],
                    "ndcg_at_5": ir_metrics["ndcg_at_5"],
                    "faithfulness": faithfulness,
                    "answer_relevance": answer_relevance,
                    "refusal_correct": refusal_correct,
                    "latency_ms": query_latency,
                }
                item_metrics_list.append(metric_row)

            # --- STEP G: AGGREGATE SUMMARY ---
            summary = IRMetricsCalculator.aggregate_metrics(item_metrics_list)
            summary["retrieval_mode"] = retrieval_mode or getattr(self.retrieval, "default_mode", "dense")
            summary["reranker_enabled"] = bool(reranker_enabled)
            summary["reranker_model"] = getattr(settings, "RERANKER_MODEL", "ms-marco-MiniLM-L-6-v2")
            summary["top_k"] = getattr(settings, "RETRIEVAL_FINAL_TOP_K", 5)
            summary["candidate_k"] = getattr(settings, "RETRIEVAL_CANDIDATE_K", 20)
            summary["rrf_k"] = getattr(settings, "RETRIEVAL_RRF_K", 60)
            summary["embedding_model"] = getattr(settings, "EMBEDDING_MODEL", "gemini-embedding-001")
            total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            eval_run.metrics_summary = summary

            eval_run.status = "COMPLETED"
            eval_run.duration_ms = total_duration_ms

            await self.session.commit()
            await self.session.refresh(eval_run)
            eval_run.items = result_items
            logger.info(
                f"Evaluation Run {eval_run.id} completed in {total_duration_ms}ms | "
                f"Recall@5={summary.get('recall_at_5')} | MRR={summary.get('mrr')} | "
                f"Faithfulness={summary.get('faithfulness')}"
            )
            return eval_run

        except Exception as e:
            await self.session.rollback()
            eval_run.status = "FAILED"
            eval_run.error_message = str(e)
            self.session.add(eval_run)
            await self.session.commit()
            logger.error(f"Evaluation Run {eval_run.id} failed: {e}", exc_info=True)
            raise


class ReportGenerator:
    """Generates human-readable Markdown and structured JSON evaluation reports."""

    @staticmethod
    def generate_markdown(eval_run: EvaluationRun, items: List[EvaluationResultItem]) -> str:
        s = eval_run.metrics_summary or {}
        created = eval_run.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if eval_run.created_at else "N/A"

        md = f"""# RAG Evaluation Benchmark Report
**Run ID:** `{eval_run.id}`  
**Dataset:** `{eval_run.dataset_name}`  
**Status:** `{eval_run.status}`  
**Executed At:** `{created}`  
**Total Queries:** {eval_run.total_queries}  
**Total Duration:** {eval_run.duration_ms:.1f}ms  

---

## 1. Executive Metrics Summary

| Metric | Score | Benchmark Target | Description |
| :--- | :--- | :--- | :--- |
| **Recall@5** | `{s.get('recall_at_5', 0.0):.4f}` | Baseline +/- 5% | Proportion of relevant chunks retrieved in top 5 |
| **Recall@3** | `{s.get('recall_at_3', 0.0):.4f}` | - | Proportion of relevant chunks retrieved in top 3 |
| **Recall@1** | `{s.get('recall_at_1', 0.0):.4f}` | - | First chunk recall |
| **Precision@5** | `{s.get('precision_at_5', 0.0):.4f}` | - | Context density in top 5 |
| **MRR** | `{s.get('mrr', 0.0):.4f}` | Baseline +/- 5% | Mean Reciprocal Rank of first relevant chunk |
| **NDCG@5** | `{s.get('ndcg_at_5', 0.0):.4f}` | - | Ranking quality discount factor |
| **Faithfulness** | `{s.get('faithfulness') if s.get('faithfulness') is not None else 'N/A'}` | >= 0.90 | LLM claim grounding in retrieved context |
| **Answer Relevance** | `{s.get('answer_relevance') if s.get('answer_relevance') is not None else 'N/A'}` | - | Semantic alignment with reference answer |
| **Refusal Accuracy** | `{s.get('refusal_accuracy', 0.0):.4f}` | 1.00 | Clean refusal rate on unanswerable queries |
| **Avg Query Latency** | `{s.get('avg_latency_ms', 0.0):.1f}ms` | <= 1500ms | Average turnaround time per query |

---

## 2. Per-Query Breakdown

| ID | Category | Query | Answerable | Recall@5 | MRR | Faithfulness | Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""
        for it in items:
            ans_str = "Yes" if it.answerable else "No (Negative)"
            f_str = f"{it.faithfulness:.2f}" if it.faithfulness is not None else "-"
            md += f"| `{it.query_id}` | `{it.category}` | {it.query[:45]}... | {ans_str} | `{it.recall_at_5:.2f}` | `{it.reciprocal_rank:.2f}` | {f_str} | {it.latency_ms:.0f}ms |\n"

        md += "\n---\n*Generated automatically by Avtaar RAG Evaluation Framework*\n"
        return md
