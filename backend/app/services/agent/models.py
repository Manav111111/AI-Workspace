from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class ToolPermission(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


class ToolErrorCode(str, Enum):
    TOOL_NOT_ASSIGNED = "TOOL_NOT_ASSIGNED"
    TOOL_NOT_AUTHORIZED = "TOOL_NOT_AUTHORIZED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    TENANT_ACCESS_DENIED = "TENANT_ACCESS_DENIED"


@dataclass(frozen=True)
class ToolContext:
    """Immutable, server-generated context passed to every tool execution.
    The LLM has zero authority to supply or override these security attributes.
    """
    company_id: uuid.UUID
    ai_employee_id: uuid.UUID
    conversation_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    assigned_kb_ids: List[uuid.UUID] = field(default_factory=list)


@dataclass
class ToolResult:
    """Normalized response from tool execution."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[ToolErrorCode] = None
    display_message: Optional[str] = None
    pending_action_id: Optional[uuid.UUID] = None


class ToolCall(BaseModel):
    """Structured tool invocation request from the LLM or agent planner."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """Schema descriptor of a tool for consumption by the LLM."""
    name: str
    description: str
    permission: ToolPermission
    input_schema: Dict[str, Any]
