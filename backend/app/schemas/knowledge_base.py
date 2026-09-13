import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.models.knowledge_base import KnowledgeBaseStatus


class KnowledgeBaseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: KnowledgeBaseStatus = KnowledgeBaseStatus.ACTIVE


class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[KnowledgeBaseStatus] = None


class KnowledgeBaseRead(KnowledgeBaseBase):
    id: uuid.UUID
    company_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
