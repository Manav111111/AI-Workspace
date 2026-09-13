from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ToolSummaryResponse(BaseModel):
    name: str
    description: str
    permission: str
    input_schema: Dict[str, Any]


class AssignEmployeeToolsRequest(BaseModel):
    tool_names: List[str] = Field(default_factory=list, description="List of tool names to assign to this employee")


class OrderItem(BaseModel):
    name: str
    quantity: int = 1
    unit_price: float = 0.0


class OrderCreateRequest(BaseModel):
    order_number: str = Field(..., max_length=50)
    customer_identifier: str = Field(..., max_length=255)
    status: str = Field(default="PENDING")
    items: List[Dict[str, Any]] = Field(default_factory=list)
    total: float = Field(default=0.0)


class OrderResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    order_number: str
    customer_identifier: str
    status: str
    items: List[Dict[str, Any]]
    total: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LeadResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    email: str
    phone: Optional[str] = None
    interest: Optional[str] = None
    source: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportTicketResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    ticket_number: str
    customer_email: Optional[str] = None
    subject: str
    description: str
    priority: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ToolExecutionResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    ai_employee_id: uuid.UUID
    conversation_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    tool_name: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    success: bool
    error_code: Optional[str] = None
    duration_ms: float
    idempotency_key: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PendingActionResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    ai_employee_id: uuid.UUID
    conversation_id: uuid.UUID
    tool_name: str
    validated_arguments: Dict[str, Any]
    status: str
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
