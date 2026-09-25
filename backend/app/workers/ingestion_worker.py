import asyncio
from datetime import datetime, timezone
import logging
import os
import re
from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
import app.db.session as db_session_module
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.models.ingestion_job import IngestionJob, IngestionJobStatus, IngestionStage
from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository
from app.repositories.ingestion_job import IngestionJobRepository
from app.services.chunking import ChunkingService
from app.services.embeddings import EmbeddingService
from app.services.invariants import validate_vectors_before_insert
from app.services.parsers import get_parser_for_file
from app.services.qdrant_service import QdrantService
from app.services.retrieval import global_bm25_cache
from app.services.storage import StorageService, LocalStorageService

logger = logging.getLogger("app.workers.ingestion")


def sanitize_error_message(msg: str) -> str:
    """Removes sensitive credentials from error messages before storing in DB or logging."""
    if not msg:
        return ""
    clean = re.sub(r"key=[^&\s'\"]+", "key=[REDACTED]", msg)
    for sensitive_key in [settings.GEMINI_API_KEY, settings.GOOGLE_API_KEY, settings.QDRANT_API_KEY]:
        if sensitive_key and sensitive_key in clean:
            clean = clean.replace(sensitive_key, "[REDACTED]")
    return clean


def classify_error(exc: Exception) -> tuple[str, bool]:
    """Classifies exception into a structured error code and determines whether it is retryable."""
    err_str = str(exc).lower()
    exc_type = type(exc).__name__

    # Non-retryable permanent data errors
    if "unsupported" in err_str or "no text content" in err_str or "cannot parse" in err_str:
        return "PARSER_ERROR", False
    if "validation" in err_str or "invalid format" in err_str:
        return "VALIDATION_ERROR", False
    if "file not found" in err_str or "nosuchfile" in err_str:
        return "STORAGE_FILE_NOT_FOUND", False

    # Retryable transient infrastructure errors
    if "429" in err_str or "rate limit" in err_str or "too many requests" in err_str:
        return "EMBEDDING_RATE_LIMIT", True
    if "503" in err_str or "unavailable" in err_str or "timeout" in err_str or "timed out" in err_str:
        return "EMBEDDING_TIMEOUT", True
    if "qdrant" in err_str or "connection refused" in err_str or "connection error" in err_str:
        return "VECTOR_STORE_UNAVAILABLE", True

    return "INTERNAL_PROCESSING_ERROR", True


class IngestionWorker:
    """Production asynchronous ingestion worker with stage-based progress tracking,
    idempotent vector upserts, tenant-scoped BM25 cache invalidation, and bounded retries.
    """

    def __init__(
        self,
        storage_service: Optional[StorageService] = None,
        embedding_service: Optional[EmbeddingService] = None,
        qdrant_service: Optional[QdrantService] = None,
        chunking_service: Optional[ChunkingService] = None,
        session_factory=None,
    ):
        self.storage = storage_service or LocalStorageService()
        self.embedder = embedding_service or EmbeddingService()
        self.qdrant = qdrant_service or QdrantService()
        self.chunker = chunking_service or ChunkingService()
        self._session_factory = session_factory

    @property
    def session_factory(self):
        return self._session_factory or db_session_module.AsyncSessionLocal

    async def process_job(self, job_id: uuid.UUID) -> Optional[IngestionJob]:
        """Processes a single ingestion job end-to-end with granular stage checkpoints and DB commits."""
        async with self.session_factory() as session:
            job_repo = IngestionJobRepository(session)
            doc_repo = DocumentRepository(session)
            chunk_repo = DocumentChunkRepository(session)

            job = await job_repo.get_by_id(job_id)
            if not job:
                logger.error(f"IngestionWorker: Job {job_id} not found")
                return None

            # Idempotency Guard: only QUEUED jobs can be transitioned to PROCESSING
            if job.status != IngestionJobStatus.QUEUED:
                logger.warning(
                    f"IngestionWorker: Job {job_id} is in status '{job.status}'. Skipping duplicate execution."
                )
                return job

            # Tenant Concurrency Check
            active_jobs = await job_repo.list_active_jobs_for_tenant(job.company_id)
            processing_count = sum(1 for j in active_jobs if j.status == IngestionJobStatus.PROCESSING)
            if processing_count >= settings.MAX_CONCURRENT_INGESTION_PER_COMPANY:
                logger.warning(
                    f"Tenant {job.company_id} reached max concurrent ingestion ({processing_count}). "
                    f"Job {job_id} remains QUEUED."
                )
                return job

            # Lock Job to PROCESSING
            job.status = IngestionJobStatus.PROCESSING
            job.started_at = datetime.now(timezone.utc)
            job.current_stage = IngestionStage.PARSING.value
            job.progress_percent = 10
            job.attempt_count += 1
            await job_repo.update(job)

            # Update Document status
            doc = await doc_repo.get_by_tenant(company_id=job.company_id, document_id=job.document_id)
            if doc:
                doc.status = DocumentStatus.PROCESSING
                doc.error_message = None
                await doc_repo.update(doc)

            await session.commit()
            await session.refresh(job)

            logger.info(
                f"IngestionWorker: Started job {job_id} (attempt {job.attempt_count}/{job.max_attempts}) "
                f"for doc {job.document_id} [tenant={job.company_id}]"
            )

        # Execute Pipeline stages (outside long DB lock)
        try:
            # Stage 1: PARSING (10%)
            if not doc:
                raise ValueError(f"Document {job.document_id} not found in database")

            file_bytes = await self.storage.get(doc.storage_path)
            parser = get_parser_for_file(doc.file_type)
            sections = parser.parse(file_bytes, doc.original_filename)

            # Stage 2: CLEANING (25%)
            await self._update_job_stage(job_id, IngestionStage.CLEANING, 25)

            # Stage 3: CHUNKING (40%)
            await self._update_job_stage(job_id, IngestionStage.CHUNKING, 40)
            raw_chunks = self.chunker.chunk_sections(
                sections=sections,
                company_id=job.company_id,
                knowledge_base_id=job.knowledge_base_id,
                document_id=doc.id,
            )

            if not raw_chunks:
                raise ValueError("No text content could be extracted or chunked from document")

            # Stage 4: EMBEDDING (60%)
            await self._update_job_stage(job_id, IngestionStage.EMBEDDING, 60)
            texts = [c.content for c in raw_chunks]
            embeddings = self.embedder.generate_embeddings(texts)

            # Stage 5: VECTOR_UPSERT (85%)
            await self._update_job_stage(job_id, IngestionStage.VECTOR_UPSERT, 85)
            validate_vectors_before_insert(embeddings, self.qdrant)

            # Persist Chunks in short DB transaction
            async with self.session_factory() as session:
                chunk_repo = DocumentChunkRepository(session)
                # Idempotency: remove any prior chunks and vectors
                await chunk_repo.delete_by_document(company_id=job.company_id, document_id=doc.id)
                self.qdrant.delete_document_vectors(company_id=job.company_id, document_id=doc.id)

                created_chunk_records = []
                for r_chunk in raw_chunks:
                    db_chunk = DocumentChunk(
                        company_id=job.company_id,
                        knowledge_base_id=job.knowledge_base_id,
                        document_id=doc.id,
                        chunk_index=r_chunk.chunk_index,
                        content=r_chunk.content,
                        token_count=r_chunk.token_count,
                        chunk_metadata=r_chunk.metadata,
                    )
                    session.add(db_chunk)
                    await session.flush()
                    await session.refresh(db_chunk)
                    created_chunk_records.append({
                        "id": db_chunk.id,
                        "chunk_index": db_chunk.chunk_index,
                        "content": db_chunk.content,
                        "token_count": db_chunk.token_count,
                        "chunk_metadata": db_chunk.chunk_metadata,
                    })
                await session.commit()

            # Upsert points to Qdrant Cloud
            self.qdrant.upsert_chunks(
                company_id=job.company_id,
                knowledge_base_id=job.knowledge_base_id,
                document_id=doc.id,
                chunk_records=created_chunk_records,
                embeddings=embeddings,
            )

            # Stage 6: INDEX_UPDATE (95%)
            await self._update_job_stage(job_id, IngestionStage.INDEX_UPDATE, 95)
            # Invalidate tenant in-memory BM25 cache so sparse retrieval refreshes immediately
            global_bm25_cache.invalidate(company_id=job.company_id)
            logger.info(f"Invalidated BM25 index cache for tenant {job.company_id}")

            # Stage 7: COMPLETED (100%)
            async with self.session_factory() as session:
                job_repo = IngestionJobRepository(session)
                doc_repo = DocumentRepository(session)
                live_job = await job_repo.get_by_id(job_id)
                live_doc = await doc_repo.get_by_tenant(company_id=job.company_id, document_id=job.document_id)

                if live_job:
                    live_job.status = IngestionJobStatus.COMPLETED
                    live_job.current_stage = IngestionStage.COMPLETED.value
                    live_job.progress_percent = 100
                    live_job.completed_at = datetime.now(timezone.utc)
                    live_job.error_code = None
                    live_job.error_message = None
                    await job_repo.update(live_job)

                if live_doc:
                    live_doc.status = DocumentStatus.PROCESSED
                    live_doc.error_message = None
                    live_doc.document_metadata = {
                        **(live_doc.document_metadata or {}),
                        "total_chunks": len(created_chunk_records),
                        "total_tokens": sum(c["token_count"] for c in created_chunk_records),
                        "embedding_provider": settings.EMBEDDING_PROVIDER,
                        "embedding_model": settings.EMBEDDING_MODEL,
                        "embedding_dimension": settings.EMBEDDING_DIMENSION,
                        "ingestion_completed_at": datetime.now(timezone.utc).isoformat(),
                    }
                    await doc_repo.update(live_doc)

                await session.commit()
                logger.info(f"IngestionWorker: Job {job_id} COMPLETED ({len(created_chunk_records)} chunks)")
                return live_job

        except Exception as exc:
            safe_error = sanitize_error_message(str(exc))
            error_code, is_retryable = classify_error(exc)
            logger.error(
                f"IngestionWorker: Job {job_id} encountered {error_code}: {safe_error}",
                exc_info=True,
            )

            async with self.session_factory() as session:
                job_repo = IngestionJobRepository(session)
                doc_repo = DocumentRepository(session)
                live_job = await job_repo.get_by_id(job_id)
                live_doc = await doc_repo.get_by_tenant(company_id=job.company_id, document_id=job.document_id)

                if live_job:
                    live_job.error_code = error_code
                    live_job.error_message = safe_error

                    if is_retryable and live_job.attempt_count < live_job.max_attempts:
                        # Schedule bounded retry with backoff
                        live_job.status = IngestionJobStatus.QUEUED
                        live_job.current_stage = IngestionStage.QUEUED.value
                        live_job.progress_percent = 0
                        backoff_delay = settings.INGESTION_RETRY_BACKOFF_SECONDS * (2 ** (live_job.attempt_count - 1))
                        logger.warning(
                            f"IngestionWorker: Re-queuing job {job_id} for retry #{live_job.attempt_count + 1} "
                            f"in {backoff_delay}s [error={error_code}]"
                        )
                        await job_repo.update(live_job)
                        await session.commit()

                        # Re-dispatch with backoff asynchronously
                        asyncio.create_task(self._delayed_reprocess(job_id, backoff_delay))
                        return live_job
                    else:
                        live_job.status = IngestionJobStatus.FAILED
                        live_job.completed_at = datetime.now(timezone.utc)
                        await job_repo.update(live_job)

                if live_doc:
                    live_doc.status = DocumentStatus.FAILED
                    live_doc.error_message = safe_error
                    await doc_repo.update(live_doc)

                await session.commit()
                return live_job

    async def _update_job_stage(self, job_id: uuid.UUID, stage: IngestionStage, percent: int) -> None:
        """Updates job stage and progress atomically in a fast transaction."""
        async with self.session_factory() as session:
            repo = IngestionJobRepository(session)
            job = await repo.get_by_id(job_id)
            if job and job.status == IngestionJobStatus.PROCESSING:
                job.current_stage = stage.value
                job.progress_percent = percent
                await repo.update(job)
                await session.commit()

    async def _delayed_reprocess(self, job_id: uuid.UUID, delay_seconds: float) -> None:
        await asyncio.sleep(delay_seconds)
        await self.process_job(job_id)

    async def recover_stale_jobs(self, timeout_seconds: int = 300, auto_reprocess: bool = False) -> int:
        """Finds jobs stuck in PROCESSING longer than threshold (indicates crashed process) and recovers them."""
        async with self.session_factory() as session:
            job_repo = IngestionJobRepository(session)
            stale_jobs = await job_repo.list_stale_processing_jobs(older_than_seconds=timeout_seconds)
            recovered_count = 0

            for job in stale_jobs:
                logger.warning(f"IngestionWorker: Found stale job {job.id} (started {job.started_at}). Recovering...")
                if job.attempt_count < job.max_attempts:
                    job.status = IngestionJobStatus.QUEUED
                    job.current_stage = IngestionStage.QUEUED.value
                    job.progress_percent = 0
                    job.error_message = f"Recovered from stale PROCESSING state after {timeout_seconds}s timeout"
                    job.error_code = "STALE_JOB_TIMEOUT"
                    await job_repo.update(job)
                    if auto_reprocess:
                        asyncio.create_task(self.process_job(job.id))
                else:
                    job.status = IngestionJobStatus.FAILED
                    job.completed_at = datetime.now(timezone.utc)
                    job.error_message = f"Job failed: exceeded timeout of {timeout_seconds}s across {job.max_attempts} attempts"
                    job.error_code = "STALE_JOB_EXHAUSTED"
                    await job_repo.update(job)

                recovered_count += 1

            if recovered_count > 0:
                await session.commit()
            return recovered_count
