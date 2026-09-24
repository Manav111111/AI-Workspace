from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional, Sequence
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService
from app.services.retrieval.dense import DenseRetriever
from app.services.retrieval.fusion import ReciprocalRankFusion
from app.services.retrieval.reranker import (
    CrossEncoderReranker,
    HeuristicReranker,
    NoOpReranker,
    Reranker,
    get_reranker,
)
from app.services.retrieval.sparse import SparseRetriever

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


class RetrievalService:
    """Production Retrieval Service executing configurable multi-tenant search.
    Supports:
        - DENSE: Vector similarity search via Qdrant
        - SPARSE: Lexical BM25 search over tenant document chunks
        - HYBRID: Dense + Sparse with Reciprocal Rank Fusion (RRF)
        - OPTIONAL RERANKING: Cross-Encoder or Heuristic cross-scoring
    
    SECURITY MANDATE: Every retrieval operation strictly mandates an authenticated company_id.
    """

    def __init__(
        self,
        qdrant_service: Optional[QdrantService] = None,
        embedding_service: Optional[EmbeddingService] = None,
        session: Optional[AsyncSession] = None,
        reranker: Optional[Reranker] = None,
        default_mode: Optional[str] = None,
    ):
        self.qdrant = qdrant_service or QdrantService()
        self.embedding = embedding_service or EmbeddingService()
        self.session = session
        self.default_mode = (default_mode or settings.RETRIEVAL_MODE).lower()

        # Initialize sub-components
        self.dense_retriever = DenseRetriever(
            qdrant_service=self.qdrant,
            embedding_service=self.embedding,
        )
        self.sparse_retriever = SparseRetriever(session=session)
        self.fusion = ReciprocalRankFusion(k=settings.RETRIEVAL_RRF_K)
        self.reranker = reranker or get_reranker(
            provider=settings.RERANKER_PROVIDER if settings.RERANKER_ENABLED else "noop",
            model_name=settings.RERANKER_MODEL,
        )

    async def retrieve(
        self,
        company_id: uuid.UUID,
        query: str,
        knowledge_base_id: Optional[uuid.UUID] = None,
        knowledge_base_ids: Optional[Sequence[uuid.UUID]] = None,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        mode: Optional[str] = None,
        reranker_enabled: Optional[bool] = None,
    ) -> List[RetrievedChunk]:
        """Retrieves tenant-isolated, relevant document chunks for the query.
        
        Args:
            company_id: Verified tenant ID (never trust client input).
            query: User search query.
            knowledge_base_id: Optional restriction to specific single KB.
            knowledge_base_ids: Optional restriction to a list of allowed KBs.
            top_k: Number of final chunks to return.
            score_threshold: Minimum score threshold.
            mode: Optional retrieval mode override ('dense', 'sparse', 'hybrid').
            reranker_enabled: Optional reranker override flag.
        """
        if not company_id:
            raise ValueError("company_id is strictly required for retrieval operations")

        clean_query = query.strip()
        if not clean_query:
            return []

        active_mode = (mode or self.default_mode).lower()
        k = top_k or settings.RAG_TOP_K
        threshold = score_threshold if score_threshold is not None else settings.RAG_SCORE_THRESHOLD
        use_reranker = reranker_enabled if reranker_enabled is not None else settings.RERANKER_ENABLED

        start_time = time.perf_counter()
        timings: Dict[str, float] = {}

        # Resolve knowledge base list
        kb_list = list(knowledge_base_ids) if knowledge_base_ids else ([knowledge_base_id] if knowledge_base_id else None)

        final_chunks: List[RetrievedChunk] = []

        if active_mode == "dense":
            t0 = time.perf_counter()
            dense_chunks = await self.dense_retriever.retrieve(
                company_id=company_id,
                query=clean_query,
                knowledge_base_id=knowledge_base_id,
                knowledge_base_ids=kb_list,
                top_k=k * 2 if use_reranker else k,
                score_threshold=threshold,
            )
            timings["dense_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            if use_reranker and dense_chunks:
                t_rerank = time.perf_counter()
                try:
                    final_chunks = await self.reranker.rerank(clean_query, dense_chunks, top_k=k)
                except Exception as err:
                    logger.warning(f"Reranker failed ({err}). Falling back to dense ranking.")
                    final_chunks = dense_chunks[:k]
                timings["rerank_ms"] = round((time.perf_counter() - t_rerank) * 1000, 2)
            else:
                final_chunks = dense_chunks[:k]

        elif active_mode == "sparse":
            t0 = time.perf_counter()
            sparse_chunks = await self.sparse_retriever.retrieve(
                company_id=company_id,
                query=clean_query,
                knowledge_base_ids=kb_list,
                top_k=k * 2 if use_reranker else k,
            )
            timings["sparse_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            if use_reranker and sparse_chunks:
                t_rerank = time.perf_counter()
                try:
                    final_chunks = await self.reranker.rerank(clean_query, sparse_chunks, top_k=k)
                except Exception as err:
                    logger.warning(f"Reranker failed ({err}). Falling back to sparse ranking.")
                    final_chunks = sparse_chunks[:k]
                timings["rerank_ms"] = round((time.perf_counter() - t_rerank) * 1000, 2)
            else:
                final_chunks = sparse_chunks[:k]

        elif active_mode == "hybrid":
            # 1. Fetch dense candidates
            dense_chunks: List[RetrievedChunk] = []
            t_dense = time.perf_counter()
            try:
                dense_chunks = await self.dense_retriever.retrieve(
                    company_id=company_id,
                    query=clean_query,
                    knowledge_base_id=knowledge_base_id,
                    knowledge_base_ids=kb_list,
                    top_k=settings.RETRIEVAL_DENSE_TOP_K,
                    score_threshold=threshold,
                )
            except Exception as e:
                logger.warning(f"Dense retrieval failed in hybrid mode ({e}). Continuing with sparse only.")
            timings["dense_ms"] = round((time.perf_counter() - t_dense) * 1000, 2)

            # 2. Fetch sparse candidates
            sparse_chunks: List[RetrievedChunk] = []
            t_sparse = time.perf_counter()
            try:
                sparse_chunks = await self.sparse_retriever.retrieve(
                    company_id=company_id,
                    query=clean_query,
                    knowledge_base_ids=kb_list,
                    top_k=settings.RETRIEVAL_SPARSE_TOP_K,
                )
            except Exception as e:
                logger.warning(f"Sparse retrieval failed in hybrid mode ({e}). Continuing with dense only.")
            timings["sparse_ms"] = round((time.perf_counter() - t_sparse) * 1000, 2)

            # 3. Fuse via Reciprocal Rank Fusion (RRF)
            t_fuse = time.perf_counter()
            fused_candidates = self.fusion.fuse(
                dense_chunks=dense_chunks,
                sparse_chunks=sparse_chunks,
                candidate_k=settings.RETRIEVAL_CANDIDATE_K,
            )
            timings["fusion_ms"] = round((time.perf_counter() - t_fuse) * 1000, 2)

            # 4. Optional Reranking
            if use_reranker and fused_candidates:
                t_rerank = time.perf_counter()
                try:
                    final_chunks = await self.reranker.rerank(clean_query, fused_candidates, top_k=k)
                except Exception as err:
                    logger.warning(f"Reranking failed ({err}). Falling back to RRF candidates.")
                    final_chunks = fused_candidates[:k]
                timings["rerank_ms"] = round((time.perf_counter() - t_rerank) * 1000, 2)
            else:
                final_chunks = fused_candidates[:k]

        else:
            raise ValueError(f"Unknown retrieval mode '{active_mode}'. Expected 'dense', 'sparse', or 'hybrid'.")

        total_retrieval_ms = round((time.perf_counter() - start_time) * 1000, 2)
        top_score = final_chunks[0].score if final_chunks else 0.0

        # Attach retrieval diagnostic timings to first chunk's metadata for telemetry
        if final_chunks:
            final_chunks[0].metadata = {
                **(final_chunks[0].metadata or {}),
                "retrieval_mode": active_mode,
                "timings": {**timings, "total_retrieval_ms": total_retrieval_ms},
            }

        logger.info(
            f"Retrieval complete [mode={active_mode}] for tenant {company_id}: retrieved {len(final_chunks)} chunks "
            f"(top score: {top_score:.4f}) in {total_retrieval_ms}ms (timings: {timings})"
        )

        return final_chunks


__all__ = [
    "RetrievedChunk",
    "RetrievalService",
    "DenseRetriever",
    "SparseRetriever",
    "ReciprocalRankFusion",
    "Reranker",
    "NoOpReranker",
    "HeuristicReranker",
    "CrossEncoderReranker",
    "get_reranker",
]
