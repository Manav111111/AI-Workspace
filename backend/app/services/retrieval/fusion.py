import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("app.services.retrieval.fusion")


class ReciprocalRankFusion:
    """Implements Reciprocal Rank Fusion (RRF) to merge dense and sparse candidate rankings.
    Formula:
        RRF(d) = sum_{m in models} 1 / (k_rrf + rank_m(d))
    where k_rrf is a smoothing constant (standard default: 60).
    """

    def __init__(self, k: int = 60):
        self.k = k

    def fuse(
        self,
        dense_chunks: List[Any],
        sparse_chunks: List[Any],
        candidate_k: int = 20,
    ) -> List[Any]:
        """Fuses ranked lists of dense and sparse RetrievedChunk objects.
        Returns a deduplicated list of chunks sorted by descending RRF score.
        """
        # Map of chunk_id string -> combined chunk object
        chunk_map: Dict[str, Any] = {}
        rrf_scores: Dict[str, float] = {}
        dense_ranks: Dict[str, int] = {}
        sparse_ranks: Dict[str, int] = {}
        dense_scores: Dict[str, float] = {}
        sparse_scores: Dict[str, float] = {}

        # 1. Process dense ranked results
        for rank, chunk in enumerate(dense_chunks, start=1):
            cid = str(chunk.chunk_id)
            chunk_map[cid] = chunk
            dense_ranks[cid] = rank
            dense_scores[cid] = chunk.score
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.k + rank))

        # 2. Process sparse ranked results
        for rank, chunk in enumerate(sparse_chunks, start=1):
            cid = str(chunk.chunk_id)
            if cid not in chunk_map:
                chunk_map[cid] = chunk
            sparse_ranks[cid] = rank
            sparse_scores[cid] = chunk.score
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.k + rank))

        # 3. Sort candidates by RRF score descending, tie-breaking by chunk ID for determinism
        sorted_cids = sorted(
            chunk_map.keys(),
            key=lambda cid: (rrf_scores[cid], cid),
            reverse=True,
        )

        # 4. Construct final fused RetrievedChunk candidates
        fused_results: List[Any] = []
        for final_rank, cid in enumerate(sorted_cids[:candidate_k], start=1):
            chunk = chunk_map[cid]
            fusion_score = rrf_scores[cid]

            # Clone chunk metadata and attach detailed provenance
            updated_metadata = {
                **(chunk.metadata or {}),
                "fusion_type": "rrf",
                "rrf_score": round(fusion_score, 6),
                "final_fusion_rank": final_rank,
            }
            if cid in dense_ranks:
                updated_metadata["dense_rank"] = dense_ranks[cid]
                updated_metadata["dense_score"] = dense_scores[cid]
            if cid in sparse_ranks:
                updated_metadata["sparse_rank"] = sparse_ranks[cid]
                updated_metadata["sparse_score"] = sparse_scores[cid]

            # In RetrievedChunk, set score to rrf_score
            chunk.score = round(fusion_score, 6)
            chunk.metadata = updated_metadata
            fused_results.append(chunk)

        logger.debug(
            f"RRF fusion: {len(dense_chunks)} dense + {len(sparse_chunks)} sparse -> {len(fused_results)} candidates"
        )
        return fused_results
