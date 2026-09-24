import datetime
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel


class EvaluationRun(BaseModel):
    """Evaluation Run model tracking a comprehensive benchmark execution.
    Strictly isolated by company_id and ai_employee_id.
    """
    __tablename__ = "evaluation_runs"

    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ai_employee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_base_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    dataset_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="golden_dataset",
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
        index=True,
    )
    total_queries: Mapped[int] = mapped_column(Integer, default=0)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)

    # Aggregated metrics summary
    # {
    #   "recall_at_1": 0.80, "recall_at_3": 0.90, "recall_at_5": 0.95,
    #   "precision_at_1": 0.80, "precision_at_3": 0.45, "precision_at_5": 0.32,
    #   "mrr": 0.88, "ndcg_at_5": 0.91,
    #   "faithfulness": 0.96, "answer_relevance": 0.92,
    #   "refusal_accuracy": 1.0, "avg_latency_ms": 420.5,
    #   "total_tokens": 12450, "estimated_cost_usd": 0.012
    # }
    metrics_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Baseline comparison results
    # {"passed": true, "degradations": [], "baseline_run_id": "..."}
    comparison_to_baseline: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    items: Mapped[List["EvaluationResultItem"]] = relationship(
        "EvaluationResultItem",
        back_populates="run",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="EvaluationResultItem.created_at",
    )


class EvaluationResultItem(BaseModel):
    """Detailed per-query evaluation result item."""
    __tablename__ = "evaluation_result_items"

    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    query_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general", index=True)
    answerable: Mapped[bool] = mapped_column(Boolean, default=True)

    # Ground truth
    expected_chunk_ids: Mapped[List[str]] = mapped_column(JSON, default=list)
    reference_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Observed execution results
    retrieved_chunk_ids: Mapped[List[str]] = mapped_column(JSON, default=list)
    retrieval_scores: Mapped[List[float]] = mapped_column(JSON, default=list)
    generated_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    citations: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)

    # IR Metrics
    recall_at_1: Mapped[float] = mapped_column(Float, default=0.0)
    recall_at_3: Mapped[float] = mapped_column(Float, default=0.0)
    recall_at_5: Mapped[float] = mapped_column(Float, default=0.0)
    precision_at_1: Mapped[float] = mapped_column(Float, default=0.0)
    precision_at_3: Mapped[float] = mapped_column(Float, default=0.0)
    precision_at_5: Mapped[float] = mapped_column(Float, default=0.0)
    reciprocal_rank: Mapped[float] = mapped_column(Float, default=0.0)
    ndcg_at_5: Mapped[float] = mapped_column(Float, default=0.0)

    # NLG Metrics
    faithfulness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    answer_relevance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    refusal_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Operational metrics
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    token_usage: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    judge_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Parent relationship
    run: Mapped["EvaluationRun"] = relationship("EvaluationRun", back_populates="items")
