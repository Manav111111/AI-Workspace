from datetime import datetime, timezone, timedelta
import io
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.company import Company
from app.models.document import Document, DocumentStatus
from app.models.ingestion_job import IngestionJob, IngestionJobStatus, IngestionStage
from app.models.knowledge_base import KnowledgeBase
from app.models.membership import Membership, MembershipRole
from app.models.user import User
from app.repositories.ingestion_job import IngestionJobRepository
from app.services.retrieval import global_bm25_cache
from app.workers.ingestion_worker import IngestionWorker


@pytest.fixture
async def test_env(db_session: AsyncSession):
    # Setup company A and user A
    company = Company(name="Acme Corp", slug=f"acme-{uuid.uuid4().hex[:6]}")
    user = User(email=f"admin-{uuid.uuid4().hex[:6]}@acme.com", full_name="Admin Acme", hashed_password="pw")
    db_session.add_all([company, user])
    await db_session.flush()

    membership = Membership(user_id=user.id, company_id=company.id, role=MembershipRole.OWNER)
    kb = KnowledgeBase(company_id=company.id, name="HR Knowledge", description="HR Docs")
    db_session.add_all([membership, kb])

    # Setup company B for isolation checks
    company_b = Company(name="Beta Corp", slug=f"beta-{uuid.uuid4().hex[:6]}")
    user_b = User(email=f"user-{uuid.uuid4().hex[:6]}@beta.com", full_name="User Beta", hashed_password="pw")
    db_session.add_all([company_b, user_b])
    await db_session.flush()

    membership_b = Membership(user_id=user_b.id, company_id=company_b.id, role=MembershipRole.OWNER)
    kb_b = KnowledgeBase(company_id=company_b.id, name="Beta KB", description="Beta Docs")
    db_session.add_all([membership_b, kb_b])

    await db_session.commit()

    return {
        "company_a": company,
        "user_a": user,
        "kb_a": kb,
        "company_b": company_b,
        "user_b": user_b,
        "kb_b": kb_b,
    }


@pytest.mark.asyncio
async def test_async_upload_returns_202_accepted(client: AsyncClient, test_env: dict):
    company = test_env["company_a"]
    user = test_env["user_a"]
    kb = test_env["kb_a"]

    from app.core.security import create_access_token
    token = create_access_token(subject=str(user.id))

    file_content = b"# Company Leave Policy\nFull-time employees receive 20 days paid leave per year."
    files = {"file": ("leave_policy.md", io.BytesIO(file_content), "text/markdown")}

    response = await client.post(
        f"/api/v1/knowledge-bases/{kb.id}/documents",
        files=files,
        headers={"Authorization": f"Bearer {token}", "X-Company-ID": str(company.id)},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "QUEUED"
    assert "document_id" in data
    assert "job_id" in data
    assert data["original_filename"] == "leave_policy.md"


@pytest.mark.asyncio
async def test_ingestion_worker_stages_and_bm25_invalidation(db_session: AsyncSession, test_env: dict):
    company = test_env["company_a"]
    kb = test_env["kb_a"]

    # 1. Warm BM25 cache for company
    from app.services.retrieval.bm25 import BM25Index
    dummy_index = BM25Index(chunk_ids=["chunk-test-1"], chunk_texts=["Sample document chunk token."])
    global_bm25_cache.set(company.id, [kb.id], dummy_index, {})
    assert global_bm25_cache.get(company.id, [kb.id]) is not None

    # 2. Create document and job
    doc = Document(
        company_id=company.id,
        knowledge_base_id=kb.id,
        filename="async_test.txt",
        original_filename="async_test.txt",
        file_type="txt",
        mime_type="text/plain",
        file_size=50,
        storage_path="uploads/test_doc.txt",
        status=DocumentStatus.QUEUED,
        document_metadata={},
    )
    db_session.add(doc)
    await db_session.flush()

    job = IngestionJob(
        company_id=company.id,
        knowledge_base_id=kb.id,
        document_id=doc.id,
        status=IngestionJobStatus.QUEUED,
        max_attempts=3,
        progress_percent=0,
        current_stage=IngestionStage.QUEUED.value,
    )
    db_session.add(job)
    await db_session.commit()

    # Mock storage so it returns content
    from app.services.storage import StorageService
    class MockStorage(StorageService):
        async def save(self, *args, **kwargs): return "uploads/test_doc.txt"
        async def get(self, *args, **kwargs): return b"Async Ingestion Pipeline Test Content with important keywords."
        async def delete(self, *args, **kwargs): pass
        async def exists(self, *args, **kwargs): return True

    worker = IngestionWorker(storage_service=MockStorage())
    completed_job = await worker.process_job(job.id)

    assert completed_job is not None
    assert completed_job.status == IngestionJobStatus.COMPLETED
    assert completed_job.progress_percent == 100
    assert completed_job.current_stage == IngestionStage.COMPLETED.value

    # Check BM25 cache was invalidated for company A
    assert global_bm25_cache.get(company.id, [kb.id]) is None


@pytest.mark.asyncio
async def test_worker_idempotency_ignores_already_processing(db_session: AsyncSession, test_env: dict):
    company = test_env["company_a"]
    kb = test_env["kb_a"]

    job = IngestionJob(
        company_id=company.id,
        knowledge_base_id=kb.id,
        document_id=uuid.uuid4(),
        status=IngestionJobStatus.PROCESSING,
        max_attempts=3,
        progress_percent=50,
        current_stage=IngestionStage.CHUNKING.value,
    )
    db_session.add(job)
    await db_session.commit()

    worker = IngestionWorker()
    result = await worker.process_job(job.id)

    # Should remain in PROCESSING without re-running or erroring
    assert result.status == IngestionJobStatus.PROCESSING
    assert result.progress_percent == 50


@pytest.mark.asyncio
async def test_stale_job_recovery(db_session: AsyncSession, test_env: dict):
    company = test_env["company_a"]
    kb = test_env["kb_a"]

    # Create job stuck in PROCESSING started 10 minutes ago
    ten_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    job = IngestionJob(
        company_id=company.id,
        knowledge_base_id=kb.id,
        document_id=uuid.uuid4(),
        status=IngestionJobStatus.PROCESSING,
        started_at=ten_mins_ago,
        attempt_count=1,
        max_attempts=3,
        progress_percent=25,
        current_stage=IngestionStage.PARSING.value,
    )
    db_session.add(job)
    await db_session.commit()

    worker = IngestionWorker()
    recovered_count = await worker.recover_stale_jobs(timeout_seconds=300)
    assert recovered_count >= 1

    await db_session.refresh(job)
    assert job.status == IngestionJobStatus.QUEUED
    assert job.error_code == "STALE_JOB_TIMEOUT"


@pytest.mark.asyncio
async def test_document_status_api_and_retry(client: AsyncClient, db_session: AsyncSession, test_env: dict):
    company = test_env["company_a"]
    user = test_env["user_a"]
    kb = test_env["kb_a"]

    from app.core.security import create_access_token
    token = create_access_token(subject=str(user.id))
    headers = {"Authorization": f"Bearer {token}", "X-Company-ID": str(company.id)}

    doc = Document(
        company_id=company.id,
        knowledge_base_id=kb.id,
        filename="failed_doc.pdf",
        original_filename="failed_doc.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=1024,
        storage_path="uploads/failed_doc.pdf",
        status=DocumentStatus.FAILED,
        error_message="Simulated temporary embedding failure",
        document_metadata={},
    )
    db_session.add(doc)
    await db_session.flush()

    job = IngestionJob(
        company_id=company.id,
        knowledge_base_id=kb.id,
        document_id=doc.id,
        status=IngestionJobStatus.FAILED,
        attempt_count=3,
        max_attempts=3,
        progress_percent=60,
        current_stage=IngestionStage.EMBEDDING.value,
        error_code="EMBEDDING_RATE_LIMIT",
        error_message="Simulated temporary embedding failure",
    )
    db_session.add(job)
    await db_session.commit()

    # 1. Check status endpoint
    status_resp = await client.get(f"/api/v1/documents/{doc.id}/status", headers=headers)
    assert status_resp.status_code == 200
    st_data = status_resp.json()
    assert st_data["status"] == "FAILED"
    assert st_data["error_code"] == "EMBEDDING_RATE_LIMIT"

    # 2. Retry failed document
    retry_resp = await client.post(f"/api/v1/documents/{doc.id}/retry", headers=headers)
    assert retry_resp.status_code == 202
    retry_data = retry_resp.json()
    assert retry_data["status"] == "QUEUED"
    assert retry_data["job_id"] != str(job.id)


@pytest.mark.asyncio
async def test_tenant_isolation_on_document_status_and_retry(client: AsyncClient, db_session: AsyncSession, test_env: dict):
    company_a = test_env["company_a"]
    kb_a = test_env["kb_a"]
    user_b = test_env["user_b"]
    company_b = test_env["company_b"]

    doc_a = Document(
        company_id=company_a.id,
        knowledge_base_id=kb_a.id,
        filename="company_a_secret.txt",
        original_filename="company_a_secret.txt",
        file_type="txt",
        mime_type="text/plain",
        file_size=100,
        storage_path="uploads/company_a_secret.txt",
        status=DocumentStatus.PROCESSED,
        document_metadata={},
    )
    db_session.add(doc_a)
    await db_session.commit()

    from app.core.security import create_access_token
    token_b = create_access_token(subject=str(user_b.id))
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Company-ID": str(company_b.id)}

    # User from Company B attempts to read Company A's document status
    status_resp = await client.get(f"/api/v1/documents/{doc_a.id}/status", headers=headers_b)
    assert status_resp.status_code == 404

    # User from Company B attempts to retry Company A's document
    retry_resp = await client.post(f"/api/v1/documents/{doc_a.id}/retry", headers=headers_b)
    assert retry_resp.status_code == 404
