import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("app.services.evaluation.baseline")

DEFAULT_BASELINE_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "baseline.json"

DEFAULT_TOLERANCES = {
    "recall_at_5": 0.05,        # Max allowed drop: 5 percentage points
    "recall_at_3": 0.05,
    "recall_at_1": 0.08,
    "mrr": 0.05,
    "ndcg_at_5": 0.05,
    "faithfulness": 0.05,
    "refusal_accuracy": 0.00,   # Zero tolerance for hallucinating on negative queries
}


class RegressionCheckResult(BaseModel):
    """Outcome of comparing an evaluation run against a baseline."""
    passed: bool
    baseline_run_id: Optional[str] = None
    baseline_dataset: Optional[str] = None
    degradations: List[Dict[str, Any]] = Field(default_factory=list)
    improvements: List[Dict[str, Any]] = Field(default_factory=list)
    metrics_diff: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    summary_message: str


class BaselineManager:
    """Manages evaluation baselines and enforces regression gate policies."""

    def __init__(self, baseline_path: Optional[Path] = None):
        self.baseline_path = baseline_path or DEFAULT_BASELINE_PATH

    def load_baseline(self) -> Optional[Dict[str, Any]]:
        """Loads baseline metrics from disk if available."""
        if not self.baseline_path.exists():
            return None
        try:
            with open(self.baseline_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read baseline file at {self.baseline_path}: {e}")
            return None

    def save_baseline(
        self,
        run_id: str,
        dataset_name: str,
        metrics_summary: Dict[str, Any],
    ) -> Path:
        """Saves current run metrics as the new authoritative baseline."""
        self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "baseline_run_id": str(run_id),
            "dataset_name": dataset_name,
            "metrics": metrics_summary,
        }
        with open(self.baseline_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Saved new evaluation baseline from Run {run_id} to {self.baseline_path}")
        return self.baseline_path

    def check_regression(
        self,
        current_metrics: Dict[str, Any],
        tolerances: Optional[Dict[str, float]] = None,
    ) -> RegressionCheckResult:
        """Evaluates whether current metrics regress beyond allowed tolerances against the baseline.
        If no baseline exists, regression check passes and signals that this run should establish baseline.
        """
        baseline_data = self.load_baseline()
        if not baseline_data:
            return RegressionCheckResult(
                passed=True,
                summary_message="No existing baseline found. Current run establishes the initial baseline.",
            )

        baseline_metrics = baseline_data.get("metrics", {})
        baseline_run_id = baseline_data.get("baseline_run_id")
        baseline_dataset = baseline_data.get("dataset_name")

        active_tolerances = {**DEFAULT_TOLERANCES, **(tolerances or {})}

        degradations: List[Dict[str, Any]] = []
        improvements: List[Dict[str, Any]] = []
        metrics_diff: Dict[str, Dict[str, Any]] = {}

        for metric_name, tol in active_tolerances.items():
            base_val = baseline_metrics.get(metric_name)
            curr_val = current_metrics.get(metric_name)

            if base_val is None or curr_val is None:
                continue

            diff = round(float(curr_val) - float(base_val), 4)
            diff_entry = {
                "baseline": base_val,
                "current": curr_val,
                "diff": diff,
                "tolerance": tol,
            }
            metrics_diff[metric_name] = diff_entry

            # Check if degraded beyond tolerance
            if diff < -tol:
                degradations.append({
                    "metric": metric_name,
                    "baseline": base_val,
                    "current": curr_val,
                    "drop": abs(diff),
                    "max_allowed_drop": tol,
                })
            elif diff > 0.01:
                improvements.append({
                    "metric": metric_name,
                    "baseline": base_val,
                    "current": curr_val,
                    "gain": diff,
                })

        passed = len(degradations) == 0
        if passed:
            msg = (
                f"Regression gate PASSED: No metrics degraded beyond allowed tolerances "
                f"({len(improvements)} improvements detected vs baseline {baseline_run_id})."
            )
        else:
            deg_names = [d["metric"] for d in degradations]
            msg = (
                f"Regression gate FAILED: {len(degradations)} metric(s) degraded beyond tolerance: "
                f"{', '.join(deg_names)}."
            )

        return RegressionCheckResult(
            passed=passed,
            baseline_run_id=baseline_run_id,
            baseline_dataset=baseline_dataset,
            degradations=degradations,
            improvements=improvements,
            metrics_diff=metrics_diff,
            summary_message=msg,
        )
