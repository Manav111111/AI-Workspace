from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional
import uuid
from app.core.config import settings
from app.services.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService

logger = logging.getLogger("app.services.retrieval")


@dataclass
class RetrievedChunk:
    """Normalized internal representation of a retrieved document chunk."""
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    text: str
    score: float
    source: Optional[str] = None
    page_number: Optional[int] = None
    header_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Reranker(ABC):
    """Abstract interface for reranking candidate chunks.
    Keeps reranking pluggable without introducing immediate GPU dependencies.
    """

    @abstractmethod
    async def rerank(
        self,
        query: str,
        chunks: List[RetrievedChunk],
    ) -> List[RetrievedChunk]:
        pass


class NoOpReranker(Reranker):
    """Default no-op reranker preserving vector similarity ranking."""

    async def rerank(
        self,
        query: str,
        chunks: List[RetrievedChunk],
    ) -> List[RetrievedChunk]:
        return chunks


class RetrievalService:
    """Retrieval service executing tenant-scoped vector search in Qdrant.
    SECURITY MANDATE: Every retrieval operation mandates an authenticated company_id.
    """

    def __init__(
        self,
        qdrant_service: Optional[QdrantService] = None,
        embedding_service: Optional[EmbeddingService] = None,
        reranker: Optional[Reranker] = None,
    ):
        self.qdrant = qdrant_service or QdrantService()
        self.embedding = embedding_service or EmbeddingService()
        self.reranker = reranker or NoOpReranker()

    async def retrieve(
        self,
        company_id: uuid.UUID,
        query: str,
        knowledge_base_id: Optional[uuid.UUID] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """Retrieves tenant-isolated, relevant document chunks for the query.
        
        Args:
            company_id: Verified tenant ID (never trust client input).
            query: User search query.
            knowledge_base_id: Optional restriction to specific KB.
            top_k: Number of chunks to return (defaults to RAG_TOP_K).
            score_threshold: Minimum cosine similarity score (defaults to RAG_SCORE_THRESHOLD).
        """
        if not company_id:
            raise ValueError("company_id is strictly required for retrieval operations")

        clean_query = query.strip()
        if not clean_query:
            return []

        k = top_k or settings.RAG_TOP_K
        threshold = score_threshold if score_threshold is not None else settings.RAG_SCORE_THRESHOLD

        start_time = time.perf_counter()

        # 1. Generate query embedding vector (384-d normalized)
        query_vectors = self.embedding.embed_texts([clean_query])
        if not query_vectors:
            return []
        query_vector = query_vectors[0]

        # 2. Search Qdrant with MANDATORY company_id payload filter
        # Fetch slightly more candidates if score thresholding or reranking is applied
        fetch_limit = max(k * 2, 10)
        raw_results = self.qdrant.search(
            company_id=company_id,
            query_vector=query_vector,
            knowledge_base_id=knowledge_base_id,
            limit=fetch_limit,
        )

        # 3. Transform and apply score threshold
        candidate_chunks: List[RetrievedChunk] = []
        for r in raw_results:
            score = float(r.get("score", 0.0))
            if score < threshold:
                continue

            payload = r.get("payload", {})
            try:
                chunk_uuid = uuid.UUID(payload.get("chunk_id", str(r.get("id"))))
                doc_uuid = uuid.UUID(payload.get("document_id"))
                kb_uuid = uuid.UUID(payload.get("knowledge_base_id"))
            except (ValueError, TypeError):
                logger.warning(f"Malformed UUID in Qdrant payload: {payload}")
                continue

            candidate_chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_uuid,
                    document_id=doc_uuid,
                    knowledge_base_id=kb_uuid,
                    text=payload.get("content", payload.get("text", "")),
                    score=score,
                    source=payload.get("source"),
                    page_number=payload.get("page_number"),
                    header_path=payload.get("header_path"),
                    metadata=payload,
                )
            )

        # 4. Optional Reranking
        reranked_chunks = await self.reranker.rerank(clean_query, candidate_chunks)

        # 5. Top-K truncation
        final_chunks = reranked_chunks[:k]

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        top_score = final_chunks[0].score if final_chunks else 0.0
        logger.info(
            f"Retrieval complete for tenant {company_id}: retrieved {len(final_chunks)} chunks "
            f"(top score: {top_score:.3f}) in {elapsed_ms}ms"
        )

        return final_chunks
