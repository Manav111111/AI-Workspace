import uuid
import pytest
from qdrant_client import QdrantClient
from app.services.qdrant_service import QdrantService


def test_qdrant_service_lifecycle_in_memory():
    # Use dedicated in-memory Qdrant client
    mem_client = QdrantClient(":memory:")
    q_service = QdrantService(client=mem_client, collection_name="test_collection")

    company_id = uuid.uuid4()
    kb_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    dummy_vector = [0.1] * 384
    # Normalize dummy vector
    norm = sum(x * x for x in dummy_vector) ** 0.5
    dummy_vector = [x / norm for x in dummy_vector]

    chunks = [
        {
            "id": chunk_id,
            "chunk_index": 0,
            "content": "Confidential internal SOP.",
            "token_count": 4,
            "chunk_metadata": {"source": "sop.pdf", "page": 1},
        }
    ]

    # 1. Upsert chunks
    q_service.upsert_chunks(
        company_id=company_id,
        knowledge_base_id=kb_id,
        document_id=doc_id,
        chunk_records=chunks,
        embeddings=[dummy_vector],
    )

    # 2. Search with company_id
    results = q_service.search(
        company_id=company_id,
        query_vector=dummy_vector,
        knowledge_base_id=kb_id,
        limit=5,
    )
    assert len(results) == 1
    hit = results[0]
    assert hit["payload"]["company_id"] == str(company_id)
    assert hit["payload"]["document_id"] == str(doc_id)
    assert hit["payload"]["source"] == "sop.pdf"

    # 3. Delete document vectors
    q_service.delete_document_vectors(company_id=company_id, document_id=doc_id)
    after_del = q_service.search(
        company_id=company_id,
        query_vector=dummy_vector,
        limit=5,
    )
    assert len(after_del) == 0
