import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from app.models.ai_employee import AIEmployeeStatus


class KnowledgeBaseSummary(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


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
    knowledge_base_ids: Optional[List[uuid.UUID]] = Field(default_factory=list)
    tools: Optional[List[str]] = Field(default_factory=list)


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
    knowledge_base_ids: Optional[List[uuid.UUID]] = None
    tools: Optional[List[str]] = None


class AIEmployeeRead(AIEmployeeBase):
    id: uuid.UUID
    company_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    knowledge_base_ids: List[uuid.UUID] = Field(default_factory=list)
    assigned_knowledge_bases: List[KnowledgeBaseSummary] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    public_id: Optional[str] = None
    is_published: bool = False
    allowed_domains: List[str] = Field(default_factory=list)
    widget_config: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_employee(cls, emp: Any) -> "AIEmployeeRead":
        """Helper to construct AIEmployeeRead with mapped assigned knowledge bases and tools."""
        kbs = getattr(emp, "knowledge_bases", []) or []
        kb_summaries = [
            KnowledgeBaseSummary(
                id=kb.id,
                name=kb.name,
                description=kb.description,
                status=kb.status.value if hasattr(kb.status, "value") else str(kb.status),
            )
            for kb in kbs
        ]
        kb_ids = [kb.id for kb in kbs]
        assigned_tools = getattr(emp, "assigned_tools", []) or []
        tool_names = [t.tool_name for t in assigned_tools]
        return cls(
            id=emp.id,
            company_id=emp.company_id,
            name=emp.name,
            role=emp.role,
            description=emp.description,
            personality=emp.personality,
            system_prompt=emp.system_prompt,
            language=emp.language,
            status=emp.status,
            avatar_config=emp.avatar_config or {},
            voice_config=emp.voice_config or {},
            created_at=emp.created_at,
            updated_at=emp.updated_at,
            knowledge_base_ids=kb_ids,
            assigned_knowledge_bases=kb_summaries,
            tools=tool_names,
            public_id=getattr(emp, "public_id", None),
            is_published=getattr(emp, "is_published", False),
            allowed_domains=getattr(emp, "allowed_domains", []) or [],
            widget_config=getattr(emp, "widget_config", {}) or {},
        )
