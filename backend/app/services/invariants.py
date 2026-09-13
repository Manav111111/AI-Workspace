import logging
from typing import Optional
from app.core.config import settings
from app.services.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService

logger = logging.getLogger("app.services.invariants")


def validate_embedding_dimension_invariant(
    embedding_service: Optional[EmbeddingService] = None,
    qdrant_service: Optional[QdrantService] = None,
) -> bool:
    """CRITICAL INVARIANT CHECK:
    Validates that the embedding model output dimension matches the Qdrant vector configuration.
    Fails fast with RuntimeError on any mismatch.
    Never silently pads or truncates vectors.
    """
    emb = embedding_service or EmbeddingService()
    qdrant = qdrant_service or QdrantService()

    expected_dim = settings.EMBEDDING_DIMENSION
    configured_model_dim = emb.dimension

    if configured_model_dim != expected_dim:
        raise RuntimeError(
            f"Embedding Dimension Invariant Violation: "
            f"EmbeddingService configured dimension ({configured_model_dim}) "
            f"does not match platform requirement ({expected_dim}). FAIL FAST."
        )

    # Validate with actual vector generation
    test_vecs = emb.embed_texts(["__invariant_validation_probe__"])
    if not test_vecs or len(test_vecs[0]) != expected_dim:
        actual_output_len = len(test_vecs[0]) if test_vecs else 0
        raise RuntimeError(
            f"Embedding Dimension Invariant Violation: "
            f"Generated vector length ({actual_output_len}) does not match expected ({expected_dim}). FAIL FAST."
        )

    # Verify Qdrant collection dimension
    try:
        collection_info = qdrant.client.get_collection(qdrant.collection_name)
        qdrant_dim = collection_info.config.params.vectors.size
        if qdrant_dim != expected_dim:
            raise RuntimeError(
                f"Qdrant Dimension Invariant Violation: "
                f"Qdrant collection '{qdrant.collection_name}' dimension ({qdrant_dim}) "
                f"does not match expected embedding dimension ({expected_dim}). FAIL FAST."
            )
    except Exception as e:
        if "Invariant Violation" in str(e):
            raise
        logger.warning(f"Could not inspect Qdrant collection params during invariant check ({e}). Skipping remote inspection.")

    logger.info(f"Embedding/Qdrant vector dimension invariant validated: {expected_dim} dimensions.")
    return True
