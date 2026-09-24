import math
from typing import Any, Dict, List, Set


def _is_match(retrieved: str, expected_set: Set[str]) -> bool:
    """Checks if a retrieved chunk matches an expected chunk.
    Enforces exact equality, or substring matching only for UUID prefixes (>= 8 chars).
    """
    if retrieved in expected_set:
        return True
    if len(retrieved) >= 8:
        for exp in expected_set:
            if len(exp) >= 8 and (retrieved in exp or exp in retrieved):
                return True
    return False


class IRMetricsCalculator:
    """Pure mathematical information retrieval (IR) metrics calculator.
    Calculates Recall@K, Precision@K, MRR, and NDCG@K without third-party dependencies.
    """

    @staticmethod
    def calculate_recall_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
        """Recall@K = |Retrieved[:k] ∩ Expected| / |Expected|
        Returns 1.0 if expected is empty and retrieved is empty.
        """
        if not expected_ids:
            return 1.0 if not retrieved_ids[:k] else 0.0

        expected_set: Set[str] = set(expected_ids)
        retrieved_slice = retrieved_ids[:k]

        hits = sum(1 for r in retrieved_slice if _is_match(r, expected_set))
        return min(1.0, round(hits / len(expected_set), 4))

    @staticmethod
    def calculate_precision_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
        """Precision@K = |Retrieved[:k] ∩ Expected| / K"""
        if k <= 0:
            return 0.0
        if not expected_ids:
            return 0.0

        expected_set: Set[str] = set(expected_ids)
        retrieved_slice = retrieved_ids[:k]

        hits = sum(1 for r in retrieved_slice if _is_match(r, expected_set))
        return round(hits / k, 4)

    @staticmethod
    def calculate_reciprocal_rank(retrieved_ids: List[str], expected_ids: List[str]) -> float:
        """Calculates Reciprocal Rank (1/rank of first relevant chunk).
        Returns 0.0 if no relevant chunk is found.
        """
        if not expected_ids or not retrieved_ids:
            return 0.0

        expected_set: Set[str] = set(expected_ids)
        for rank, r in enumerate(retrieved_ids, start=1):
            if _is_match(r, expected_set):
                return round(1.0 / rank, 4)

        return 0.0

    @staticmethod
    def calculate_ndcg_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int = 5) -> float:
        """Normalized Discounted Cumulative Gain (NDCG@K) with binary relevance."""
        if not expected_ids or k <= 0:
            return 0.0

        expected_set: Set[str] = set(expected_ids)
        retrieved_slice = retrieved_ids[:k]

        # Calculate DCG@K
        dcg = 0.0
        for i, r in enumerate(retrieved_slice, start=1):
            is_relevant = 1.0 if _is_match(r, expected_set) else 0.0
            if is_relevant > 0:
                dcg += is_relevant / math.log2(i + 1)

        # Calculate Ideal DCG@K (IDCG)
        ideal_count = min(k, len(expected_set))
        if ideal_count == 0:
            return 0.0

        idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_count + 1))
        if idcg <= 0:
            return 0.0

        return round(dcg / idcg, 4)

    @classmethod
    def compute_query_ir_metrics(
        cls,
        retrieved_ids: List[str],
        expected_ids: List[str],
    ) -> Dict[str, float]:
        """Computes complete IR metrics package for a single test query."""
        return {
            "recall_at_1": cls.calculate_recall_at_k(retrieved_ids, expected_ids, 1),
            "recall_at_3": cls.calculate_recall_at_k(retrieved_ids, expected_ids, 3),
            "recall_at_5": cls.calculate_recall_at_k(retrieved_ids, expected_ids, 5),
            "precision_at_1": cls.calculate_precision_at_k(retrieved_ids, expected_ids, 1),
            "precision_at_3": cls.calculate_precision_at_k(retrieved_ids, expected_ids, 3),
            "precision_at_5": cls.calculate_precision_at_k(retrieved_ids, expected_ids, 5),
            "reciprocal_rank": cls.calculate_reciprocal_rank(retrieved_ids, expected_ids),
            "ndcg_at_5": cls.calculate_ndcg_at_k(retrieved_ids, expected_ids, 5),
        }

    @classmethod
    def aggregate_metrics(cls, query_metrics: List[Dict[str, Any]]) -> Dict[str, float]:
        """Averages metrics across a list of query results."""
        if not query_metrics:
            return {
                "recall_at_1": 0.0, "recall_at_3": 0.0, "recall_at_5": 0.0,
                "precision_at_1": 0.0, "precision_at_3": 0.0, "precision_at_5": 0.0,
                "mrr": 0.0, "ndcg_at_5": 0.0, "refusal_accuracy": 0.0,
            }

        answerable_items = [m for m in query_metrics if m.get("answerable", True)]
        unanswerable_items = [m for m in query_metrics if not m.get("answerable", True)]

        summary: Dict[str, float] = {}

        if answerable_items:
            for key in ["recall_at_1", "recall_at_3", "recall_at_5",
                        "precision_at_1", "precision_at_3", "precision_at_5",
                        "ndcg_at_5"]:
                values = [float(m.get(key, 0.0)) for m in answerable_items]
                summary[key] = round(sum(values) / len(values), 4)

            # MRR = Mean of reciprocal_rank
            rr_values = [float(m.get("reciprocal_rank", 0.0)) for m in answerable_items]
            summary["mrr"] = round(sum(rr_values) / len(rr_values), 4)
        else:
            for key in ["recall_at_1", "recall_at_3", "recall_at_5",
                        "precision_at_1", "precision_at_3", "precision_at_5",
                        "mrr", "ndcg_at_5"]:
                summary[key] = 0.0

        # Refusal accuracy for negative/unanswerable queries
        if unanswerable_items:
            refusals = [1.0 if m.get("refusal_correct", False) else 0.0 for m in unanswerable_items]
            summary["refusal_accuracy"] = round(sum(refusals) / len(refusals), 4)
        else:
            summary["refusal_accuracy"] = 1.0

        # Average latency
        latencies = [float(m.get("latency_ms", 0.0)) for m in query_metrics if "latency_ms" in m]
        summary["avg_latency_ms"] = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

        # Generation metrics averages if present
        faithfulness_vals = [
            float(m["faithfulness"]) for m in answerable_items
            if m.get("faithfulness") is not None
        ]
        if faithfulness_vals:
            summary["faithfulness"] = round(sum(faithfulness_vals) / len(faithfulness_vals), 4)
        else:
            summary["faithfulness"] = None

        relevance_vals = [
            float(m["answer_relevance"]) for m in answerable_items
            if m.get("answer_relevance") is not None
        ]
        if relevance_vals:
            summary["answer_relevance"] = round(sum(relevance_vals) / len(relevance_vals), 4)
        else:
            summary["answer_relevance"] = None

        return summary
