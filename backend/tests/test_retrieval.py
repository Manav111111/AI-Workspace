import uuid
import pytest
from app.services.embeddings import EmbeddingService
from app.services.qdrant_service import QdrantService
from app.services.retrieval import RetrievalService


@pytest.mark.asyncio
async def test_retrieval_service_filtering_and_metadata():
    qdrant = QdrantService()
    embedding = EmbeddingService()
    retrieval = RetrievalService(qdrant_service=qdrant, embedding_service=embedding)

    company_id = uuid.uuid4()
    kb_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    # 1. Upsert mock chunk records
    chunk_1_id = uuid.uuid4()
    chunk_2_id = uuid.uuid4()
    texts = [
        "Company standard warranty covers all hardware defects for 24 months from purchase date.",
        "Internal security protocols require all employee passwords to be at least 16 characters.",
    ]
    vecs = embedding.embed_texts(texts)

    chunks = [
        {
            "id": chunk_1_id,
            "chunk_index": 0,
            "content": texts[0],
            "token_count": 15,
            "chunk_metadata": {
                "source": "warranty_policy.pdf",
                "page_number": 2,
                "header_path": "Warranty Coverage",
            },
        },
        {
            "id": chunk_2_id,
            "chunk_index": 1,
            "content": texts[1],
            "token_count": 14,
            "chunk_metadata": {
                "source": "security_handbook.md",
                "page_number": 5,
                "header_path": "Password Standards",
            },
        },
    ]

    qdrant.upsert_chunks(
        company_id=company_id,
        knowledge_base_id=kb_id,
        document_id=doc_id,
        chunk_records=chunks,
        embeddings=vecs,
    )

    # 2. Test mandatory company_id enforcement
    with pytest.raises(ValueError):
        await retrieval.retrieve(company_id=None, query="warranty period")

    # 3. Retrieve relevant chunk
    results = await retrieval.retrieve(
        company_id=company_id,
        query="Company standard warranty defects",
        top_k=2,
        score_threshold=0.05,
    )

    assert len(results) >= 1
    top = results[0]
    assert "warranty" in top.text.lower()
    assert top.source == "warranty_policy.pdf"
    assert top.page_number == 2
    assert top.header_path == "Warranty Coverage"
    assert top.score > 0.05

    # 4. Filter by specific KB ID
    kb_results = await retrieval.retrieve(
        company_id=company_id,
        query="Company standard warranty defects",
        knowledge_base_id=kb_id,
        score_threshold=0.05,
    )
    assert len(kb_results) >= 1

    # Filter by non-existent KB ID -> 0 results
    empty_results = await retrieval.retrieve(
        company_id=company_id,
        query="Company standard warranty defects",
        knowledge_base_id=uuid.uuid4(),
        score_threshold=0.05,
    )
    assert len(empty_results) == 0
