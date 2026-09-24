import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class EvaluationRunRequest(BaseModel):
    """Payload to trigger an automated RAG evaluation benchmark."""
    ai_employee_id: uuid.UUID = Field(..., description="Target AI Employee to evaluate")
    dataset_name: Optional[str] = Field("golden_eval_dataset_hr", description="Dataset identifier")
    custom_dataset_items: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Optional ad-hoc dataset items in memory instead of reading file"
    )
    run_generation_eval: bool = Field(True, description="Whether to execute LLM answer generation and judging")
    set_as_baseline: bool = Field(False, description="Whether to designate this run as the new baseline")
    retrieval_mode: Optional[str] = Field(None, description="Retrieval mode: dense | sparse | hybrid")
    reranker_enabled: Optional[bool] = Field(None, description="Whether to enable candidate reranking")



class EvaluationResultItemResponse(BaseModel):
    """Itemized query evaluation result schema."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    query_id: str
    query: str
    category: str
    answerable: bool
    expected_chunk_ids: List[str]
    retrieved_chunk_ids: List[str]
    retrieval_scores: List[float]
    generated_answer: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    precision_at_1: float
    precision_at_3: float
    precision_at_5: float
    reciprocal_rank: float
    ndcg_at_5: float
    faithfulness: Optional[float] = None
    answer_relevance: Optional[float] = None
    refusal_correct: Optional[bool] = None
    latency_ms: float
    judge_reasoning: Optional[str] = None


class EvaluationRunResponse(BaseModel):
    """Summary representation of an evaluation run."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    ai_employee_id: uuid.UUID
    knowledge_base_id: Optional[uuid.UUID] = None
    dataset_name: str
    status: str
    total_queries: int
    is_baseline: bool
    duration_ms: float
    metrics_summary: Dict[str, Any]
    comparison_to_baseline: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime.datetime


class EvaluationDetailResponse(EvaluationRunResponse):
    """Detailed evaluation run representation including all per-query results."""
    model_config = ConfigDict(from_attributes=True)

    items: List[EvaluationResultItemResponse] = Field(default_factory=list)

