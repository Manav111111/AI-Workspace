from abc import ABC, abstractmethod
import hashlib
import logging
import math
import random
import re
import time
from typing import List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger("app.services.embeddings")


class EmbeddingException(Exception):
    """Base exception for all embedding operations."""
    pass


class EmbeddingDimensionMismatchException(EmbeddingException):
    """Raised when generated embedding dimension does not match configured dimension."""
    pass


class EmbeddingAuthenticationException(EmbeddingException):
    """Raised when provider authentication fails."""
    pass


class EmbeddingRateLimitException(EmbeddingException):
    """Raised when provider rate limits are exceeded after retries."""
    pass


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


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock provider for unit tests, generating predictable unit-normalized vectors
    without consuming quota or requiring network access.
    """

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def _generate_vector(self, seed_val: int) -> List[float]:
        vec = [0.0] * self._dimension
        if self._dimension > 0:
            idx = seed_val % self._dimension
            vec[idx] = 1.0
        return vec

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        results = []
        for i, t in enumerate(texts):
            seed = sum(ord(c) for c in t) if t else i
            results.append(self._generate_vector(seed))
        return results

    def embed_query(self, query: str) -> List[float]:
        seed = sum(ord(c) for c in query) if query else 0
        return self._generate_vector(seed)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Production Google Gemini Embedding Provider using the official Gemini batchEmbedContents REST API.
    Features:
    - Native outputDimensionality control (384-dimensional dense vectors)
    - Strict vector length validation
    - Bounded batching
    - Exponential backoff retry on 429 and transient 5xx errors
    - Zero credential exposure in logs or exceptions
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        dimension: int = 384,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        batch_size: int = 20,
    ):
        if not api_key:
            raise EmbeddingAuthenticationException("Gemini API key is required and cannot be empty.")
        self.api_key = api_key
        self.model = model.replace("models/", "")
        self._dimension = dimension
        self.timeout = float(timeout_seconds)
        self.max_retries = max(1, int(max_retries))
        self.batch_size = max(1, min(int(batch_size), 50))
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def dimension(self) -> int:
        return self._dimension

    def _redact(self, message: str) -> str:
        """Sanitizes sensitive API keys from strings, URLs, or error messages."""
        if not message:
            return ""
        redacted = re.sub(r"key=[^&\s'\"]+", "key=[REDACTED]", message)
        if self.api_key and self.api_key in redacted:
            redacted = redacted.replace(self.api_key, "[REDACTED]")
        return redacted

    def _embed_batch_with_retry(self, texts: List[str]) -> List[List[float]]:
        """Sends a single bounded batch to Gemini batchEmbedContents with exponential backoff."""
        if not texts:
            return []

        url = f"{self.base_url}/models/{self.model}:batchEmbedContents?key={self.api_key}"
        requests_payload = [
            {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": t}]},
                "outputDimensionality": self._dimension,
            }
            for t in texts
        ]
        payload = {"requests": requests_payload}

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    raw_embeddings = data.get("embeddings", [])
                    if len(raw_embeddings) != len(texts):
                        raise EmbeddingException(
                            f"Gemini returned {len(raw_embeddings)} embeddings for {len(texts)} inputs."
                        )

                    vectors: List[List[float]] = []
                    for idx, emb_item in enumerate(raw_embeddings):
                        values = emb_item.get("values", [])
                        if len(values) != self._dimension:
                            raise EmbeddingDimensionMismatchException(
                                f"Gemini returned vector of dimension {len(values)}, "
                                f"but configured dimension is {self._dimension}."
                            )
                        # Normalize vector to unit length for cosine similarity
                        norm = math.sqrt(sum(v * v for v in values))
                        if norm > 0:
                            values = [v / norm for v in values]
                        vectors.append(values)

                    return vectors

                # Handle specific HTTP error codes
                if resp.status_code in (401, 403):
                    clean_err = self._redact(resp.text)
                    logger.error(f"Gemini API authentication failed: {clean_err}")
                    raise EmbeddingAuthenticationException(
                        f"Gemini API authentication failed (HTTP {resp.status_code}): {clean_err}"
                    )

                if resp.status_code == 429:
                    clean_err = self._redact(resp.text)
                    logger.warning(
                        f"Gemini embedding rate limited (429), attempt {attempt + 1}/{self.max_retries}. Backing off."
                    )
                    last_exception = EmbeddingRateLimitException(f"Gemini rate limit 429: {clean_err}")
                elif resp.status_code in (500, 502, 503, 504):
                    clean_err = self._redact(resp.text)
                    logger.warning(
                        f"Gemini service unavailable (HTTP {resp.status_code}), attempt {attempt + 1}/{self.max_retries}."
                    )
                    last_exception = EmbeddingException(f"Gemini server error {resp.status_code}: {clean_err}")
                else:
                    clean_err = self._redact(resp.text)
                    logger.error(f"Gemini embedding failed with status {resp.status_code}: {clean_err}")
                    raise EmbeddingException(f"Gemini returned HTTP {resp.status_code}: {clean_err}")

            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                clean_msg = self._redact(str(net_err))
                logger.warning(
                    f"Gemini network/timeout error, attempt {attempt + 1}/{self.max_retries}: {clean_msg}"
                )
                last_exception = EmbeddingException(f"Gemini connection timeout/network error: {clean_msg}")
            except (EmbeddingAuthenticationException, EmbeddingDimensionMismatchException):
                raise
            except Exception as ex:
                clean_msg = self._redact(str(ex))
                logger.error(f"Unexpected error calling Gemini embeddings: {clean_msg}")
                last_exception = EmbeddingException(f"Gemini unexpected error: {clean_msg}")

            # Exponential backoff before next attempt
            if attempt < self.max_retries - 1:
                backoff_delay = (2 ** attempt) * 1.0 + random.uniform(0.1, 0.5)
                time.sleep(backoff_delay)

        raise EmbeddingException(
            f"Gemini embedding batch failed after {self.max_retries} attempts: {last_exception}"
        )

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        all_vectors: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = texts[i : i + self.batch_size]
            batch_vectors = self._embed_batch_with_retry(chunk)
            all_vectors.extend(batch_vectors)

        return all_vectors

    def embed_query(self, query: str) -> List[float]:
        vectors = self.embed_texts([query])
        if not vectors:
            raise EmbeddingException("Failed to generate embedding for query.")
        return vectors[0]


class EmbeddingService:
    """Service facade for generating vector embeddings.
    CRITICAL RULE: Never silently falls back from configured provider to CPU in production.
    """

    def __init__(self, provider: Optional[EmbeddingProvider] = None):
        if provider:
            self.provider = provider
            return

        provider_name = (settings.EMBEDDING_PROVIDER or "cpu").lower()
        if provider_name == "gemini":
            gemini_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
            if not gemini_key:
                raise EmbeddingAuthenticationException(
                    "EMBEDDING_PROVIDER is 'gemini' but neither GEMINI_API_KEY nor GOOGLE_API_KEY is configured. "
                    "Silent fallback to CPU is forbidden. Fail fast."
                )
            self.provider = GeminiEmbeddingProvider(
                api_key=gemini_key,
                model=settings.EMBEDDING_MODEL,
                dimension=settings.EMBEDDING_DIMENSION,
                timeout_seconds=settings.EMBEDDING_TIMEOUT_SECONDS,
                max_retries=settings.EMBEDDING_MAX_RETRIES,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
            )
        elif provider_name == "cpu":
            self.provider = DeterministicCpuEmbeddingProvider(dim=settings.EMBEDDING_DIMENSION)
        elif provider_name == "mock":
            self.provider = MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
        else:
            raise ValueError(
                f"Unknown EMBEDDING_PROVIDER '{provider_name}'. Supported values are 'gemini', 'cpu', 'mock'."
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
