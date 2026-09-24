from abc import ABC, abstractmethod
import asyncio
import logging
import re
import time
from typing import Any, List, Optional

logger = logging.getLogger("app.services.retrieval.reranker")


class Reranker(ABC):
    """Abstract interface for candidate chunk reranking.
    Takes candidate chunks and a query, scoring and ordering them by relevance.
    """

    @abstractmethod
    async def rerank(
        self,
        query: str,
        chunks: List[Any],
        top_k: int = 5,
    ) -> List[Any]:
        """Reranks candidate chunks. Returns the top_k most relevant chunks."""
        pass


class NoOpReranker(Reranker):
    """Pass-through reranker preserving candidate fusion order."""

    async def rerank(
        self,
        query: str,
        chunks: List[Any],
        top_k: int = 5,
    ) -> List[Any]:
        return chunks[:top_k]


class HeuristicReranker(Reranker):
    """Lightweight, CPU-only semantic & exact-match cross-scoring reranker.
    Computes term coverage, keyword density, and phrase alignment without heavy external models.
    """

    async def rerank(
        self,
        query: str,
        chunks: List[Any],
        top_k: int = 5,
    ) -> List[Any]:
        if not chunks:
            return []

        query_terms = [t.lower() for t in re.findall(r"\b[a-zA-Z0-9_\-]+\b", query) if len(t) > 1]
        clean_query = query.strip().lower()

        scored_chunks = []
        for chunk in chunks:
            text = (chunk.text or "").lower()

            # 1. Exact query match bonus
            exact_bonus = 1.0 if clean_query in text else 0.0

            # 2. Term coverage ratio
            matched_terms = sum(1 for term in query_terms if term in text)
            coverage_ratio = matched_terms / max(1, len(query_terms))

            # 3. Term frequency density
            term_freq = sum(text.count(term) for term in query_terms)
            density = min(1.0, term_freq / max(1, len(text.split())))

            # 4. Existing candidate score prior (from RRF or Dense)
            prior_score = getattr(chunk, "score", 0.0)

            # Combined heuristic rerank score
            rerank_score = (
                0.40 * coverage_ratio
                + 0.30 * exact_bonus
                + 0.15 * density
                + 0.15 * prior_score
            )

            # Attach metadata
            updated_metadata = {
                **(chunk.metadata or {}),
                "reranker": "heuristic",
                "reranker_score": round(rerank_score, 4),
                "term_coverage": round(coverage_ratio, 2),
            }
            chunk.metadata = updated_metadata
            scored_chunks.append((chunk, rerank_score))

        # Sort descending by rerank score, then by chunk_id string for determinism
        scored_chunks.sort(key=lambda x: (x[1], str(x[0].chunk_id)), reverse=True)

        return [c for c, _ in scored_chunks[:top_k]]


class CrossEncoderReranker(Reranker):
    """Deep learning cross-encoder reranker utilizing sentence-transformers.
    If sentence-transformers is unavailable or raises an error, gracefully falls back to HeuristicReranker.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None
        self._load_failed = False
        self._fallback = HeuristicReranker()

    def _get_model(self):
        if self._model is None and not self._load_failed:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
                logger.info(f"Loaded CrossEncoder model: {self.model_name}")
            except Exception as e:
                logger.warning(
                    f"CrossEncoder '{self.model_name}' could not be loaded ({e}). "
                    f"Falling back to HeuristicReranker."
                )
                self._load_failed = True
        return self._model

    async def rerank(
        self,
        query: str,
        chunks: List[Any],
        top_k: int = 5,
    ) -> List[Any]:
        if not chunks:
            return []

        model = self._get_model()
        if model is None:
            return await self._fallback.rerank(query, chunks, top_k)

        try:
            pairs = [[query, chunk.text] for chunk in chunks]
            scores = await asyncio.to_thread(model.predict, pairs)

            scored_chunks = []
            for chunk, score in zip(chunks, scores):
                chunk.metadata = {
                    **(chunk.metadata or {}),
                    "reranker": "cross_encoder",
                    "reranker_score": round(float(score), 4),
                }
                scored_chunks.append((chunk, float(score)))

            scored_chunks.sort(key=lambda x: (x[1], str(x[0].chunk_id)), reverse=True)
            return [c for c, _ in scored_chunks[:top_k]]
        except Exception as err:
            logger.warning(f"CrossEncoder prediction failed: {err}. Falling back to HeuristicReranker.")
            return await self._fallback.rerank(query, chunks, top_k)


def get_reranker(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
) -> Reranker:
    """Factory creating configured Reranker instance."""
    p = (provider or "noop").lower()
    if p in ("noop", "none", "false"):
        return NoOpReranker()
    elif p in ("cross_encoder", "crossencoder"):
        return CrossEncoderReranker(model_name=model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2")
    elif p in ("heuristic", "keyword", "cpu"):
        return HeuristicReranker()
    else:
        logger.warning(f"Unknown reranker provider '{p}', defaulting to NoOpReranker")
        return NoOpReranker()
