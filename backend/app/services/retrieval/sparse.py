import logging
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.document_chunk import DocumentChunk
from app.repositories.document_chunk import DocumentChunkRepository
from app.services.retrieval.bm25 import BM25Index

logger = logging.getLogger("app.services.retrieval.sparse")


class TenantBM25CacheManager:
    """Thread-safe in-memory cache for tenant-scoped BM25 indices.
    Cache key: (company_id, tuple(sorted(kb_ids)))
    Ensures that multi-tenant boundaries are strictly respected and indices are reused across queries.
    """

    def __init__(self, ttl_seconds: int = 1800):
        self._cache: Dict[Tuple[str, Tuple[str, ...]], Tuple[float, BM25Index, Dict[str, DocumentChunk]]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def get(
        self, company_id: uuid.UUID, kb_ids: Optional[Sequence[uuid.UUID]]
    ) -> Optional[Tuple[BM25Index, Dict[str, DocumentChunk]]]:
        key = self._make_key(company_id, kb_ids)
        with self._lock:
            if key in self._cache:
                timestamp, index, chunk_map = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    return index, chunk_map
                else:
                    del self._cache[key]
        return None

    def set(
        self,
        company_id: uuid.UUID,
        kb_ids: Optional[Sequence[uuid.UUID]],
        index: BM25Index,
        chunk_map: Dict[str, DocumentChunk],
    ) -> None:
        key = self._make_key(company_id, kb_ids)
        with self._lock:
            self._cache[key] = (time.time(), index, chunk_map)

    def invalidate(self, company_id: Optional[uuid.UUID] = None) -> None:
        """Invalidate cache entries for a specific company or all companies."""
        with self._lock:
            if company_id is None:
                self._cache.clear()
            else:
                cid_str = str(company_id)
                keys_to_del = [k for k in self._cache.keys() if k[0] == cid_str]
                for k in keys_to_del:
                    del self._cache[k]

    def _make_key(
        self, company_id: uuid.UUID, kb_ids: Optional[Sequence[uuid.UUID]]
    ) -> Tuple[str, Tuple[str, ...]]:
        sorted_kbs = tuple(sorted([str(kb) for kb in kb_ids])) if kb_ids else ()
        return (str(company_id), sorted_kbs)


# Global process-wide cache manager
global_bm25_cache = TenantBM25CacheManager()


class SparseRetriever:
    """Sparse lexical retriever implementing tenant-isolated BM25 search over document chunks."""

    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        cache_manager: Optional[TenantBM25CacheManager] = None,
    ):
        self._injected_session = session
        self.cache = cache_manager or global_bm25_cache

    async def retrieve(
        self,
        company_id: uuid.UUID,
        query: str,
        knowledge_base_ids: Optional[Sequence[uuid.UUID]] = None,
        top_k: int = 10,
    ) -> List[Any]:
        """Retrieves chunks matching the query lexical terms using BM25.
        Returns a list of RetrievedChunk objects with sparse scores.
        """
        from app.services.retrieval import RetrievedChunk

        if not company_id:
            raise ValueError("company_id is strictly required for sparse retrieval operations")

        clean_query = query.strip()
        if not clean_query:
            return []

        # 1. Check in-memory cache
        cached = self.cache.get(company_id, knowledge_base_ids)
        if cached is not None:
            index, chunk_map = cached
        else:
            # 2. Build index from DB chunks
            index, chunk_map = await self._build_index_from_db(company_id, knowledge_base_ids)
            self.cache.set(company_id, knowledge_base_ids, index, chunk_map)

        if not index.chunk_ids:
            return []

        # 3. Perform BM25 lexical search
        matches = index.search(clean_query, top_k=top_k)
        if not matches:
            return []

        # Normalize BM25 scores (min-max or proportional scaling for visibility)
        max_score = matches[0][1] if matches else 1.0

        results: List[RetrievedChunk] = []
        for rank, (cid, score) in enumerate(matches, start=1):
            chunk = chunk_map.get(cid)
            if not chunk:
                continue

            # Store original sparse score and normalized score
            norm_score = round(score / max(1.0, max_score), 4)

            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    knowledge_base_id=chunk.knowledge_base_id,
                    text=chunk.content,
                    score=norm_score,
                    source=chunk.chunk_metadata.get("source"),
                    page_number=chunk.chunk_metadata.get("page_number"),
                    header_path=chunk.chunk_metadata.get("header_path"),
                    metadata={
                        **chunk.chunk_metadata,
                        "retrieval_type": "sparse",
                        "sparse_raw_score": score,
                        "sparse_rank": rank,
                    },
                )
            )

        return results

    async def _build_index_from_db(
        self,
        company_id: uuid.UUID,
        knowledge_base_ids: Optional[Sequence[uuid.UUID]] = None,
    ) -> Tuple[BM25Index, Dict[str, DocumentChunk]]:
        """Queries chunks from PostgreSQL/SQLite repository and constructs BM25 index."""
        if self._injected_session is not None:
            repo = DocumentChunkRepository(self._injected_session)
            chunks = await repo.list_by_knowledge_bases(company_id, knowledge_base_ids)
            return self._index_chunks(chunks)
        else:
            async with AsyncSessionLocal() as session:
                repo = DocumentChunkRepository(session)
                chunks = await repo.list_by_knowledge_bases(company_id, knowledge_base_ids)
                return self._index_chunks(chunks)

    def _index_chunks(
        self, chunks: Sequence[DocumentChunk]
    ) -> Tuple[BM25Index, Dict[str, DocumentChunk]]:
        chunk_ids: List[str] = []
        chunk_texts: List[str] = []
        chunk_map: Dict[str, DocumentChunk] = {}

        for c in chunks:
            cid_str = str(c.id)
            chunk_ids.append(cid_str)
            chunk_texts.append(c.content)
            chunk_map[cid_str] = c

        index = BM25Index(chunk_ids=chunk_ids, chunk_texts=chunk_texts)
        return index, chunk_map
