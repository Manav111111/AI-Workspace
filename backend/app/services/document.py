import os
from typing import List, Optional, Sequence, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.models.ingestion_job import IngestionJob, IngestionJobStatus, IngestionStage
from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository
from app.repositories.ingestion_job import IngestionJobRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository
from app.schemas.document import DocumentStatusResponse
from app.services.ingestion import IngestionService
from app.services.parsers import get_parser_for_file
from app.services.qdrant_service import QdrantService
from app.services.retrieval import global_bm25_cache
from app.services.storage import StorageService, LocalStorageService
from app.workers.ingestion_worker import IngestionWorker


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        storage_service: Optional[StorageService] = None,
        qdrant_service: Optional[QdrantService] = None,
    ):
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.chunk_repo = DocumentChunkRepository(session)
        self.job_repo = IngestionJobRepository(session)
        self.kb_repo = KnowledgeBaseRepository(session)
        self.storage = storage_service or LocalStorageService()
        self.qdrant = qdrant_service or QdrantService()
        self.ingestion = IngestionService(
            session=session,
            storage_service=self.storage,
            qdrant_service=self.qdrant,
        )
        self.worker = IngestionWorker(
            storage_service=self.storage,
            qdrant_service=self.qdrant,
        )

    async def upload_document_async(
        self,
        company_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        original_filename: str,
        content: bytes,
        mime_type: Optional[str] = None,
    ) -> Tuple[Document, IngestionJob]:
        """Validates upload, stores file, creates Document and IngestionJob in QUEUED state,
        and returns immediately without blocking on chunking or embedding.
        """
        # 1. Verify target Knowledge Base belongs to this company
        kb = await self.kb_repo.get_by_tenant(company_id=company_id, kb_id=knowledge_base_id)
        if not kb:
            raise NotFoundException("Knowledge Base not found in this company")

        # 2. File validation: empty check
        if not content or len(content) == 0:
            raise ValidationException("Cannot upload an empty file")

        # 3. File validation: max size check
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise ValidationException(
                f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        # 4. File validation: parser support
        file_ext = os.path.splitext(original_filename)[1].lower().lstrip(".")
        if not file_ext:
            raise ValidationException("File has no extension")
        get_parser_for_file(file_ext)

        # 5. Check tenant queued job limit
        active_jobs = await self.job_repo.list_active_jobs_for_tenant(company_id)
        if len(active_jobs) >= settings.MAX_QUEUED_INGESTION_JOBS_PER_COMPANY:
            raise ValidationException(
                f"Tenant ingestion queue is full ({len(active_jobs)} active jobs). "
                "Please wait for ongoing jobs to complete."
            )

        # 6. Save file to storage
        storage_path = await self.storage.save(
            company_id=company_id,
            original_filename=original_filename,
            content=content,
        )

        # 7. Create Document record in DB with QUEUED status
        doc = Document(
            company_id=company_id,
            knowledge_base_id=knowledge_base_id,
            filename=os.path.basename(storage_path),
            original_filename=original_filename,
            file_type=file_ext,
            mime_type=mime_type or "application/octet-stream",
            file_size=len(content),
            storage_path=storage_path,
            status=DocumentStatus.QUEUED,
            document_metadata={},
        )
        created_doc = await self.doc_repo.create(doc)

        # 8. Create IngestionJob record
        job = IngestionJob(
            company_id=company_id,
            knowledge_base_id=knowledge_base_id,
            document_id=created_doc.id,
            status=IngestionJobStatus.QUEUED,
            max_attempts=settings.INGESTION_MAX_RETRIES,
            progress_percent=0,
            current_stage=IngestionStage.QUEUED.value,
        )
        created_job = await self.job_repo.create(job)

        await self.session.commit()
        await self.session.refresh(created_doc)
        await self.session.refresh(created_job)

        return created_doc, created_job

    async def upload_and_process_document(
        self,
        company_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        original_filename: str,
        content: bytes,
        mime_type: Optional[str] = None,
    ) -> Document:
        """Synchronous wrapper for backward compatibility. Creates job and awaits execution."""
        doc, job = await self.upload_document_async(
            company_id=company_id,
            knowledge_base_id=knowledge_base_id,
            original_filename=original_filename,
            content=content,
            mime_type=mime_type,
        )
        await self.worker.process_job(job.id)
        refreshed_doc = await self.get_document(company_id=company_id, document_id=doc.id)
        return refreshed_doc

    async def get_document(
        self,
        company_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Document:
        doc = await self.doc_repo.get_by_tenant(company_id=company_id, document_id=document_id)
        if not doc:
            raise NotFoundException("Document not found in this company")
        return doc

    async def get_document_status(
        self,
        company_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> DocumentStatusResponse:
        doc = await self.get_document(company_id=company_id, document_id=document_id)
        latest_job = await self.job_repo.get_latest_job_for_document(
            company_id=company_id, document_id=document_id
        )

        return DocumentStatusResponse(
            document_id=doc.id,
            job_id=latest_job.id if latest_job else None,
            status=doc.status.value,
            progress_percent=latest_job.progress_percent if latest_job else (100 if doc.status == DocumentStatus.PROCESSED else 0),
            current_stage=latest_job.current_stage if latest_job else (IngestionStage.COMPLETED.value if doc.status == DocumentStatus.PROCESSED else IngestionStage.QUEUED.value),
            error_code=latest_job.error_code if latest_job else None,
            error_message=latest_job.error_message or doc.error_message,
            attempt_count=latest_job.attempt_count if latest_job else 0,
            created_at=doc.created_at,
            updated_at=latest_job.updated_at if latest_job else doc.updated_at,
        )

    async def retry_document_ingestion(
        self,
        company_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Tuple[Document, IngestionJob]:
        """Creates a new IngestionJob for a FAILED document and resets status to QUEUED."""
        doc = await self.get_document(company_id=company_id, document_id=document_id)

        # Invariant: can only retry FAILED documents
        active_job = await self.job_repo.get_active_job_for_document(
            company_id=company_id, document_id=document_id
        )
        if active_job:
            raise ValidationException(
                f"Document is currently {active_job.status.value}. Cannot retry an active job."
            )

        if doc.status not in (DocumentStatus.FAILED, DocumentStatus.UPLOADED):
            raise ValidationException(
                f"Document is in status '{doc.status.value}'. Retry is only permitted for FAILED documents."
            )

        # Reset document status to QUEUED
        doc.status = DocumentStatus.QUEUED
        doc.error_message = None
        await self.doc_repo.update(doc)

        # Create new IngestionJob
        new_job = IngestionJob(
            company_id=company_id,
            knowledge_base_id=doc.knowledge_base_id,
            document_id=doc.id,
            status=IngestionJobStatus.QUEUED,
            max_attempts=settings.INGESTION_MAX_RETRIES,
            progress_percent=0,
            current_stage=IngestionStage.QUEUED.value,
        )
        created_job = await self.job_repo.create(new_job)

        await self.session.commit()
        await self.session.refresh(doc)
        await self.session.refresh(created_job)

        return doc, created_job

    async def cancel_document_ingestion(
        self,
        company_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> DocumentStatusResponse:
        """Cooperative cancellation of an active QUEUED ingestion job."""
        doc = await self.get_document(company_id=company_id, document_id=document_id)
        active_job = await self.job_repo.get_active_job_for_document(
            company_id=company_id, document_id=document_id
        )

        if not active_job:
            raise ValidationException("No active ingestion job found to cancel")

        if active_job.status == IngestionJobStatus.PROCESSING:
            raise ValidationException(
                "Ingestion job is currently PROCESSING and cannot be safely aborted mid-stage. "
                "Wait for completion or failure."
            )

        active_job.status = IngestionJobStatus.CANCELLED
        active_job.current_stage = "CANCELLED"
        active_job.error_message = "Ingestion cancelled by user"
        await self.job_repo.update(active_job)

        doc.status = DocumentStatus.FAILED
        doc.error_message = "Ingestion cancelled by user"
        await self.doc_repo.update(doc)

        await self.session.commit()
        return await self.get_document_status(company_id=company_id, document_id=document_id)

    async def list_documents(
        self,
        company_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Document]:
        # Validate KB ownership
        kb = await self.kb_repo.get_by_tenant(company_id=company_id, kb_id=knowledge_base_id)
        if not kb:
            raise NotFoundException("Knowledge Base not found in this company")

        return await self.doc_repo.list_by_knowledge_base(
            company_id=company_id,
            knowledge_base_id=knowledge_base_id,
            skip=skip,
            limit=limit,
        )

    async def get_document_chunks(
        self,
        company_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Sequence[DocumentChunk]:
        await self.get_document(company_id=company_id, document_id=document_id)
        return await self.chunk_repo.list_by_document(company_id=company_id, document_id=document_id)

    async def delete_document(
        self,
        company_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> None:
        doc = await self.get_document(company_id=company_id, document_id=document_id)

        # 1. Delete physical file from storage
        try:
            await self.storage.delete(doc.storage_path)
        except Exception as e:
            pass

        # 2. Delete vectors from Qdrant
        self.qdrant.delete_document_vectors(company_id=company_id, document_id=doc.id)

        # 3. Invalidate BM25 cache for tenant immediately
        global_bm25_cache.invalidate(company_id=company_id)

        # 4. Delete Document record (cascades chunks and jobs)
        await self.doc_repo.delete(doc)
        await self.session.commit()
