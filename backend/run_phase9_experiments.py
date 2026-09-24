import asyncio
import json
import logging
import os
import time
from pathlib import Path
import uuid

# Ensure CWD is backend directory for SQLite relative database path
os.chdir(Path(__file__).resolve().parent)

from app.db.session import AsyncSessionLocal
from app.services.evaluation.dataset import DatasetValidator
from app.services.evaluation.runner import EvaluationRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("run_phase9_experiments")

DATASET_FILE = Path(__file__).resolve().parent / "data" / "golden_eval_dataset_hr.jsonl"
OUTPUT_FILE = Path(__file__).resolve().parent / "data" / "phase9_benchmark_comparison.json"

TARGET_COMPANY_ID = uuid.UUID("1651e87c-8eae-4e10-82c4-83f791bbfac2")
TARGET_EMPLOYEE_ID = uuid.UUID("f4900ae6-9f0c-436c-aaa8-b4beb0085d5b")


async def run_experiments():
    dataset = DatasetValidator.load_jsonl(DATASET_FILE)
    logger.info(f"Loaded {len(dataset)} queries from golden dataset {DATASET_FILE}")

    experiments = [
        {"name": "Dense", "mode": "dense", "reranker": False},
        {"name": "Sparse", "mode": "sparse", "reranker": False},
        {"name": "Hybrid", "mode": "hybrid", "reranker": False},
        {"name": "Hybrid + Reranker", "mode": "hybrid", "reranker": True},
    ]

    results_table = {}

    for exp in experiments:
        logger.info(f"\n{'='*60}\nRUNNING EXPERIMENT: {exp['name']} (mode={exp['mode']}, reranker={exp['reranker']})\n{'='*60}")
        async with AsyncSessionLocal() as session:
            runner = EvaluationRunner(session=session)
            t0 = time.perf_counter()
            eval_run = await runner.run_evaluation(
                company_id=TARGET_COMPANY_ID,
                ai_employee_id=TARGET_EMPLOYEE_ID,
                dataset=dataset,
                dataset_name=f"phase9_{exp['name'].lower().replace(' ', '_').replace('+', '')}",
                run_generation_eval=False,  # High-speed pure retrieval benchmark
                retrieval_mode=exp["mode"],
                reranker_enabled=exp["reranker"],
            )
            elapsed_s = round(time.perf_counter() - t0, 2)
            metrics = eval_run.metrics_summary
            metrics["experiment_wall_time_s"] = elapsed_s
            results_table[exp["name"]] = metrics
            logger.info(
                f"Completed {exp['name']}: Recall@5={metrics.get('recall_at_5'):.4f}, "
                f"Recall@1={metrics.get('recall_at_1'):.4f}, MRR={metrics.get('mrr'):.4f}, "
                f"NDCG@5={metrics.get('ndcg_at_5'):.4f}, AvgLatency={metrics.get('avg_latency_ms', 0.0):.1f}ms"
            )

    # Save to disk
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results_table, f, indent=2)
    logger.info(f"Saved Phase 9 benchmark comparison to {OUTPUT_FILE}")

    # Print formatted markdown table
    print("\n" + "="*80)
    print("PHASE 9 HYBRID RETRIEVAL BENCHMARK COMPARISON TABLE")
    print("="*80)
    cols = ["Metric", "Dense", "Sparse", "Hybrid", "Hybrid + Reranker"]
    print(f"| {' | '.join(cols)} |")
    print(f"|{'---|'*len(cols)}")
    metric_keys = [
        ("Recall@1", "recall_at_1", True),
        ("Recall@3", "recall_at_3", True),
        ("Recall@5", "recall_at_5", True),
        ("Precision@5", "precision_at_5", True),
        ("MRR", "mrr", False),
        ("NDCG@5", "ndcg_at_5", False),
        ("Refusal Accuracy", "refusal_accuracy", True),
        ("Avg Retrieval Latency", "avg_latency_ms", False),
    ]


    for label, key, is_pct in metric_keys:
        row = [label]
        for exp in experiments:
            val = results_table[exp["name"]].get(key, 0.0)
            if is_pct:
                formatted = f"{val * 100:.1f}%"
            elif "latency" in key:
                formatted = f"{val:.1f}ms"
            else:
                formatted = f"{val:.4f}"
            row.append(formatted)
        print(f"| {' | '.join(row)} |")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_experiments())
