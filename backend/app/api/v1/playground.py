import datetime
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import TenantContext, get_db, get_tenant_context
from app.services.playground.playground_service import PlaygroundService

router = APIRouter(prefix="/playground", tags=["AI Employee Playground"])


class PlaygroundSessionCreate(BaseModel):
    ai_employee_id: uuid.UUID
    session_name: Optional[str] = Field(None, max_length=100)
    config_overrides: Optional[Dict[str, Any]] = Field(default_factory=dict)


class PlaygroundSessionResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    user_id: uuid.UUID
    ai_employee_id: uuid.UUID
    session_name: str
    config_snapshot: Dict[str, Any]
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class PlaygroundMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class PlaygroundCompareRequest(BaseModel):
    ai_employee_id: uuid.UUID
    test_queries: List[str] = Field(..., min_length=1, max_length=5)
    config_a: Dict[str, Any]
    config_b: Dict[str, Any]



@router.post("/sessions", response_model=PlaygroundSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_playground_session(
    payload: PlaygroundSessionCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> PlaygroundSessionResponse:
    """Initializes a new playground session with an immutable configuration snapshot."""
    pg = await PlaygroundService.create_session(
        session=session,
        company_id=tenant.company_id,
        user_id=tenant.user_id,
        ai_employee_id=payload.ai_employee_id,
        session_name=payload.session_name,
        config_overrides=payload.config_overrides,
    )
    return PlaygroundSessionResponse.model_validate(pg)


@router.get("/sessions", response_model=List[PlaygroundSessionResponse])
async def list_playground_sessions(
    ai_employee_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[PlaygroundSessionResponse]:
    """Lists playground test sessions strictly scoped to the active tenant."""
    sessions = await PlaygroundService.list_sessions(
        session=session,
        company_id=tenant.company_id,
        ai_employee_id=ai_employee_id,
        limit=limit,
        offset=offset,
    )
    return [PlaygroundSessionResponse.model_validate(s) for s in sessions]


@router.get("/sessions/{id}")
async def get_playground_session(
    id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves session details and its message history with tenant isolation."""
    pg = await PlaygroundService.get_session(session, tenant.company_id, id)
    return {
        "session": PlaygroundSessionResponse.model_validate(pg),
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "citations": m.citations,
                "retrieval_debug": m.retrieval_debug,
                "prompt_debug": m.prompt_debug,
                "metrics": m.metrics,
                "trace_id": m.trace_id,
                "created_at": m.created_at.isoformat(),
            }
            for m in pg.messages
        ],
    }


@router.post("/sessions/{id}/messages")
async def send_playground_message(
    id: uuid.UUID,
    payload: PlaygroundMessageCreate,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Sends a test message, runs scoped retrieval & generation, and returns retrieval and prompt debug trees."""
    return await PlaygroundService.send_message(
        session=session,
        company_id=tenant.company_id,
        user_id=tenant.user_id,
        session_id=id,
        user_query=payload.content,
    )


@router.delete("/sessions/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playground_session(
    id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Deletes a playground test session."""
    await PlaygroundService.delete_session(session, tenant.company_id, id)


@router.post("/compare")
async def compare_configurations(
    payload: PlaygroundCompareRequest,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Executes test questions against two configurations side-by-side, measuring quality and cost differences."""
    return await PlaygroundService.compare_configurations(
        session=session,
        company_id=tenant.company_id,
        ai_employee_id=payload.ai_employee_id,
        test_queries=payload.test_queries,
        config_a=payload.config_a,
        config_b=payload.config_b,
    )
