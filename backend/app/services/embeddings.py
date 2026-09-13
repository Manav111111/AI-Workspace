from abc import ABC, abstractmethod
import hashlib
import math
import re
from typing import List, Optional
from app.core.config import settings


class EmbeddingProvider(ABC):
    """Abstract interface for generating vector embeddings."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        pass


class DeterministicCpuEmbeddingProvider(EmbeddingProvider):
    """Fast, deterministic, zero-dependency CPU embedding generator.
    Produces unit-normalized 384-dimensional dense vectors suitable for
    development, testing, and offline environments without GPU requirements.
    """

    def __init__(self, dim: int = 384):
        self._dimension = dim

    @property
    def dimension(self) -> int:
        return self._dimension

    def _hash_token(self, token: str) -> int:
        return int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)

    def _embed_single(self, text: str) -> List[float]:
        vec = [0.0] * self._dimension
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            vec[0] = 1.0
            return vec

        for idx, token in enumerate(tokens):
            h = self._hash_token(token)
            slot = h % self._dimension
            sign = 1.0 if ((h >> 4) & 1) else -1.0
            # Weight early tokens slightly more
            weight = 1.0 / math.log2(idx + 2)
            vec[slot] += sign * weight

        # L2 normalization to unit hypersphere
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        else:
            vec[0] = 1.0
        return vec

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        return self._embed_single(query)


class EmbeddingService:
    """Service facade for generating vector embeddings."""

    def __init__(self, provider: Optional[EmbeddingProvider] = None):
        self.provider = provider or DeterministicCpuEmbeddingProvider(
            dim=settings.EMBEDDING_DIMENSION
        )

    @property
    def dimension(self) -> int:
        return self.provider.dimension

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        return self.provider.embed_texts(texts)

    def generate_query_embedding(self, query: str) -> List[float]:
        return self.provider.embed_query(query)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return self.generate_embeddings(texts)

    def embed_query(self, query: str) -> List[float]:
        return self.generate_query_embedding(query)
