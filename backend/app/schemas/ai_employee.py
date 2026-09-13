import datetime
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.models.ai_employee import AIEmployeeStatus


class AIEmployeeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    personality: Optional[str] = None
    system_prompt: Optional[str] = None
    language: str = Field(default="en", max_length=10)
    status: AIEmployeeStatus = AIEmployeeStatus.DRAFT
    avatar_config: Dict[str, Any] = Field(default_factory=dict)
    voice_config: Dict[str, Any] = Field(default_factory=dict)


class AIEmployeeCreate(AIEmployeeBase):
    pass


class AIEmployeeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    personality: Optional[str] = None
    system_prompt: Optional[str] = None
    language: Optional[str] = Field(None, max_length=10)
    status: Optional[AIEmployeeStatus] = None
    avatar_config: Optional[Dict[str, Any]] = None
    voice_config: Optional[Dict[str, Any]] = None


class AIEmployeeRead(AIEmployeeBase):
    id: uuid.UUID
    company_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
