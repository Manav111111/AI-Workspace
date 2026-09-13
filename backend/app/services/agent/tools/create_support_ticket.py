import logging
import random
import string
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.business_entities import SupportTicket, TicketPriority, TicketStatus
from app.services.agent.base_tool import Tool
from app.services.agent.models import ToolContext, ToolErrorCode, ToolPermission, ToolResult

logger = logging.getLogger("app.services.agent.tools.create_support_ticket")


class CreateSupportTicketInput(BaseModel):
    subject: str = Field(..., min_length=3, max_length=255, description="Brief summary of the support issue or request.")
    description: str = Field(..., min_length=5, description="Detailed explanation of the issue, question, or error.")
    priority: str = Field(default="medium", description="Priority level: low, medium, or high.")
    customer_email: Optional[str] = Field(None, description="Optional customer email address for follow-up.")


class CreateSupportTicketTool(Tool):
    """Creates a customer support ticket in the tenant database.
    PERMISSION: WRITE (requires confirmation or pre-validated pending action).
    """

    @property
    def name(self) -> str:
        return "create_support_ticket"

    @property
    def description(self) -> str:
        return "Create a new customer support or technical escalation ticket for issues, bugs, refund inquiries, or account help."

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.WRITE

    @property
    def input_schema(self) -> Dict[str, Any]:
        return CreateSupportTicketInput.model_json_schema()

    async def execute(
        self,
        context: ToolContext,
        arguments: Dict[str, Any],
        session: AsyncSession,
    ) -> ToolResult:
        try:
            validated = CreateSupportTicketInput(**arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                error_code=ToolErrorCode.VALIDATION_ERROR,
                error=f"Invalid ticket arguments: {str(e)}",
                display_message="Please provide a valid subject and description for the support ticket.",
            )

        # Normalize priority
        p_raw = validated.priority.strip().upper()
        priority_val = p_raw if p_raw in (TicketPriority.LOW.value, TicketPriority.MEDIUM.value, TicketPriority.HIGH.value) else TicketPriority.MEDIUM.value

        # Generate unique ticket number e.g. TCK-8492
        suffix = "".join(random.choices(string.digits, k=4))
        ticket_num = f"TCK-{suffix}"

        ticket = SupportTicket(
            company_id=context.company_id,
            ticket_number=ticket_num,
            customer_email=validated.customer_email.strip().lower() if validated.customer_email else None,
            subject=validated.subject.strip(),
            description=validated.description.strip(),
            priority=priority_val,
            status=TicketStatus.OPEN.value,
        )
        session.add(ticket)
        await session.flush()
        await session.refresh(ticket)

        return ToolResult(
            success=True,
            data={
                "ticket_id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
                "subject": ticket.subject,
                "priority": ticket.priority,
                "status": ticket.status,
                "created_at": ticket.created_at.isoformat(),
            },
            display_message=f"Support ticket {ticket.ticket_number} was successfully created.",
        )
