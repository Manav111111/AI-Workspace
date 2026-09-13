import pytest
from app.services.embeddings import EmbeddingService
from app.services.invariants import validate_embedding_dimension_invariant
from app.services.qdrant_service import QdrantService


def test_embedding_dimension_invariant_success():
    """Verifies that the embedding dimension invariant passes when 384-d matches."""
    emb = EmbeddingService()
    assert emb.dimension == 384

    qdrant = QdrantService()
    assert qdrant._dim == 384

    # Must return True without raising RuntimeError
    assert validate_embedding_dimension_invariant(emb, qdrant) is True


def test_embedding_dimension_invariant_mismatch_fails_fast():
    """Verifies that dimension mismatch raises RuntimeError immediately (FAIL FAST)."""
    class MismatchedEmbeddingService:
        dimension = 512
        def embed_texts(self, texts):
            return [[0.0] * 512 for _ in texts]

    mismatched_emb = MismatchedEmbeddingService()
    qdrant = QdrantService()

    with pytest.raises(RuntimeError) as exc_info:
        validate_embedding_dimension_invariant(mismatched_emb, qdrant)

    assert "Embedding Dimension Invariant Violation" in str(exc_info.value)
