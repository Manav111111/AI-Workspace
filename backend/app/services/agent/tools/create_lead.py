import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.business_entities import Lead
from app.services.agent.base_tool import Tool
from app.services.agent.models import ToolContext, ToolErrorCode, ToolPermission, ToolResult

logger = logging.getLogger("app.services.agent.tools.create_lead")


class CreateLeadInput(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Full name of the prospective customer/lead.")
    email: str = Field(..., description="Email address of the lead.")
    phone: Optional[str] = Field(None, max_length=50, description="Optional phone number.")
    interest: Optional[str] = Field(None, description="Products, services, or topics the lead is interested in.")


class CreateLeadTool(Tool):
    """Captures new sales leads into the tenant database.
    PERMISSION: WRITE (requires confirmation or pre-validated pending action).
    """

    @property
    def name(self) -> str:
        return "create_lead"

    @property
    def description(self) -> str:
        return "Capture a new sales lead or customer contact details when a user expresses interest in products or services."

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.WRITE

    @property
    def input_schema(self) -> Dict[str, Any]:
        return CreateLeadInput.model_json_schema()

    async def execute(
        self,
        context: ToolContext,
        arguments: Dict[str, Any],
        session: AsyncSession,
    ) -> ToolResult:
        try:
            validated = CreateLeadInput(**arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                error_code=ToolErrorCode.VALIDATION_ERROR,
                error=f"Invalid lead arguments: {str(e)}",
                display_message="Please provide a valid name and email address for the lead.",
            )

        lead = Lead(
            company_id=context.company_id,
            name=validated.name.strip(),
            email=validated.email.strip().lower(),
            phone=validated.phone.strip() if validated.phone else None,
            interest=validated.interest.strip() if validated.interest else None,
            source="ai_employee_chat",
            status="new",
        )
        session.add(lead)
        await session.flush()
        await session.refresh(lead)

        return ToolResult(
            success=True,
            data={
                "lead_id": str(lead.id),
                "name": lead.name,
                "email": lead.email,
                "status": lead.status,
                "created_at": lead.created_at.isoformat(),
            },
            display_message=f"Lead for {lead.name} ({lead.email}) was successfully created.",
        )
