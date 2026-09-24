import logging
import re
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository
from app.services.chunking import ChunkingService
from app.services.embeddings import EmbeddingService
from app.services.invariants import validate_vectors_before_insert
from app.services.parsers import get_parser_for_file
from app.services.qdrant_service import QdrantService
from app.services.storage import StorageService, LocalStorageService

logger = logging.getLogger("app.services.ingestion")


def sanitize_error_message(msg: str) -> str:
    """Removes sensitive credentials from error messages before storing in DB or logging."""
    if not msg:
        return ""
    clean = re.sub(r"key=[^&\s'\"]+", "key=[REDACTED]", msg)
    for sensitive_key in [settings.GEMINI_API_KEY, settings.GOOGLE_API_KEY, settings.QDRANT_API_KEY]:
        if sensitive_key and sensitive_key in clean:
            clean = clean.replace(sensitive_key, "[REDACTED]")
    return clean


class IngestionService:
    """Orchestrates document parsing, cleaning, chunking, embedding, and vector storage.
    Enforces strict failure states, credential-sanitized errors, and vector dimension invariants.
    """

    def __init__(
        self,
        session: AsyncSession,
        storage_service: Optional[StorageService] = None,
        embedding_service: Optional[EmbeddingService] = None,
        qdrant_service: Optional[QdrantService] = None,
        chunking_service: Optional[ChunkingService] = None,
    ):
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.chunk_repo = DocumentChunkRepository(session)
        self.storage = storage_service or LocalStorageService()
        self.embedder = embedding_service or EmbeddingService()
        self.qdrant = qdrant_service or QdrantService()
        self.chunker = chunking_service or ChunkingService()

    async def process_document(self, document_id: uuid.UUID, company_id: uuid.UUID) -> Document:
        """Processes an uploaded document end-to-end with idempotency and error tracking."""
        document = await self.doc_repo.get_by_tenant(company_id=company_id, document_id=document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found in company {company_id}")

        # Update status to PROCESSING
        document.status = DocumentStatus.PROCESSING
        document.error_message = None
        await self.doc_repo.update(document)
        await self.session.commit()

        try:
            # 1. Read binary content from storage
            file_bytes = await self.storage.get(document.storage_path)

            # 2. Select appropriate parser and extract structured sections
            parser = get_parser_for_file(document.file_type)
            sections = parser.parse(file_bytes, document.original_filename)

            # 3. Split sections into cleaned semantic chunks
            raw_chunks = self.chunker.chunk_sections(
                sections=sections,
                company_id=company_id,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
            )

            if not raw_chunks:
                raise ValueError("No text content could be extracted or chunked from document")

            # 4. Generate dense embeddings for all chunks in bounded batches
            texts = [c.content for c in raw_chunks]
            embeddings = self.embedder.generate_embeddings(texts)

            # 5. Invariant Check: Verify vector dimension matches Qdrant collection
            validate_vectors_before_insert(embeddings, self.qdrant)

            # 6. Idempotency: Clean up any existing chunks or vectors for this document
            await self.chunk_repo.delete_by_document(company_id=company_id, document_id=document.id)
            self.qdrant.delete_document_vectors(company_id=company_id, document_id=document.id)

            # 7. Persist DocumentChunk records to database
            created_chunk_records = []
            for r_chunk in raw_chunks:
                db_chunk = DocumentChunk(
                    company_id=company_id,
                    knowledge_base_id=document.knowledge_base_id,
                    document_id=document.id,
                    chunk_index=r_chunk.chunk_index,
                    content=r_chunk.content,
                    token_count=r_chunk.token_count,
                    chunk_metadata=r_chunk.metadata,
                )
                self.session.add(db_chunk)
                await self.session.flush()
                await self.session.refresh(db_chunk)
                created_chunk_records.append({
                    "id": db_chunk.id,
                    "chunk_index": db_chunk.chunk_index,
                    "content": db_chunk.content,
                    "token_count": db_chunk.token_count,
                    "chunk_metadata": db_chunk.chunk_metadata,
                })

            # 8. Upsert vectors with tenant payload metadata to Qdrant
            self.qdrant.upsert_chunks(
                company_id=company_id,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                chunk_records=created_chunk_records,
                embeddings=embeddings,
            )

            # 9. Mark document as PROCESSED
            document.status = DocumentStatus.PROCESSED
            document.error_message = None
            document.document_metadata = {
                **document.document_metadata,
                "total_chunks": len(created_chunk_records),
                "total_tokens": sum(c["token_count"] for c in created_chunk_records),
                "embedding_provider": settings.EMBEDDING_PROVIDER,
                "embedding_model": settings.EMBEDDING_MODEL,
                "embedding_dimension": settings.EMBEDDING_DIMENSION,
            }
            await self.doc_repo.update(document)
            await self.session.commit()
            await self.session.refresh(document)

            logger.info(
                f"Successfully processed document {document.id} ({len(created_chunk_records)} chunks) for company {company_id}"
            )
            return document

        except Exception as e:
            safe_error = sanitize_error_message(str(e))
            logger.error(
                f"Failed to process document {document.id} for company {company_id}: {safe_error}",
                exc_info=True,
            )
            document.status = DocumentStatus.FAILED
            document.error_message = safe_error
            await self.doc_repo.update(document)
            await self.session.commit()
            await self.session.refresh(document)
            return document
