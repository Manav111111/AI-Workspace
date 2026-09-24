import uuid
import pytest
from app.models.company import Company
from app.models.document import Document, DocumentStatus
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_base import KnowledgeBase
from app.services.retrieval import (
    DenseRetriever,
    HeuristicReranker,
    NoOpReranker,
    ReciprocalRankFusion,
    RetrievalService,
    RetrievedChunk,
    SparseRetriever,
)
from app.services.retrieval.bm25 import BM25Index, PurePythonBM25, tokenize_text
from app.services.retrieval.reranker import CrossEncoderReranker, get_reranker


# ============================================================================
# 1. PURE BM25 MATHEMATICAL & TOKENIZATION TESTS
# ============================================================================

def test_tokenize_text():
    raw = "HR Policy: Annual-Leave & Medical_Leave 2026! Employee #123."
    tokens = tokenize_text(raw)
    assert "hr" in tokens
    assert "policy" in tokens
    assert "annual-leave" in tokens or "annual" in tokens
    assert "employee" in tokens
    assert "123" in tokens
    # Empty string
    assert tokenize_text("") == []


def test_pure_python_bm25_math():
    corpus = [
        ["annual", "leave", "entitlement", "days"],
        ["casual", "leave", "process"],
        ["medical", "insurance", "coverage"],
    ]
    bm25 = PurePythonBM25(corpus)
    assert bm25.corpus_size == 3
    assert len(bm25.idf) > 0

    # Query with exact terms from doc 0
    scores = bm25.get_scores(["annual", "leave"])
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]
    # Doc 1 has "leave" but not "annual"
    assert scores[1] > scores[2]

    # Query with out-of-vocabulary term
    scores_oov = bm25.get_scores(["cryptocurrency"])
    assert all(s == 0.0 for s in scores_oov)


def test_bm25_index_search():
    ids = ["doc_1", "doc_2", "doc_3"]
    texts = [
        "Full-time employees receive 18 days of paid annual leave.",
        "Probationary period for new hires is three months.",
        "Travel expense reimbursement guidelines and meal allowances.",
    ]
    index = BM25Index(chunk_ids=ids, chunk_texts=texts)
    results = index.search("annual leave days", top_k=2)

    assert len(results) > 0
    assert results[0][0] == "doc_1"
    assert results[0][1] > 0.0


# ============================================================================
# 2. RECIPROCAL RANK FUSION (RRF) MATHEMATICAL TESTS
# ============================================================================

def test_reciprocal_rank_fusion_math():
    c1 = uuid.uuid4()
    c2 = uuid.uuid4()
    c3 = uuid.uuid4()

    doc_id = uuid.uuid4()
    kb_id = uuid.uuid4()

    # Dense ranked: c1 (rank 1), c2 (rank 2)
    dense_list = [
        RetrievedChunk(chunk_id=c1, document_id=doc_id, knowledge_base_id=kb_id, text="C1 text", score=0.90),
        RetrievedChunk(chunk_id=c2, document_id=doc_id, knowledge_base_id=kb_id, text="C2 text", score=0.80),
    ]

    # Sparse ranked: c2 (rank 1), c3 (rank 2)
    sparse_list = [
        RetrievedChunk(chunk_id=c2, document_id=doc_id, knowledge_base_id=kb_id, text="C2 text", score=0.95),
        RetrievedChunk(chunk_id=c3, document_id=doc_id, knowledge_base_id=kb_id, text="C3 text", score=0.70),
    ]

    fusion = ReciprocalRankFusion(k=60)
    fused = fusion.fuse(dense_chunks=dense_list, sparse_chunks=sparse_list, candidate_k=5)

    # c2 appears in BOTH lists: rank 2 in dense + rank 1 in sparse
    # Score(c2) = 1/(60+2) + 1/(60+1) = 1/62 + 1/61 = 0.016129 + 0.016393 = 0.03252
    # Score(c1) = 1/(60+1) = 1/61 = 0.016393
    # Score(c3) = 1/(60+2) = 1/62 = 0.016129
    # Expected ordering: c2 > c1 > c3
    assert len(fused) == 3
    assert fused[0].chunk_id == c2
    assert fused[1].chunk_id == c1
    assert fused[2].chunk_id == c3

    # Check provenance metadata preservation
    assert fused[0].metadata["dense_rank"] == 2
    assert fused[0].metadata["sparse_rank"] == 1
    assert "rrf_score" in fused[0].metadata


# ============================================================================
# 3. RERANKER LAYER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_noop_reranker():
    reranker = NoOpReranker()
    c1 = RetrievedChunk(chunk_id=uuid.uuid4(), document_id=uuid.uuid4(), knowledge_base_id=uuid.uuid4(), text="A", score=0.9)
    c2 = RetrievedChunk(chunk_id=uuid.uuid4(), document_id=uuid.uuid4(), knowledge_base_id=uuid.uuid4(), text="B", score=0.8)
    res = await reranker.rerank("test query", [c1, c2], top_k=1)
    assert len(res) == 1
    assert res[0].chunk_id == c1.chunk_id


@pytest.mark.asyncio
async def test_heuristic_reranker_exact_match_boost():
    reranker = HeuristicReranker()
    c_weak = RetrievedChunk(
        chunk_id=uuid.uuid4(), document_id=uuid.uuid4(), knowledge_base_id=uuid.uuid4(),
        text="General office guidelines and coffee machine rules.", score=0.95
    )
    c_exact = RetrievedChunk(
        chunk_id=uuid.uuid4(), document_id=uuid.uuid4(), knowledge_base_id=uuid.uuid4(),
        text="Official Policy: Annual leave allocation is 24 working days per calendar year.", score=0.50
    )

    # Candidate order has c_weak first, but query matches c_exact terms specifically
    res = await reranker.rerank("Annual leave allocation", [c_weak, c_exact], top_k=2)
    assert res[0].chunk_id == c_exact.chunk_id
    assert res[0].metadata["reranker"] == "heuristic"


@pytest.mark.asyncio
async def test_cross_encoder_reranker_fallback():
    # Model name that doesn't exist locally -> must fall back gracefully to heuristic
    reranker = CrossEncoderReranker(model_name="non_existent_mock_model_12345")
    c1 = RetrievedChunk(chunk_id=uuid.uuid4(), document_id=uuid.uuid4(), knowledge_base_id=uuid.uuid4(), text="Leave policy details", score=0.8)
    res = await reranker.rerank("Leave policy", [c1], top_k=1)
    assert len(res) == 1
    assert res[0].chunk_id == c1.chunk_id


# ============================================================================
# 4. DATABASE & MULTI-TENANT ISOLATION INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_sparse_retriever_strict_tenant_isolation(db_session):
    # Setup Tenant A and Tenant B
    comp_a = Company(name="Tenant Alpha", slug="tenant-alpha")
    comp_b = Company(name="Tenant Beta", slug="tenant-beta")
    db_session.add_all([comp_a, comp_b])
    await db_session.flush()

    kb_a = KnowledgeBase(company_id=comp_a.id, name="KB A")
    kb_b = KnowledgeBase(company_id=comp_b.id, name="KB B")
    db_session.add_all([kb_a, kb_b])
    await db_session.flush()

    doc_a = Document(company_id=comp_a.id, knowledge_base_id=kb_a.id, filename="A.pdf", original_filename="A.pdf", file_type="pdf", mime_type="application/pdf", file_size=100, storage_path="uploads/A.pdf", status=DocumentStatus.PROCESSED)
    doc_b = Document(company_id=comp_b.id, knowledge_base_id=kb_b.id, filename="B.pdf", original_filename="B.pdf", file_type="pdf", mime_type="application/pdf", file_size=100, storage_path="uploads/B.pdf", status=DocumentStatus.PROCESSED)
    db_session.add_all([doc_a, doc_b])

    await db_session.flush()

    # Tenant A chunk: contains "AlphaSecretKey999"
    chunk_a = DocumentChunk(
        company_id=comp_a.id,
        knowledge_base_id=kb_a.id,
        document_id=doc_a.id,
        chunk_index=0,
        content="Confidential AlphaSecretKey999 for Tenant Alpha internal systems.",
        chunk_metadata={"source": "A.pdf"},
    )
    # Tenant B chunk: contains "BetaSecretKey888"
    chunk_b = DocumentChunk(
        company_id=comp_b.id,
        knowledge_base_id=kb_b.id,
        document_id=doc_b.id,
        chunk_index=0,
        content="Confidential BetaSecretKey888 for Tenant Beta internal systems.",
        chunk_metadata={"source": "B.pdf"},
    )
    db_session.add_all([chunk_a, chunk_b])
    await db_session.commit()

    sparse = SparseRetriever(session=db_session)

    # 1. Tenant A queries for "BetaSecretKey888" -> must NOT retrieve Tenant B's chunk!
    results_a = await sparse.retrieve(
        company_id=comp_a.id,
        query="BetaSecretKey888",
        knowledge_base_ids=[kb_a.id],
    )
    assert len(results_a) == 0

    # 2. Tenant B queries for "BetaSecretKey888" -> retrieves Tenant B's chunk
    results_b = await sparse.retrieve(
        company_id=comp_b.id,
        query="BetaSecretKey888",
        knowledge_base_ids=[kb_b.id],
    )
    assert len(results_b) == 1
    assert results_b[0].chunk_id == chunk_b.id


# ============================================================================
# 5. RETRIEVAL SERVICE HYBRID ORCHESTRATION TEST
# ============================================================================

class MockDenseRetriever:
    def __init__(self, chunks):
        self.chunks = chunks

    async def retrieve(self, company_id, query, knowledge_base_id=None, knowledge_base_ids=None, top_k=10, score_threshold=None):
        return self.chunks


class MockSparseRetriever:
    def __init__(self, chunks):
        self.chunks = chunks

    async def retrieve(self, company_id, query, knowledge_base_ids=None, top_k=10):
        return self.chunks


@pytest.mark.asyncio
async def test_retrieval_service_hybrid_mode():
    cid = uuid.uuid4()
    doc_id = uuid.uuid4()
    kb_id = uuid.uuid4()

    chunk_dense = RetrievedChunk(chunk_id=uuid.uuid4(), document_id=doc_id, knowledge_base_id=kb_id, text="Dense chunk", score=0.88)
    chunk_sparse = RetrievedChunk(chunk_id=uuid.uuid4(), document_id=doc_id, knowledge_base_id=kb_id, text="Sparse chunk", score=0.92)

    service = RetrievalService()
    service.dense_retriever = MockDenseRetriever([chunk_dense])
    service.sparse_retriever = MockSparseRetriever([chunk_sparse])

    # Run in hybrid mode
    results = await service.retrieve(
        company_id=cid,
        query="test search query",
        mode="hybrid",
        top_k=5,
    )

    assert len(results) == 2
    # Verify metadata shows hybrid mode and fusion type
    assert results[0].metadata["fusion_type"] == "rrf"
    assert "timings" in results[0].metadata
