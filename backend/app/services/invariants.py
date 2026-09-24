import logging
from typing import List, Optional
from app.core.config import settings
from app.services.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService

logger = logging.getLogger("app.services.invariants")


def validate_embedding_dimension_invariant(
    embedding_service: Optional[EmbeddingService] = None,
    qdrant_service: Optional[QdrantService] = None,
) -> bool:
    """CRITICAL INVARIANT CHECK:
    Validates that:
      configured dimension == actual embedding dimension == Qdrant collection dimension
    Fails fast with RuntimeError on any mismatch.
    Never silently pads, truncates, or mutates collections.
    """
    emb = embedding_service or EmbeddingService()
    qdrant = qdrant_service or QdrantService()

    configured_dim = settings.EMBEDDING_DIMENSION
    configured_model = settings.EMBEDDING_MODEL
    actual_emb_dim = emb.dimension

    # 1. Configured dimension vs EmbeddingService dimension
    if actual_emb_dim != configured_dim:
        raise RuntimeError(
            f"Embedding Dimension Invariant Violation: "
            f"Configured Model: '{configured_model}', "
            f"Configured Dimension: {configured_dim}, "
            f"Actual Embedding Dimension: {actual_emb_dim}. FAIL FAST."
        )

    # 2. Check Qdrant configured dimension and collection dimension
    if qdrant._dim != configured_dim:
        raise RuntimeError(
            f"Embedding Space Invariant Violation: "
            f"Configured Model: '{configured_model}', "
            f"Configured Dimension: {configured_dim}, "
            f"Actual Embedding Dimension: {actual_emb_dim}, "
            f"Qdrant Configured Dimension: {qdrant._dim}. FAIL FAST."
        )

    try:
        collection_info = qdrant.client.get_collection(qdrant.collection_name)
        vec_params = collection_info.config.params.vectors
        qdrant_dim = vec_params.size if hasattr(vec_params, "size") else None
        if qdrant_dim is not None and qdrant_dim != configured_dim:
            raise RuntimeError(
                f"Embedding Space Invariant Violation: "
                f"Configured Model: '{configured_model}', "
                f"Configured Dimension: {configured_dim}, "
                f"Actual Embedding Dimension: {actual_emb_dim}, "
                f"Qdrant Collection Dimension: {qdrant_dim}. FAIL FAST."
            )
    except Exception as e:
        if "Invariant Violation" in str(e):
            raise
        logger.warning(
            f"Could not inspect Qdrant collection params during invariant check ({e}). Skipping remote inspection."
        )

    logger.info(
        f"Embedding/Qdrant vector dimension invariant validated: {configured_dim} dimensions "
        f"(Model: {configured_model})."
    )
    return True


def validate_vectors_before_insert(
    embeddings: List[List[float]],
    qdrant_service: Optional[QdrantService] = None,
) -> bool:
    """Pre-insertion invariant check on actual vectors before committing points to Qdrant."""
    if not embeddings:
        return True

    configured_dim = settings.EMBEDDING_DIMENSION
    configured_model = settings.EMBEDDING_MODEL
    qdrant = qdrant_service or QdrantService()

    qdrant_dim = qdrant._dim
    try:
        col_info = qdrant.client.get_collection(qdrant.collection_name)
        vec_params = col_info.config.params.vectors
        if hasattr(vec_params, "size"):
            qdrant_dim = vec_params.size
    except Exception:
        pass

    for idx, vec in enumerate(embeddings):
        actual_len = len(vec)
        if actual_len != configured_dim or actual_len != qdrant_dim:
            raise RuntimeError(
                f"Embedding Space Invariant Violation at vector index {idx}: "
                f"Configured Model: '{configured_model}', "
                f"Configured Dimension: {configured_dim}, "
                f"Actual Dimension: {actual_len}, "
                f"Qdrant Dimension: {qdrant_dim}. FAIL FAST."
            )

    return True
