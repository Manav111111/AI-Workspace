from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    ai_employee_id: uuid.UUID
    title: Optional[str] = Field(None, max_length=255)


class ConversationResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    ai_employee_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    title: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CitationResponse(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    header_path: Optional[str] = None
    score: float
    preview: Optional[str] = None


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="User message content")


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    company_id: uuid.UUID
    role: str
    content: str
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    citations: List[CitationResponse] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
