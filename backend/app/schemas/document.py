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
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


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
