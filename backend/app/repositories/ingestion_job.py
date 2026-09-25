from datetime import datetime, timezone, timedelta
from typing import List, Optional, Sequence
import uuid
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ingestion_job import IngestionJob, IngestionJobStatus, IngestionStage


class IngestionJobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, job: IngestionJob) -> IngestionJob:
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def get_by_id(self, job_id: uuid.UUID) -> Optional[IngestionJob]:
        stmt = select(IngestionJob).where(IngestionJob.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_tenant(self, company_id: uuid.UUID, job_id: uuid.UUID) -> Optional[IngestionJob]:
        stmt = select(IngestionJob).where(
            IngestionJob.id == job_id,
            IngestionJob.company_id == company_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_job_for_document(
        self, company_id: uuid.UUID, document_id: uuid.UUID
    ) -> Optional[IngestionJob]:
        """Finds any job for the document currently in QUEUED or PROCESSING status."""
        stmt = (
            select(IngestionJob)
            .where(
                IngestionJob.company_id == company_id,
                IngestionJob.document_id == document_id,
                IngestionJob.status.in_([IngestionJobStatus.QUEUED, IngestionJobStatus.PROCESSING]),
            )
            .order_by(desc(IngestionJob.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_job_for_document(
        self, company_id: uuid.UUID, document_id: uuid.UUID
    ) -> Optional[IngestionJob]:
        stmt = (
            select(IngestionJob)
            .where(
                IngestionJob.company_id == company_id,
                IngestionJob.document_id == document_id,
            )
            .order_by(desc(IngestionJob.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_document(
        self, company_id: uuid.UUID, document_id: uuid.UUID
    ) -> Sequence[IngestionJob]:
        stmt = (
            select(IngestionJob)
            .where(
                IngestionJob.company_id == company_id,
                IngestionJob.document_id == document_id,
            )
            .order_by(desc(IngestionJob.created_at))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_active_jobs_for_tenant(
        self, company_id: uuid.UUID
    ) -> Sequence[IngestionJob]:
        stmt = select(IngestionJob).where(
            IngestionJob.company_id == company_id,
            IngestionJob.status.in_([IngestionJobStatus.QUEUED, IngestionJobStatus.PROCESSING]),
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_stale_processing_jobs(
        self, older_than_seconds: int = 300
    ) -> Sequence[IngestionJob]:
        """Finds jobs stuck in PROCESSING longer than threshold (indicates crashed worker)."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)
        stmt = select(IngestionJob).where(
            IngestionJob.status == IngestionJobStatus.PROCESSING,
            IngestionJob.started_at < cutoff,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(self, job: IngestionJob) -> IngestionJob:
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job
