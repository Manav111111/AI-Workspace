import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence, Tuple
import logging

logger = logging.getLogger("app.services.retrieval.bm25")

try:
    from rank_bm25 import BM25Okapi as ExternalBM25Okapi
    HAS_RANK_BM25 = True
except ImportError:
    HAS_RANK_BM25 = False


def tokenize_text(text: str) -> List[str]:
    """Tokenizes input text into normalized lowercased terms.
    Preserves alphanumeric codes, hyphenated identifiers, and words.
    """
    if not text:
        return []
    # Match alphanumeric words, including internal hyphens/underscores for product/policy codes
    tokens = re.findall(r"\b[a-zA-Z0-9_\-]+\b", text.lower())
    return [t for t in tokens if len(t) > 0]


class PurePythonBM25:
    """Pure Python Okapi BM25 implementation.
    Zero external dependencies. Guaranteed deterministic execution across all environments.
    Formula:
        score(D, Q) = sum(IDF(q) * (f(q, D) * (k1 + 1)) / (f(q, D) + k1 * (1 - b + b * (|D| / avgdl))))
    """

    def __init__(self, corpus: Sequence[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.doc_lens = [len(doc) for doc in corpus]
        self.avgdl = sum(self.doc_lens) / max(1, self.corpus_size)

        # Document frequencies for all terms
        self.doc_freqs: Dict[str, int] = Counter()
        self.doc_term_freqs: List[Counter] = []

        for doc in corpus:
            tf = Counter(doc)
            self.doc_term_freqs.append(tf)
            for term in tf.keys():
                self.doc_freqs[term] += 1

        # Precompute IDF values
        self.idf: Dict[str, float] = {}
        for term, df in self.doc_freqs.items():
            # Standard Lucene / Okapi BM25 IDF formulation
            self.idf[term] = math.log(1.0 + (self.corpus_size - df + 0.5) / (df + 0.5))

    def get_scores(self, query_tokens: List[str]) -> List[float]:
        scores = [0.0] * self.corpus_size
        if not query_tokens or self.corpus_size == 0:
            return scores

        query_counts = Counter(query_tokens)

        for i, tf in enumerate(self.doc_term_freqs):
            doc_len = self.doc_lens[i]
            len_norm = 1.0 - self.b + self.b * (doc_len / max(1.0, self.avgdl))

            doc_score = 0.0
            for term, _ in query_counts.items():
                if term not in tf:
                    continue
                term_freq = tf[term]
                term_idf = self.idf.get(term, 0.0)
                numerator = term_freq * (self.k1 + 1.0)
                denominator = term_freq + self.k1 * len_norm
                doc_score += term_idf * (numerator / denominator)

            scores[i] = doc_score

        return scores


class BM25Index:
    """Manages an in-memory BM25 index over a collection of text chunks."""

    def __init__(
        self,
        chunk_ids: List[str],
        chunk_texts: List[str],
        k1: float = 1.5,
        b: float = 0.75,
        use_external: bool = False,
    ):
        self.chunk_ids = chunk_ids
        self.chunk_texts = chunk_texts
        self.tokenized_corpus = [tokenize_text(text) for text in chunk_texts]
        self.k1 = k1
        self.b = b

        if use_external and HAS_RANK_BM25 and len(self.tokenized_corpus) > 0:
            self._engine = ExternalBM25Okapi(self.tokenized_corpus, k1=k1, b=b)
            self._is_external = True
        else:
            self._engine = PurePythonBM25(self.tokenized_corpus, k1=k1, b=b)
            self._is_external = False


    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Searches index with BM25, returning top-k (chunk_id, bm25_score) tuples."""
        if not self.chunk_ids:
            return []

        tokens = tokenize_text(query)
        if not tokens:
            return []

        scores = self._engine.get_scores(tokens)

        # Pair scores with chunk_ids
        scored_pairs: List[Tuple[str, float]] = []
        for i, score in enumerate(scores):
            if score > 0.0001:
                scored_pairs.append((self.chunk_ids[i], float(score)))

        # Sort descending by score, tie-breaking by chunk_id string for determinism
        scored_pairs.sort(key=lambda x: (x[1], x[0]), reverse=True)
        return scored_pairs[:top_k]
