import asyncio
import json
import logging
from pathlib import Path
import sys
import uuid
from app.db.session import AsyncSessionLocal
from app.models.ai_employee import AIEmployee
from app.services.evaluation.baseline import BaselineManager
from app.services.evaluation.dataset import DatasetValidator
from app.services.evaluation.runner import EvaluationRunner, ReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("eval_cli")

DATASET_PATH = Path(__file__).parent / "data" / "golden_eval_dataset_hr.jsonl"
COMPANY_ID = uuid.UUID("1651e87c-8eae-4e10-82c4-83f791bbfac2")
EMPLOYEE_ID = uuid.UUID("f4900ae6-9f0c-436c-aaa8-b4beb0085d5b")


async def main():
    logger.info("Loading golden evaluation dataset...")
    dataset = DatasetValidator.load_jsonl(DATASET_PATH)
    logger.info(f"Loaded {len(dataset)} evaluation items.")

    async with AsyncSessionLocal() as session:
        runner = EvaluationRunner(session=session)
        logger.info(f"Running evaluation benchmark for Maya ({EMPLOYEE_ID}) in Company ({COMPANY_ID})...")

        eval_run = await runner.run_evaluation(
            company_id=COMPANY_ID,
            ai_employee_id=EMPLOYEE_ID,
            dataset=dataset,
            dataset_name="golden_eval_dataset_hr",
            run_generation_eval=True,
        )

        logger.info(f"Run completed with status: {eval_run.status} in {eval_run.duration_ms:.1f}ms")

        # Save as baseline if none exists
        baseline_mgr = BaselineManager()
        is_first = baseline_mgr.load_baseline() is None
        if is_first:
            logger.info("No baseline found. Establishing this run as the official baseline...")
            baseline_mgr.save_baseline(
                run_id=str(eval_run.id),
                dataset_name=eval_run.dataset_name,
                metrics_summary=eval_run.metrics_summary,
            )
            eval_run.is_baseline = True
            await session.commit()
            await session.refresh(eval_run)

        # Check regression against baseline
        reg_check = baseline_mgr.check_regression(eval_run.metrics_summary)
        print("\n" + "=" * 70)
        print("EVALUATION BENCHMARK METRICS SUMMARY")
        print("=" * 70)
        for k, v in eval_run.metrics_summary.items():
            print(f"  {k:20s}: {v}")
        print("=" * 70)
        print("REGRESSION STATUS:", reg_check.summary_message)
        print("=" * 70 + "\n")

        # Generate markdown report
        md = ReportGenerator.generate_markdown(eval_run, eval_run.items)
        report_file = Path(__file__).parent / "data" / f"eval_report_{eval_run.id}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(md)
        logger.info(f"Full Markdown evaluation report written to: {report_file}")

        # Also write latest report
        latest_report = Path(__file__).parent / "data" / "latest_eval_report.md"
        with open(latest_report, "w", encoding="utf-8") as f:
            f.write(md)
        logger.info(f"Latest report symlink/copy written to: {latest_report}")


if __name__ == "__main__":
    asyncio.run(main())
