import logging
from typing import Any, Dict, List, Optional
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from app.core.config import settings

logger = logging.getLogger("app.services.qdrant")

_shared_memory_client: Optional[QdrantClient] = None


class QdrantService:
    """Service abstraction for Qdrant Vector Database.
    Strictly enforces company_id tenant payload filtering on all search operations.
    """

    def __init__(self, client: Optional[QdrantClient] = None, collection_name: Optional[str] = None):
        global _shared_memory_client
        self.collection_name = collection_name or f"{settings.QDRANT_COLLECTION_PREFIX}documents"
        self._dim = settings.EMBEDDING_DIMENSION

        if client:
            self.client = client
        elif settings.QDRANT_URL == ":memory:":
            if _shared_memory_client is None:
                _shared_memory_client = QdrantClient(":memory:")
            self.client = _shared_memory_client
        elif not settings.QDRANT_URL.startswith("http"):
            if _shared_memory_client is None:
                _shared_memory_client = QdrantClient(path=settings.QDRANT_URL)
            self.client = _shared_memory_client
        else:
            try:
                self.client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                    timeout=30.0,
                )
                # Quick test connection
                self.client.get_collections()
            except Exception as e:
                # In test environment, permit in-memory fallback
                if settings.ENVIRONMENT == "test":
                    logger.warning(
                        f"Test environment: could not connect to live Qdrant ({e}). Falling back to :memory:."
                    )
                    if _shared_memory_client is None:
                        _shared_memory_client = QdrantClient(":memory:")
                    self.client = _shared_memory_client
                else:
                    logger.error(
                        f"CRITICAL: Failed to connect to configured Qdrant endpoint ({settings.QDRANT_URL}). "
                        "Silent fallback to :memory: is forbidden in non-test environments."
                    )
                    raise RuntimeError(f"Qdrant connection failure at {settings.QDRANT_URL}: {e}")

        self.ensure_collection()

    def ensure_collection(self) -> None:
        """Ensures the collection exists with cosine distance and payload indexes.
        CRITICAL: Never automatically mutates or recreates collection on dimension mismatch.
        """
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self._dim,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
            else:
                # Validate existing collection dimension invariant
                col_info = self.client.get_collection(self.collection_name)
                vec_params = col_info.config.params.vectors
                col_size = vec_params.size if hasattr(vec_params, "size") else None
                if col_size is not None and col_size != self._dim:
                    raise RuntimeError(
                        f"Qdrant Dimension Mismatch: Collection '{self.collection_name}' has dimension {col_size}, "
                        f"but configured dimension is {self._dim} (Model: {settings.EMBEDDING_MODEL}). FAIL FAST. "
                        f"Do NOT automatically recreate or mutate the collection."
                    )

            for field in ["company_id", "knowledge_base_id", "document_id"]:
                try:
                    self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field,
                        field_schema=qmodels.PayloadSchemaType.KEYWORD,
                    )
                except Exception as idx_err:
                    logger.debug(f"Payload index on {field} already exists or note: {idx_err}")
        except Exception as e:
            if "Dimension Mismatch" in str(e) or "FAIL FAST" in str(e):
                raise
            if settings.ENVIRONMENT == "test":
                logger.warning(f"Error checking/creating Qdrant collection in test ({e}). Using in-memory.")
                self.client = QdrantClient(":memory:")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self._dim,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
            else:
                raise

    def upsert_chunks(
        self,
        company_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        document_id: uuid.UUID,
        chunk_records: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        """Upserts document chunk vectors with mandatory tenant payload metadata in bounded batches."""
        if not chunk_records or not embeddings:
            return

        points: List[qmodels.PointStruct] = []
        for chunk, vec in zip(chunk_records, embeddings):
            chunk_id = chunk["id"]
            point_id = str(chunk_id)

            payload = {
                "chunk_id": str(chunk_id),
                "company_id": str(company_id),
                "knowledge_base_id": str(knowledge_base_id),
                "document_id": str(document_id),
                "chunk_index": chunk.get("chunk_index", 0),
                "content": chunk.get("content", ""),
                "token_count": chunk.get("token_count", 0),
                "embedding_provider": settings.EMBEDDING_PROVIDER,
                "embedding_model": settings.EMBEDDING_MODEL,
                "embedding_dimension": settings.EMBEDDING_DIMENSION,
            }
            # Add extra metadata from chunk (page_number, header_path, source, title)
            if "chunk_metadata" in chunk and isinstance(chunk["chunk_metadata"], dict):
                for k, v in chunk["chunk_metadata"].items():
                    if k not in payload:
                        payload[k] = v

            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=vec,
                    payload=payload,
                )
            )

        # Upsert in bounded batches of 50
        batch_size = 50
        for i in range(0, len(points), batch_size):
            pts_batch = points[i : i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=pts_batch,
                wait=True,
            )

    def delete_document_vectors(self, company_id: uuid.UUID, document_id: uuid.UUID) -> None:
        """Deletes all vectors belonging to a document, verifying company_id boundary."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="company_id",
                            match=qmodels.MatchValue(value=str(company_id)),
                        ),
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=str(document_id)),
                        ),
                    ]
                )
            ),
            wait=True,
        )

    def delete_knowledge_base_vectors(self, company_id: uuid.UUID, knowledge_base_id: uuid.UUID) -> None:
        """Deletes all vectors belonging to a Knowledge Base within a company."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="company_id",
                            match=qmodels.MatchValue(value=str(company_id)),
                        ),
                        qmodels.FieldCondition(
                            key="knowledge_base_id",
                            match=qmodels.MatchValue(value=str(knowledge_base_id)),
                        ),
                    ]
                )
            ),
            wait=True,
        )

    def search(
        self,
        company_id: uuid.UUID,
        query_vector: List[float],
        knowledge_base_id: Optional[uuid.UUID] = None,
        knowledge_base_ids: Optional[List[uuid.UUID]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """MANDATORY TENANT ISOLATION:
        Searches vectors strictly scoped to the authenticated caller's company_id.
        Optionally scopes to a list of allowed knowledge_base_ids or a single knowledge_base_id.
        Company A can NEVER retrieve Company B vectors.
        """
        must_conditions: List[qmodels.Condition] = [
            qmodels.FieldCondition(
                key="company_id",
                match=qmodels.MatchValue(value=str(company_id)),
            )
        ]
        if knowledge_base_ids:
            if len(knowledge_base_ids) == 1:
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="knowledge_base_id",
                        match=qmodels.MatchValue(value=str(knowledge_base_ids[0])),
                    )
                )
            else:
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="knowledge_base_id",
                        match=qmodels.MatchAny(any=[str(kb_id) for kb_id in knowledge_base_ids]),
                    )
                )
        elif knowledge_base_id:
            must_conditions.append(
                qmodels.FieldCondition(
                    key="knowledge_base_id",
                    match=qmodels.MatchValue(value=str(knowledge_base_id)),
                )
            )

        search_filter = qmodels.Filter(must=must_conditions)

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                with_payload=True,
            )
            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                }
                for hit in results
            ]
        except AttributeError:
            import time
            for attempt in range(3):
                try:
                    response = self.client.query_points(
                        collection_name=self.collection_name,
                        query=query_vector,
                        query_filter=search_filter,
                        limit=limit,
                        with_payload=True,
                    )
                    return [
                        {
                            "id": point.id,
                            "score": point.score,
                            "payload": point.payload,
                        }
                        for point in response.points
                    ]
                except Exception as ex:
                    if attempt < 2:
                        time.sleep(1.0)
                        continue
                    raise
