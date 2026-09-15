import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class PublicEmployeeConfigResponse(BaseModel):
    """Sanitized public metadata for an AI Employee.
    Strictly prevents leakage of system prompts, internal database UUIDs, company credentials, or tools internals.
    """
    public_id: str
    name: str
    role: str
    description: Optional[str] = None
    language: str
    avatar_config: Dict[str, Any] = Field(default_factory=dict)
    widget_config: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class PublicSessionCreateRequest(BaseModel):
    """Anonymous visitor session creation request."""
    visitor_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Untrusted client correlation identifier from browser localStorage"
    )


class PublicSessionResponse(BaseModel):
    """Session credentials returned once upon initialization."""
    session_token: str = Field(description="Raw bearer token for subsequent public API calls")
    expires_at: datetime.datetime
    employee: PublicEmployeeConfigResponse


class PublicMessageCreate(BaseModel):
    """Visitor message payload."""
    message: str = Field(
        default="",
        max_length=1000,
        description="Visitor input message (enforced max 1000 chars)"
    )
    pending_action_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Server-generated pending action ID to confirm or cancel"
    )
    confirm_action: bool = Field(
        default=False,
        description="Confirmation verdict for the existing server-side pending action"
    )


class PublicCitation(BaseModel):
    document_name: str
    page_number: Optional[int] = None
    header_path: Optional[str] = None
    score: float


class PublicPendingConfirmation(BaseModel):
    pending_action_id: str
    tool_name: str
    arguments: Dict[str, Any]
    message: Optional[str] = None


class PublicChatResponse(BaseModel):
    """Normalized response for public website widget."""
    message: str
    citations: List[PublicCitation] = Field(default_factory=list)
    tool_activity: List[str] = Field(default_factory=list)
    pending_confirmation: Optional[PublicPendingConfirmation] = None
    created_at: datetime.datetime


class PublicMessageHistoryItem(BaseModel):
    role: str
    content: str
    citations: List[PublicCitation] = Field(default_factory=list)
    tool_activity: List[str] = Field(default_factory=list)
    created_at: datetime.datetime


class EmployeePublishRequest(BaseModel):
    """Publishing state toggle."""
    is_published: bool = True
    allowed_domains: Optional[List[str]] = Field(
        default_factory=list,
        description="Allowed origins/domains. Empty means development/open."
    )


class EmployeeWidgetConfigRequest(BaseModel):
    """Customization of the embeddable widget."""
    primary_color: Optional[str] = Field(default="#4f46e5")
    theme: Optional[str] = Field(default="dark")  # "light", "dark", "system"
    position: Optional[str] = Field(default="bottom-right")  # "bottom-right", "bottom-left"
    brand_name: Optional[str] = None
    welcome_message: Optional[str] = Field(default="Hi! How can I help you today?")
    logo_url: Optional[str] = None
    allowed_domains: Optional[List[str]] = Field(default_factory=list)


class EmployeeEmbedCodeResponse(BaseModel):
    """Embed code metadata for company dashboard."""
    public_id: str
    is_published: bool
    widget_script_url: str
    embed_snippet: str
    preview_url: str
    allowed_domains: List[str]
    widget_config: Dict[str, Any]
