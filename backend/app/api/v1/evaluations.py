from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_tenant_context, require_roles, TenantContext
from app.db.session import get_db
from app.models.evaluation import EvaluationRun, EvaluationResultItem
from app.models.membership import MembershipRole
from app.schemas.evaluation import (
    EvaluationDetailResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
)
from app.services.evaluation.baseline import BaselineManager
from app.services.evaluation.dataset import DatasetValidator, GoldenQueryItem
from app.services.evaluation.runner import EvaluationRunner, ReportGenerator

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])

DEFAULT_DATASET_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "golden_eval_dataset_hr.jsonl"


@router.post("/run", response_model=EvaluationDetailResponse, status_code=status.HTTP_201_CREATED)
async def run_evaluation(
    payload: EvaluationRunRequest,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> EvaluationDetailResponse:
    """Trigger an automated RAG evaluation benchmark run against the tenant's AI Employee."""
    # Load dataset
    if payload.custom_dataset_items:
        dataset = DatasetValidator.validate_items(payload.custom_dataset_items)
    else:
        dataset = DatasetValidator.load_jsonl(DEFAULT_DATASET_FILE)

    runner = EvaluationRunner(session=session)
    eval_run = await runner.run_evaluation(
        company_id=tenant.company_id,
        ai_employee_id=payload.ai_employee_id,
        dataset=dataset,
        dataset_name=payload.dataset_name or "golden_eval_dataset_hr",
        run_generation_eval=payload.run_generation_eval,
        retrieval_mode=payload.retrieval_mode,
        reranker_enabled=payload.reranker_enabled,
    )


    # Check regression against baseline
    baseline_mgr = BaselineManager()
    regression_res = baseline_mgr.check_regression(eval_run.metrics_summary)
    eval_run.comparison_to_baseline = regression_res.model_dump()

    # If requested or if no baseline exists, save this run as baseline
    if payload.set_as_baseline or not baseline_mgr.load_baseline():
        baseline_mgr.save_baseline(
            run_id=str(eval_run.id),
            dataset_name=eval_run.dataset_name,
            metrics_summary=eval_run.metrics_summary,
        )
        eval_run.is_baseline = True

    await session.commit()
    await session.refresh(eval_run)

    # Load items eagerly
    items_stmt = select(EvaluationResultItem).where(
        EvaluationResultItem.evaluation_run_id == eval_run.id
    ).order_by(EvaluationResultItem.created_at)
    res = await session.execute(items_stmt)
    eval_run.items = list(res.scalars().all())

    return EvaluationDetailResponse.model_validate(eval_run)


@router.get("", response_model=List[EvaluationRunResponse])
async def list_evaluation_runs(
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
) -> List[EvaluationRunResponse]:
    """List historical evaluation benchmark runs for the tenant."""
    stmt = (
        select(EvaluationRun)
        .where(EvaluationRun.company_id == tenant.company_id)
        .order_by(EvaluationRun.created_at.desc())
        .limit(limit)
    )
    res = await session.execute(stmt)
    runs = res.scalars().all()
    return [EvaluationRunResponse.model_validate(r) for r in runs]


@router.get("/baseline", response_model=Dict[str, Any])
async def get_active_baseline(
    tenant: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Retrieve the active baseline metrics against which runs are compared."""
    baseline_mgr = BaselineManager()
    data = baseline_mgr.load_baseline()
    if not data:
        return {"status": "none", "message": "No baseline established yet."}
    return data


@router.get("/{run_id}", response_model=EvaluationDetailResponse)
async def get_evaluation_run_details(
    run_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> EvaluationDetailResponse:
    """Retrieve full details of an evaluation run including all query items."""
    stmt = (
        select(EvaluationRun)
        .where(EvaluationRun.id == run_id, EvaluationRun.company_id == tenant.company_id)
        .options(selectinload(EvaluationRun.items))
    )
    res = await session.execute(stmt)
    run_obj = res.scalar_one_or_none()
    if not run_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found.")

    return EvaluationDetailResponse.model_validate(run_obj)


@router.get("/{run_id}/report")
async def download_markdown_report(
    run_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Generate and return a formatted Markdown evaluation report."""
    stmt = (
        select(EvaluationRun)
        .where(EvaluationRun.id == run_id, EvaluationRun.company_id == tenant.company_id)
        .options(selectinload(EvaluationRun.items))
    )
    res = await session.execute(stmt)
    run_obj = res.scalar_one_or_none()
    if not run_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found.")

    md_report = ReportGenerator.generate_markdown(run_obj, run_obj.items)
    return Response(
        content=md_report,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=eval_report_{run_obj.id}.md"},
    )


@router.post("/{run_id}/set-baseline", response_model=EvaluationRunResponse)
async def set_run_as_baseline(
    run_id: uuid.UUID,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> EvaluationRunResponse:
    """Promote an existing successful evaluation run to be the official baseline."""
    stmt = select(EvaluationRun).where(
        EvaluationRun.id == run_id,
        EvaluationRun.company_id == tenant.company_id,
    )
    res = await session.execute(stmt)
    run_obj = res.scalar_one_or_none()
    if not run_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found.")

    if run_obj.status != "COMPLETED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only COMPLETED runs can become baseline.")

    baseline_mgr = BaselineManager()
    baseline_mgr.save_baseline(
        run_id=str(run_obj.id),
        dataset_name=run_obj.dataset_name,
        metrics_summary=run_obj.metrics_summary,
    )

    # Mark is_baseline flag
    run_obj.is_baseline = True
    await session.commit()
    await session.refresh(run_obj)
    return EvaluationRunResponse.model_validate(run_obj)
