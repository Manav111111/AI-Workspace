from typing import List
import uuid
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_tenant_context, require_roles, TenantContext
from app.db.session import get_db
from app.models.membership import MembershipRole
from app.schemas.document import DocumentChunkRead, DocumentRead
from app.services.document import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document_direct(
    knowledge_base_id: uuid.UUID = Query(...),
    file: UploadFile = File(...),
    tenant: TenantContext = Depends(require_roles([MembershipRole.OWNER, MembershipRole.ADMIN])),
    session: AsyncSession = Depends(get_db),
) -> DocumentRead:
    """Upload and ingest a document directly via /api/v1/documents/upload."""
    content = await file.read()
    service = DocumentService(session)
    doc = await service.upload_and_process_document(
        company_id=tenant.company_id,
        knowledge_base_id=knowledge_base_id,
        original_filename=file.filename or "unknown",
        content=content,
        mime_type=file.content_type,
    )
    return DocumentRead.model_validate(doc)


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
    """Delete a document, its physical storage file, database chunks, and Qdrant vectors."""
    service = DocumentService(session)
    await service.delete_document(company_id=tenant.company_id, document_id=document_id)
