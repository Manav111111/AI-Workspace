import logging
from typing import Any, Dict, List, Optional, Sequence
import uuid
from app.core.config import settings
from app.services.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService

logger = logging.getLogger("app.services.retrieval.dense")


class DenseRetriever:
    """Dense semantic retriever executing tenant-scoped vector search in Qdrant."""

    def __init__(
        self,
        qdrant_service: Optional[QdrantService] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        self.qdrant = qdrant_service or QdrantService()
        self.embedding = embedding_service or EmbeddingService()

    async def retrieve(
        self,
        company_id: uuid.UUID,
        query: str,
        knowledge_base_id: Optional[uuid.UUID] = None,
        knowledge_base_ids: Optional[Sequence[uuid.UUID]] = None,
        top_k: int = 10,
        score_threshold: Optional[float] = None,
    ) -> List[Any]:
        """Retrieves tenant-isolated chunks via dense vector similarity search in Qdrant."""
        from app.services.retrieval import RetrievedChunk

        if not company_id:
            raise ValueError("company_id is strictly required for dense retrieval operations")

        clean_query = query.strip()
        if not clean_query:
            return []

        threshold = score_threshold if score_threshold is not None else settings.RAG_SCORE_THRESHOLD

        # 1. Generate query embedding vector
        query_vectors = self.embedding.embed_texts([clean_query])
        if not query_vectors:
            return []
        query_vector = query_vectors[0]

        # 2. Search Qdrant with mandatory company_id payload filter
        raw_results = self.qdrant.search(
            company_id=company_id,
            query_vector=query_vector,
            knowledge_base_id=knowledge_base_id,
            knowledge_base_ids=knowledge_base_ids,
            limit=top_k,
        )

        # 3. Transform into normalized RetrievedChunk objects
        chunks: List[RetrievedChunk] = []
        for rank, r in enumerate(raw_results, start=1):
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

            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_uuid,
                    document_id=doc_uuid,
                    knowledge_base_id=kb_uuid,
                    text=payload.get("content", payload.get("text", "")),
                    score=round(score, 4),
                    source=payload.get("source"),
                    page_number=payload.get("page_number"),
                    header_path=payload.get("header_path"),
                    metadata={
                        **payload,
                        "retrieval_type": "dense",
                        "dense_score": round(score, 4),
                        "dense_rank": rank,
                    },
                )
            )

        return chunks
