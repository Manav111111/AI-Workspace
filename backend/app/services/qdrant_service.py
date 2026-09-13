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
        else:
            try:
                self.client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                    timeout=1.0,
                )
                # Quick test connection
                self.client.get_collections()
            except Exception as e:
                logger.warning(
                    f"Could not connect to live Qdrant at {settings.QDRANT_URL} ({e}). "
                    "Falling back to shared in-memory QdrantClient."
                )
                if _shared_memory_client is None:
                    _shared_memory_client = QdrantClient(":memory:")
                self.client = _shared_memory_client

        self.ensure_collection()

    def ensure_collection(self) -> None:
        """Ensures the collection exists with cosine distance and payload index on company_id."""
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
                # Create payload index on company_id for high-performance multi-tenant filtering
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="company_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="document_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
        except Exception as e:
            logger.warning(f"Error checking/creating Qdrant collection ({e}). Re-attempting in-memory.")
            self.client = QdrantClient(":memory:")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=self._dim,
                    distance=qmodels.Distance.COSINE,
                ),
            )

    def upsert_chunks(
        self,
        company_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        document_id: uuid.UUID,
        chunk_records: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> None:
        """Upserts document chunk vectors with mandatory tenant payload metadata."""
        if not chunk_records or not embeddings:
            return

        points: List[qmodels.PointStruct] = []
        for chunk, vec in zip(chunk_records, embeddings):
            chunk_id = chunk["id"]
            # Convert UUID to valid string
            point_id = str(chunk_id)

            payload = {
                "chunk_id": str(chunk_id),
                "company_id": str(company_id),
                "knowledge_base_id": str(knowledge_base_id),
                "document_id": str(document_id),
                "chunk_index": chunk.get("chunk_index", 0),
                "content": chunk.get("content", ""),
                "token_count": chunk.get("token_count", 0),
            }
            # Add any extra metadata from chunk
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

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
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

        # qdrant-client >= 1.10+ supports query_points or search
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
