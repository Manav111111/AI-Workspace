import math
import pytest
from app.services.embeddings import EmbeddingService


def test_embedding_service_dimensions_and_norm():
    service = EmbeddingService()
    assert service.dimension == 384

    texts = [
        "Welcome to the multi-tenant AI Employee platform.",
        "Qdrant vector database indexes company knowledge.",
    ]
    vectors = service.generate_embeddings(texts)
    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384

    # Verify unit-length normalization
    norm0 = math.sqrt(sum(x * x for x in vectors[0]))
    assert abs(norm0 - 1.0) < 1e-4

    # Test query embedding
    q_vec = service.generate_query_embedding("company knowledge")
    assert len(q_vec) == 384
    norm_q = math.sqrt(sum(x * x for x in q_vec))
    assert abs(norm_q - 1.0) < 1e-4
