import math
import uuid
import pytest
from app.models.ai_employee import AIEmployee, AIEmployeeStatus
from app.models.ai_employee_knowledge_base import AIEmployeeKnowledgeBase
from app.models.company import Company
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.services.evaluation.baseline import BaselineManager, RegressionCheckResult
from app.services.evaluation.dataset import DatasetValidator, GoldenQueryItem
from app.services.evaluation.judge import GenerationJudge
from app.services.evaluation.metrics import IRMetricsCalculator
from app.services.evaluation.runner import EvaluationRunner, ReportGenerator
from app.services.llm.mock_provider import MockLLMProvider
from app.services.retrieval import RetrievalService, RetrievedChunk


# ============================================================================
# 1. DATASET SCHEMA & VALIDATOR TESTS
# ============================================================================

def test_golden_dataset_validation_success():
    valid_data = [
        {
            "id": "item_1",
            "query": "What is annual leave?",
            "expected_chunk_ids": ["chk_1"],
            "reference_answer": "18 days.",
            "category": "hr",
            "answerable": True,
        },
        {
            "id": "neg_1",
            "query": "Unanswerable query?",
            "expected_chunk_ids": [],
            "reference_answer": None,
            "category": "out_of_scope",
            "answerable": False,
        }
    ]
    items = DatasetValidator.validate_items(valid_data)
    assert len(items) == 2
    assert items[0].id == "item_1"
    assert items[0].answerable is True
    assert items[1].id == "neg_1"
    assert items[1].answerable is False


def test_golden_dataset_validation_rejects_empty():
    with pytest.raises(ValueError, match="Dataset cannot be empty"):
        DatasetValidator.validate_items([])


def test_golden_dataset_validation_rejects_duplicate_ids():
    dupes = [
        {"id": "same_id", "query": "Q1", "expected_chunk_ids": ["c1"]},
        {"id": "same_id", "query": "Q2", "expected_chunk_ids": ["c2"]},
    ]
    with pytest.raises(ValueError, match="Duplicate query ID"):
        DatasetValidator.validate_items(dupes)


# ============================================================================
# 2. PURE IR METRICS MATHEMATICAL VERIFICATION
# ============================================================================

def test_recall_at_k():
    # Target: chk_1, chk_2 (2 expected)
    # Retrieved: chk_1, chk_9, chk_2, chk_3, chk_4
    retrieved = ["chk_1", "chk_9", "chk_2", "chk_3", "chk_4"]
    expected = ["chk_1", "chk_2"]

    # At K=1: only chk_1 is in retrieved[:1] -> 1/2 = 0.5
    assert IRMetricsCalculator.calculate_recall_at_k(retrieved, expected, 1) == 0.5

    # At K=2: chk_1 and chk_9 -> still 1/2 = 0.5
    assert IRMetricsCalculator.calculate_recall_at_k(retrieved, expected, 2) == 0.5

    # At K=3: chk_1, chk_9, chk_2 -> 2/2 = 1.0
    assert IRMetricsCalculator.calculate_recall_at_k(retrieved, expected, 3) == 1.0
    assert IRMetricsCalculator.calculate_recall_at_k(retrieved, expected, 5) == 1.0

    # No hits
    assert IRMetricsCalculator.calculate_recall_at_k(["chk_x", "chk_y"], expected, 2) == 0.0


def test_precision_at_k():
    retrieved = ["chk_1", "chk_9", "chk_2", "chk_3", "chk_4"]
    expected = ["chk_1", "chk_2"]

    # At K=1: 1 hit out of 1 -> 1.0
    assert IRMetricsCalculator.calculate_precision_at_k(retrieved, expected, 1) == 1.0

    # At K=2: 1 hit out of 2 -> 0.5
    assert IRMetricsCalculator.calculate_precision_at_k(retrieved, expected, 2) == 0.5

    # At K=5: 2 hits out of 5 -> 0.4
    assert IRMetricsCalculator.calculate_precision_at_k(retrieved, expected, 5) == 0.4


def test_reciprocal_rank():
    expected = ["chk_target"]

    # Ranked at position 1 -> RR = 1/1 = 1.0
    assert IRMetricsCalculator.calculate_reciprocal_rank(["chk_target", "other"], expected) == 1.0

    # Ranked at position 2 -> RR = 1/2 = 0.5
    assert IRMetricsCalculator.calculate_reciprocal_rank(["other", "chk_target"], expected) == 0.5

    # Ranked at position 4 -> RR = 1/4 = 0.25
    assert IRMetricsCalculator.calculate_reciprocal_rank(["a", "b", "c", "chk_target"], expected) == 0.25

    # Not found -> RR = 0.0
    assert IRMetricsCalculator.calculate_reciprocal_rank(["a", "b"], expected) == 0.0


def test_ndcg_at_k():
    expected = ["chk_1", "chk_2"]
    # Perfect ranking: chk_1 at pos 1, chk_2 at pos 2
    perfect = ["chk_1", "chk_2", "chk_3"]
    assert IRMetricsCalculator.calculate_ndcg_at_k(perfect, expected, 3) == 1.0

    # Suboptimal ranking: relevant items at pos 2 and 3
    suboptimal = ["chk_x", "chk_1", "chk_2"]
    ndcg_sub = IRMetricsCalculator.calculate_ndcg_at_k(suboptimal, expected, 3)
    assert 0.0 < ndcg_sub < 1.0


# ============================================================================
# 3. GENERATION JUDGE & REFUSAL TESTS
# ============================================================================

def test_refusal_evaluator():
    refusal_msg = "I am sorry, but I don't know. The specific details are not currently available in the company knowledge base."
    assert GenerationJudge.evaluate_refusal(refusal_msg) is True

    hallucinated_msg = "The secret bitcoin master key is 0x1234abcd5678."
    assert GenerationJudge.evaluate_refusal(hallucinated_msg) is False


def test_answer_relevance_evaluator():
    ref = "Full-time employees receive 18 days of annual leave and 6 casual days."
    gen_good = "Employees are entitled to 18 days annual leave and 6 days casual leave."
    gen_bad = "The office cafeteria serves pizza on Fridays."

    score_good, _ = GenerationJudge.evaluate_answer_relevance(ref, gen_good)
    score_bad, _ = GenerationJudge.evaluate_answer_relevance(ref, gen_bad)

    assert score_good > 0.60
    assert score_bad < 0.20


# ============================================================================
# 4. BASELINE & REGRESSION POLICY TESTS
# ============================================================================

def test_regression_gate_detects_drop(tmp_path):
    baseline_file = tmp_path / "test_baseline.json"
    mgr = BaselineManager(baseline_path=baseline_file)

    # Save initial baseline
    mgr.save_baseline(
        run_id="run_base",
        dataset_name="golden_v1",
        metrics_summary={
            "recall_at_5": 0.90,
            "mrr": 0.85,
            "faithfulness": 0.95,
            "refusal_accuracy": 1.0,
        }
    )

    # Test 1: Metrics slightly degraded within tolerance (drop <= 0.05) -> PASS
    mild_drop = {
        "recall_at_5": 0.88,  # drop of 0.02 <= 0.05
        "mrr": 0.84,         # drop of 0.01 <= 0.05
        "faithfulness": 0.94,# drop of 0.01 <= 0.05
        "refusal_accuracy": 1.0,
    }
    res_pass = mgr.check_regression(mild_drop)
    assert res_pass.passed is True
    assert len(res_pass.degradations) == 0

    # Test 2: Severe drop in recall@5 (> 0.05) -> FAIL
    severe_drop = {
        "recall_at_5": 0.80,  # drop of 0.10 > 0.05 tolerance!
        "mrr": 0.85,
        "faithfulness": 0.95,
        "refusal_accuracy": 1.0,
    }
    res_fail = mgr.check_regression(severe_drop)
    assert res_fail.passed is False
    assert len(res_fail.degradations) == 1
    assert res_fail.degradations[0]["metric"] == "recall_at_5"


def test_baseline_json_disk_loading_and_regression_enforcement():
    """Verify that baseline.json can be loaded from disk and regression check enforces gates."""
    from pathlib import Path
    base_path = Path("backend/data/baseline.json")
    if not base_path.exists():
        base_path = Path("data/baseline.json")

    if base_path.exists():
        mgr = BaselineManager(baseline_path=base_path)
        baseline = mgr.load_baseline()
        assert baseline is not None
        metrics = baseline.get("metrics", {})
        assert "recall_at_5" in metrics
        assert "mrr" in metrics

        # Check identical metrics -> must PASS
        pass_res = mgr.check_regression(metrics)
        assert pass_res.passed is True

        # Check degraded metrics -> must FAIL
        degraded = dict(metrics)
        degraded["recall_at_5"] = max(0.0, degraded["recall_at_5"] - 0.20)
        fail_res = mgr.check_regression(degraded)
        assert fail_res.passed is False
        assert any(d["metric"] == "recall_at_5" for d in fail_res.degradations)



# ============================================================================
# 5. END-TO-END EVALUATION RUNNER INTEGRATION TEST
# ============================================================================

class MockRetrievalForEval:
    """Mock Retrieval Service returning deterministic chunks matching test expectations."""
    def __init__(self, target_chunk_id: str):
        self.target_chunk_id = target_chunk_id

    async def retrieve(self, company_id, query, knowledge_base_ids=None, top_k=5, *args, **kwargs):
        if "unanswerable" in query.lower() or "secret" in query.lower():

            return []
        return [
            RetrievedChunk(
                chunk_id=uuid.UUID(self.target_chunk_id),
                document_id=uuid.uuid4(),
                knowledge_base_id=uuid.uuid4(),
                text="Employees receive 18 days of annual leave and 6 days casual leave per year.",
                score=0.88,
                source="HR_Policy.pdf",
                page_number=1,
            )
        ]


@pytest.mark.asyncio
async def test_evaluation_runner_e2e(db_session):
    # Setup test company and employee
    comp = Company(name="Eval Test Corp", slug="eval-test-corp")
    db_session.add(comp)
    await db_session.flush()

    emp = AIEmployee(
        company_id=comp.id,
        name="Eval Maya",
        role="HR Evaluator",
        status=AIEmployeeStatus.ACTIVE,
    )
    db_session.add(emp)
    await db_session.flush()

    # Create test knowledge base and assignment
    kb = KnowledgeBase(company_id=comp.id, name="HR KB")
    db_session.add(kb)
    await db_session.flush()

    rel = AIEmployeeKnowledgeBase(ai_employee_id=emp.id, knowledge_base_id=kb.id)
    db_session.add(rel)
    await db_session.commit()

    chunk_uuid = str(uuid.uuid4())
    mock_retrieval = MockRetrievalForEval(target_chunk_id=chunk_uuid)
    mock_llm = MockLLMProvider(model="mock-gemini")

    runner = EvaluationRunner(
        session=db_session,
        retrieval_service=mock_retrieval,
        llm_provider=mock_llm,
    )

    test_dataset = [
        GoldenQueryItem(
            id="test_001",
            query="What is annual leave entitlement?",
            expected_chunk_ids=[chunk_uuid],
            reference_answer="18 days annual leave",
            category="leave",
            answerable=True,
        ),
        GoldenQueryItem(
            id="test_002",
            query="What is the secret acquisition target?",
            expected_chunk_ids=[],
            reference_answer=None,
            category="negative",
            answerable=False,
        )
    ]

    eval_run = await runner.run_evaluation(
        company_id=comp.id,
        ai_employee_id=emp.id,
        dataset=test_dataset,
        dataset_name="unit_test_dataset",
        run_generation_eval=True,
    )

    assert eval_run.status == "COMPLETED"
    assert eval_run.total_queries == 2
    metrics = eval_run.metrics_summary
    assert "recall_at_5" in metrics
    assert "mrr" in metrics
    assert "refusal_accuracy" in metrics
    # Query 1 had target at rank 1 -> recall=1.0, mrr=1.0
    assert metrics["recall_at_5"] == 1.0
    assert metrics["mrr"] == 1.0

    # Check report generation
    md_report = ReportGenerator.generate_markdown(eval_run, eval_run.items)
    assert "# RAG Evaluation Benchmark Report" in md_report
    assert "Recall@5" in md_report
