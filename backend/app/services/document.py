import os
from typing import List, Optional, Sequence
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository
from app.services.ingestion import IngestionService
from app.services.parsers import get_parser_for_file
from app.services.qdrant_service import QdrantService
from app.services.storage import StorageService, LocalStorageService


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
        self.kb_repo = KnowledgeBaseRepository(session)
        self.storage = storage_service or LocalStorageService()
        self.qdrant = qdrant_service or QdrantService()
        self.ingestion = IngestionService(
            session=session,
            storage_service=self.storage,
            qdrant_service=self.qdrant,
        )

    async def upload_and_process_document(
        self,
        company_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        original_filename: str,
        content: bytes,
        mime_type: Optional[str] = None,
    ) -> Document:
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

        # Verify parser exists
        get_parser_for_file(file_ext)

        # 5. Save file to storage
        storage_path = await self.storage.save(
            company_id=company_id,
            original_filename=original_filename,
            content=content,
        )

        # 6. Create Document record in DB with UPLOADED status
        doc = Document(
            company_id=company_id,
            knowledge_base_id=knowledge_base_id,
            filename=os.path.basename(storage_path),
            original_filename=original_filename,
            file_type=file_ext,
            mime_type=mime_type or "application/octet-stream",
            file_size=len(content),
            storage_path=storage_path,
            status=DocumentStatus.UPLOADED,
            document_metadata={},
        )
        created_doc = await self.doc_repo.create(doc)
        await self.session.commit()
        await self.session.refresh(created_doc)

        # 7. Trigger ingestion pipeline
        processed_doc = await self.ingestion.process_document(
            document_id=created_doc.id,
            company_id=company_id,
        )
        return processed_doc

    async def get_document(
        self,
        company_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> Document:
        doc = await self.doc_repo.get_by_tenant(company_id=company_id, document_id=document_id)
        if not doc:
            raise NotFoundException("Document not found in this company")
        return doc

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
        # Validate document ownership
        await self.get_document(company_id=company_id, document_id=document_id)
        return await self.chunk_repo.list_by_document(company_id=company_id, document_id=document_id)

    async def delete_document(
        self,
        company_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> None:
        doc = await self.get_document(company_id=company_id, document_id=document_id)

        # 1. Delete physical file from storage
        await self.storage.delete(doc.storage_path)

        # 2. Delete vectors from Qdrant
        self.qdrant.delete_document_vectors(company_id=company_id, document_id=doc.id)

        # 3. Delete Document record (cascades chunks)
        await self.doc_repo.delete(doc)
        await self.session.commit()
