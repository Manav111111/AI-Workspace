import logging
from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository
from app.services.chunking import ChunkingService
from app.services.embeddings import EmbeddingService
from app.services.parsers import get_parser_for_file
from app.services.qdrant_service import QdrantService
from app.services.storage import StorageService, LocalStorageService

logger = logging.getLogger("app.services.ingestion")


class IngestionService:
    """Orchestrates document parsing, cleaning, chunking, embedding, and vector storage."""

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

            # 4. Generate dense embeddings for all chunks in batch
            texts = [c.content for c in raw_chunks]
            embeddings = self.embedder.generate_embeddings(texts)

            # 5. Idempotency: Clean up any existing chunks or vectors for this document
            await self.chunk_repo.delete_by_document(company_id=company_id, document_id=document.id)
            self.qdrant.delete_document_vectors(company_id=company_id, document_id=document.id)

            # 6. Persist DocumentChunk records to database
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

            # 7. Upsert vectors with tenant payload metadata to Qdrant
            self.qdrant.upsert_chunks(
                company_id=company_id,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                chunk_records=created_chunk_records,
                embeddings=embeddings,
            )

            # 8. Mark document as PROCESSED
            document.status = DocumentStatus.PROCESSED
            document.error_message = None
            document.document_metadata = {
                **document.document_metadata,
                "total_chunks": len(created_chunk_records),
                "total_tokens": sum(c["token_count"] for c in created_chunk_records),
            }
            await self.doc_repo.update(document)
            await self.session.commit()
            await self.session.refresh(document)

            logger.info(
                f"Successfully processed document {document.id} ({len(created_chunk_records)} chunks) for company {company_id}"
            )
            return document

        except Exception as e:
            logger.error(
                f"Failed to process document {document.id} for company {company_id}: {str(e)}",
                exc_info=True,
            )
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            await self.doc_repo.update(document)
            await self.session.commit()
            await self.session.refresh(document)
            return document
