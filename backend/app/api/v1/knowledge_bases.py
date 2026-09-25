from typing import List
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_tenant_context, require_roles, TenantContext
from app.core.config import settings
from app.db.session import get_db
from app.models.membership import MembershipRole
from app.schemas.document import DocumentRead, DocumentUploadResponse
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
)
from app.services.document import DocumentService
from app.services.knowledge_base import KnowledgeBaseService
from app.services.rate_limit import distributed_rate_limiter

router = APIRouter(prefix="/knowledge-bases", tags=["Knowledge Bases"])


@router.post("/", response_model=KnowledgeBaseRead, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> KnowledgeBaseRead:
    """Create a new company Knowledge Base. Requires OWNER or ADMIN role."""
    service = KnowledgeBaseService(session)
    kb = await service.create_knowledge_base(company_id=tenant.company_id, data=data)
    return KnowledgeBaseRead.model_validate(kb)


@router.get("/", response_model=List[KnowledgeBaseRead])
async def list_knowledge_bases(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[KnowledgeBaseRead]:
    """List all Knowledge Bases for the caller's authorized company."""
    service = KnowledgeBaseService(session)
    kbs = await service.list_knowledge_bases(company_id=tenant.company_id, skip=skip, limit=limit)
    return [KnowledgeBaseRead.model_validate(kb) for kb in kbs]


@router.get("/{kb_id}", response_model=KnowledgeBaseRead)
async def get_knowledge_base(
    kb_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> KnowledgeBaseRead:
    """Get details of a specific Knowledge Base."""
    service = KnowledgeBaseService(session)
    kb = await service.get_knowledge_base(company_id=tenant.company_id, kb_id=kb_id)
    return KnowledgeBaseRead.model_validate(kb)


@router.patch("/{kb_id}", response_model=KnowledgeBaseRead)
async def update_knowledge_base(
    kb_id: uuid.UUID,
    data: KnowledgeBaseUpdate,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> KnowledgeBaseRead:
    """Update Knowledge Base metadata or status."""
    service = KnowledgeBaseService(session)
    kb = await service.update_knowledge_base(
        company_id=tenant.company_id,
        kb_id=kb_id,
        data=data,
    )
    return KnowledgeBaseRead.model_validate(kb)


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: uuid.UUID,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a Knowledge Base, its documents, chunks, and Qdrant vectors."""
    service = KnowledgeBaseService(session)
    await service.delete_knowledge_base(company_id=tenant.company_id, kb_id=kb_id)


# Document endpoints under Knowledge Base
@router.post("/{kb_id}/documents", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    kb_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Asynchronously upload and ingest a document into the Knowledge Base. Returns HTTP 202 Accepted immediately."""
    # Tenant-level upload rate limit
    distributed_rate_limiter.check_limit(
        key=f"rl:ingest:upl:{tenant.company_id}",
        max_requests=settings.RATE_LIMIT_DOCUMENT_UPLOAD_PER_MINUTE,
        window_seconds=60,
        action_name="document upload",
        fail_mode="fail_open_with_local",
    )

    content = await file.read()
    service = DocumentService(session)
    doc, job = await service.upload_document_async(
        company_id=tenant.company_id,
        knowledge_base_id=kb_id,
        original_filename=file.filename or "unknown",
        content=content,
        mime_type=file.content_type,
    )

    # Dispatch to background task runner immediately
    background_tasks.add_task(service.worker.process_job, job.id)

    return DocumentUploadResponse(
        id=doc.id,
        document_id=doc.id,
        job_id=job.id,
        status=doc.status.value,
        filename=doc.filename,
        original_filename=doc.original_filename,
        file_size=doc.file_size,
        created_at=doc.created_at,
    )


@router.get("/{kb_id}/documents", response_model=List[DocumentRead])
async def list_documents_in_kb(
    kb_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[DocumentRead]:
    """List documents belonging to the specified Knowledge Base."""
    service = DocumentService(session)
    docs = await service.list_documents(
        company_id=tenant.company_id,
        knowledge_base_id=kb_id,
        skip=skip,
        limit=limit,
    )
    return [DocumentRead.model_validate(d) for d in docs]
