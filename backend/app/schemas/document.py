import datetime
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, ConfigDict
from app.models.document import DocumentStatus


class DocumentRead(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    filename: str
    original_filename: str
    file_type: str
    mime_type: str
    file_size: int
    status: DocumentStatus
    error_message: Optional[str] = None
    document_metadata: Dict[str, Any]
    job_id: Optional[uuid.UUID] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    filename: str
    original_filename: Optional[str] = None
    file_size: int
    created_at: datetime.datetime


class DocumentStatusResponse(BaseModel):
    document_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    status: str
    progress_percent: int = 0
    current_stage: str = "QUEUED"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    attempt_count: int = 0
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None


class DocumentChunkRead(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    token_count: int
    chunk_metadata: Dict[str, Any]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
