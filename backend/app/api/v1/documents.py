from typing import List
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_tenant_context, require_roles, TenantContext
from app.core.config import settings
from app.db.session import get_db
from app.models.membership import MembershipRole
from app.schemas.document import (
    DocumentChunkRead,
    DocumentRead,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from app.services.document import DocumentService
from app.services.rate_limit import distributed_rate_limiter

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document_direct(
    background_tasks: BackgroundTasks,
    knowledge_base_id: uuid.UUID = Query(...),
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Asynchronously upload and ingest a document. Returns HTTP 202 immediately while processing in background."""
    # Rate Limit enforcement (per tenant)
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
        knowledge_base_id=knowledge_base_id,
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


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> DocumentStatusResponse:
    """Get real-time ingestion stage and progress for an uploaded document."""
    service = DocumentService(session)
    return await service.get_document_status(
        company_id=tenant.company_id,
        document_id=document_id,
    )


@router.post("/{document_id}/retry", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_document_ingestion(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Re-enqueue a failed document for ingestion with fresh attempt counters."""
    service = DocumentService(session)
    doc, job = await service.retry_document_ingestion(
        company_id=tenant.company_id,
        document_id=document_id,
    )

    background_tasks.add_task(service.worker.process_job, job.id)

    return DocumentUploadResponse(
        id=doc.id,
        document_id=doc.id,
        job_id=job.id,
        status=doc.status.value,
        filename=doc.original_filename,
        file_size=doc.file_size,
        created_at=doc.created_at,
    )


@router.post("/{document_id}/cancel", response_model=DocumentStatusResponse)
async def cancel_document_ingestion(
    document_id: uuid.UUID,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> DocumentStatusResponse:
    """Cooperatively cancels a QUEUED document ingestion job."""
    service = DocumentService(session)
    return await service.cancel_document_ingestion(
        company_id=tenant.company_id,
        document_id=document_id,
    )


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> DocumentRead:
    """Get document details strictly within the tenant company boundary."""
    service = DocumentService(session)
    doc = await service.get_document(company_id=tenant.company_id, document_id=document_id)
    return DocumentRead.model_validate(doc)


@router.get("/{document_id}/chunks", response_model=List[DocumentChunkRead])
async def get_document_chunks(
    document_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db),
) -> List[DocumentChunkRead]:
    """Get extracted text chunks and metadata for a document."""
    service = DocumentService(session)
    chunks = await service.get_document_chunks(
        company_id=tenant.company_id,
        document_id=document_id,
    )
    return [DocumentChunkRead.model_validate(c) for c in chunks]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a document, its physical storage file, database chunks, Qdrant vectors, and invalidate BM25 cache."""
    service = DocumentService(session)
    await service.delete_document(company_id=tenant.company_id, document_id=document_id)
