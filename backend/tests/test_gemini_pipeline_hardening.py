import math
import os
import unittest.mock as mock
import uuid
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.services.chunking import ChunkingService, RawChunk
from app.services.embeddings import (
    DeterministicCpuEmbeddingProvider,
    EmbeddingAuthenticationException,
    EmbeddingDimensionMismatchException,
    EmbeddingException,
    EmbeddingProvider,
    EmbeddingRateLimitException,
    EmbeddingService,
    GeminiEmbeddingProvider,
    MockEmbeddingProvider,
)
from app.services.ingestion import IngestionService, sanitize_error_message
from app.services.invariants import (
    validate_embedding_dimension_invariant,
    validate_vectors_before_insert,
)
from app.services.qdrant_service import QdrantService
from app.services.retrieval import RetrievalService


# ==============================================================================
# 1. Gemini Provider Configuration
# ==============================================================================
def test_gemini_provider_configuration():
    provider = GeminiEmbeddingProvider(
        api_key="test-api-key",
        model="gemini-embedding-001",
        dimension=384,
        timeout_seconds=25.0,
        max_retries=2,
        batch_size=15,
    )
    assert provider.dimension == 384
    assert provider.model == "gemini-embedding-001"
    assert provider.timeout == 25.0
    assert provider.max_retries == 2
    assert provider.batch_size == 15
    assert provider._redact("url?key=test-api-key&other=1") == "url?key=[REDACTED]&other=1"


# ==============================================================================
# 2. Vector Dimension Validation
# ==============================================================================
def test_gemini_vector_dimension_validation():
    provider = GeminiEmbeddingProvider(
        api_key="test-key",
        model="gemini-embedding-001",
        dimension=384,
        max_retries=1,
    )
    # Mock response returning 512 dimensions instead of 384
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "embeddings": [{"values": [0.1] * 512}]
    }

    with mock.patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(EmbeddingDimensionMismatchException) as exc_info:
            provider.embed_texts(["sample text"])
        assert "dimension 512" in str(exc_info.value)
        assert "configured dimension is 384" in str(exc_info.value)


# ==============================================================================
# 3. Qdrant Dimension Mismatch
# ==============================================================================
def test_qdrant_dimension_mismatch_fails_fast():
    class MismatchedEmbService(EmbeddingService):
        @property
        def dimension(self):
            return 384

        def embed_texts(self, texts):
            return [[0.0] * 384 for _ in texts]

    emb = MismatchedEmbService()
    # Create QdrantService with mismatched dimension
    qdrant = QdrantService()
    qdrant._dim = 768

    with pytest.raises(RuntimeError) as exc_info:
        validate_embedding_dimension_invariant(emb, qdrant)

    msg = str(exc_info.value)
    assert "Invariant Violation" in msg
    assert "Configured Dimension: 384" in msg


# ==============================================================================
# 4. Gemini 429 Retry (Exponential Backoff)
# ==============================================================================
def test_gemini_429_retry_exhaustion():
    provider = GeminiEmbeddingProvider(
        api_key="test-key",
        model="gemini-embedding-001",
        dimension=384,
        max_retries=2,
    )
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Quota exceeded (RESOURCE_EXHAUSTED)"

    with mock.patch("httpx.Client.post", return_value=mock_resp), mock.patch("time.sleep"):
        with pytest.raises(EmbeddingException) as exc_info:
            provider.embed_texts(["sample text"])
        assert "failed after 2 attempts" in str(exc_info.value)


def test_gemini_429_retry_recovery():
    provider = GeminiEmbeddingProvider(
        api_key="test-key",
        model="gemini-embedding-001",
        dimension=384,
        max_retries=3,
    )
    resp_429 = mock.MagicMock(status_code=429, text="Rate limit")
    resp_200 = mock.MagicMock(status_code=200)
    resp_200.json.return_value = {
        "embeddings": [{"values": [0.05] * 384}]
    }

    with mock.patch("httpx.Client.post", side_effect=[resp_429, resp_200]), mock.patch("time.sleep"):
        vecs = provider.embed_texts(["recovered text"])
        assert len(vecs) == 1
        assert len(vecs[0]) == 384


# ==============================================================================
# 5. Gemini Timeout Handling
# ==============================================================================
def test_gemini_timeout_handling():
    provider = GeminiEmbeddingProvider(
        api_key="test-key",
        dimension=384,
        max_retries=2,
    )
    with mock.patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timed out")), mock.patch("time.sleep"):
        with pytest.raises(EmbeddingException) as exc:
            provider.embed_texts(["timeout probe"])
        assert "timeout" in str(exc.value).lower()


# ==============================================================================
# 6. Gemini 5xx Server Error Handling
# ==============================================================================
def test_gemini_5xx_server_error():
    provider = GeminiEmbeddingProvider(
        api_key="test-key",
        dimension=384,
        max_retries=2,
    )
    mock_resp = mock.MagicMock(status_code=503, text="Service Unavailable")
    with mock.patch("httpx.Client.post", return_value=mock_resp), mock.patch("time.sleep"):
        with pytest.raises(EmbeddingException) as exc:
            provider.embed_texts(["probe"])
        assert "503" in str(exc.value)


# ==============================================================================
# 7. Failed Ingestion & Safe Error Recording
# ==============================================================================
@pytest.mark.asyncio
async def test_failed_ingestion_state_and_safe_error(db_session: AsyncSession):
    company_id = uuid.uuid4()
    kb_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    kb = KnowledgeBase(id=kb_id, company_id=company_id, name="Test KB")
    db_session.add(kb)

    doc = Document(
        id=doc_id,
        company_id=company_id,
        knowledge_base_id=kb_id,
        filename="test.txt",
        original_filename="test.txt",
        file_type="txt",
        mime_type="text/plain",
        file_size=100,
        storage_path="mock/path/test.txt",
        status=DocumentStatus.UPLOADED,
        document_metadata={},
    )
    db_session.add(doc)
    await db_session.commit()

    # Mock storage to return bytes
    mock_storage = mock.MagicMock()
    mock_storage.get = mock.AsyncMock(return_value=b"Document content for test")

    # Mock embedder that raises an error containing a sensitive API key
    mock_embedder = mock.MagicMock()
    mock_embedder.generate_embeddings.side_effect = EmbeddingException(
        "API request failed with key=SECRET_KEY_123456"
    )

    ingestion = IngestionService(
        session=db_session,
        storage_service=mock_storage,
        embedding_service=mock_embedder,
        qdrant_service=QdrantService(),
    )

    failed_doc = await ingestion.process_document(document_id=doc_id, company_id=company_id)
    assert failed_doc.status == DocumentStatus.FAILED
    assert "SECRET_KEY_123456" not in failed_doc.error_message
    assert "[REDACTED]" in failed_doc.error_message


# ==============================================================================
# 8. No Silent CPU Fallback
# ==============================================================================
def test_no_silent_cpu_fallback_when_gemini_fails():
    with mock.patch.object(settings, "EMBEDDING_PROVIDER", "gemini"):
        with mock.patch.object(settings, "GEMINI_API_KEY", ""):
            with mock.patch.object(settings, "GOOGLE_API_KEY", ""):
                with pytest.raises(EmbeddingAuthenticationException) as exc:
                    EmbeddingService()
                assert "Silent fallback to CPU is forbidden" in str(exc.value)


# ==============================================================================
# 9. Explicit CPU Provider
# ==============================================================================
def test_explicit_cpu_provider():
    with mock.patch.object(settings, "EMBEDDING_PROVIDER", "cpu"):
        service = EmbeddingService()
        assert isinstance(service.provider, DeterministicCpuEmbeddingProvider)
        assert service.dimension == 384
        vecs = service.generate_embeddings(["test text"])
        assert len(vecs) == 1
        assert len(vecs[0]) == 384


# ==============================================================================
# 10. Mock Provider
# ==============================================================================
def test_mock_provider():
    with mock.patch.object(settings, "EMBEDDING_PROVIDER", "mock"):
        service = EmbeddingService()
        assert isinstance(service.provider, MockEmbeddingProvider)
        assert service.dimension == 384
        vecs = service.generate_embeddings(["test", "another"])
        assert len(vecs) == 2
        assert len(vecs[0]) == 384


# ==============================================================================
# 11. Batch Embedding
# ==============================================================================
def test_batch_embedding_chunking():
    provider = GeminiEmbeddingProvider(
        api_key="test-key",
        dimension=384,
        batch_size=2,
    )
    # 5 texts should produce 3 batches (2, 2, 1)
    texts = [f"text {i}" for i in range(5)]
    calls = []

    def mock_embed_batch(batch):
        calls.append(len(batch))
        return [[0.1] * 384 for _ in batch]

    provider._embed_batch_with_retry = mock_embed_batch
    res = provider.embed_texts(texts)
    assert len(res) == 5
    assert calls == [2, 2, 1]


# ==============================================================================
# 12. Metadata Preservation
# ==============================================================================
def test_metadata_preservation():
    qdrant = QdrantService()
    comp_id = uuid.uuid4()
    kb_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    chunk_records = [
        {
            "id": chunk_id,
            "chunk_index": 0,
            "content": "Return policy chunk.",
            "token_count": 4,
            "chunk_metadata": {
                "source": "manual.pdf",
                "title": "Return Policy",
                "page_number": 2,
                "header_path": "Policies > Returns",
            },
        }
    ]
    embeddings = [[0.05] * 384]

    with mock.patch.object(qdrant.client, "upsert") as mock_upsert:
        qdrant.upsert_chunks(
            company_id=comp_id,
            knowledge_base_id=kb_id,
            document_id=doc_id,
            chunk_records=chunk_records,
            embeddings=embeddings,
        )
        assert mock_upsert.called
        points = mock_upsert.call_args[1]["points"]
        assert len(points) == 1
        payload = points[0].payload
        assert payload["company_id"] == str(comp_id)
        assert payload["knowledge_base_id"] == str(kb_id)
        assert payload["document_id"] == str(doc_id)
        assert payload["source"] == "manual.pdf"
        assert payload["title"] == "Return Policy"
        assert payload["page_number"] == 2
        assert payload["header_path"] == "Policies > Returns"
        assert payload["embedding_provider"] == settings.EMBEDDING_PROVIDER
        assert payload["embedding_model"] == settings.EMBEDDING_MODEL
        assert payload["embedding_dimension"] == 384


# ==============================================================================
# 13. Tenant Isolation in Retrieval
# ==============================================================================
@pytest.mark.asyncio
async def test_tenant_isolation_retrieval():
    qdrant = QdrantService()
    comp_a = uuid.uuid4()
    comp_b = uuid.uuid4()

    # Search with company A
    with mock.patch.object(qdrant, "search", return_value=[]) as mock_search:
        retrieval = RetrievalService(qdrant_service=qdrant)
        await retrieval.retrieve(company_id=comp_a, query="test query")
        assert mock_search.called
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["company_id"] == comp_a
        assert call_kwargs["company_id"] != comp_b


# ==============================================================================
# 14. Knowledge Base Filtering
# ==============================================================================
@pytest.mark.asyncio
async def test_knowledge_base_filtering_retrieval():
    qdrant = QdrantService()
    comp_id = uuid.uuid4()
    kb_id = uuid.uuid4()

    with mock.patch.object(qdrant, "search", return_value=[]) as mock_search:
        retrieval = RetrievalService(qdrant_service=qdrant)
        await retrieval.retrieve(company_id=comp_id, query="policy", knowledge_base_id=kb_id)
        assert mock_search.called
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["company_id"] == comp_id
        assert call_kwargs["knowledge_base_id"] == kb_id


# ==============================================================================
# 15. Retrieval Compatibility & Dimension Probe
# ==============================================================================
@pytest.mark.asyncio
async def test_retrieval_compatibility_probe():
    retrieval = RetrievalService()
    # Embed a query probe
    q_vec = retrieval.embedding.embed_query("Sample query")
    assert len(q_vec) == 384
    norm = math.sqrt(sum(x * x for x in q_vec))
    assert abs(norm - 1.0) < 1e-4


# ==============================================================================
# OPT-IN REAL API INTEGRATION TEST
# Only executes when RUN_GEMINI_INTEGRATION=1 is explicitly set in environment
# ==============================================================================
@pytest.mark.skipif(
    os.getenv("RUN_GEMINI_INTEGRATION") not in ("1", "true", "True"),
    reason="Opt-in real Gemini and Qdrant Cloud integration test. Enable with RUN_GEMINI_INTEGRATION=1.",
)
@pytest.mark.asyncio
async def test_real_gemini_and_qdrant_cloud_integration():
    """Live opt-in verification of GeminiEmbeddingProvider and Qdrant Cloud."""
    from dotenv import dotenv_values
    env_vals = dotenv_values(".env")

    gemini_key = env_vals.get("GEMINI_API_KEY") or env_vals.get("GOOGLE_API_KEY")
    qdrant_url = env_vals.get("QDRANT_URL")
    qdrant_key = env_vals.get("QDRANT_API_KEY")

    assert gemini_key, "GEMINI_API_KEY required for integration test"
    assert qdrant_url, "QDRANT_URL required for integration test"

    # 1. Real Gemini Embedding
    provider = GeminiEmbeddingProvider(
        api_key=gemini_key,
        model="gemini-embedding-001",
        dimension=384,
    )
    texts = [
        "Google Gemini powers vector embeddings.",
        "Qdrant Cloud stores high-dimensional vectors.",
    ]
    vectors = provider.embed_texts(texts)
    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384

    # 2. Real Qdrant Cloud Connection
    from qdrant_client import QdrantClient
    client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=15.0)
    colls = [c.name for c in client.get_collections().collections]
    assert "kb_documents" in colls

    # 3. Upsert test point into Qdrant Cloud
    test_tenant_id = uuid.uuid4()
    test_kb_id = uuid.uuid4()
    test_doc_id = uuid.uuid4()
    test_chunk_id = uuid.uuid4()

    qdrant_service = QdrantService(client=client)
    qdrant_service.upsert_chunks(
        company_id=test_tenant_id,
        knowledge_base_id=test_kb_id,
        document_id=test_doc_id,
        chunk_records=[
            {
                "id": test_chunk_id,
                "chunk_index": 0,
                "content": "Live integration test chunk for Gemini + Qdrant Cloud.",
                "token_count": 9,
                "chunk_metadata": {"source": "integration_test.txt"},
            }
        ],
        embeddings=[vectors[0]],
    )

    # 4. Search and verify retrieval
    query_vec = provider.embed_query("Live integration test")
    results = qdrant_service.search(
        company_id=test_tenant_id,
        query_vector=query_vec,
        limit=5,
    )
    assert len(results) >= 1
    assert results[0]["payload"]["chunk_id"] == str(test_chunk_id)

    # 5. Clean up test vector
    qdrant_service.delete_document_vectors(company_id=test_tenant_id, document_id=test_doc_id)
