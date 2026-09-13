import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.business_entities import Order
from app.services.agent.base_tool import Tool
from app.services.agent.models import ToolContext, ToolErrorCode, ToolPermission, ToolResult

logger = logging.getLogger("app.services.agent.tools.order_lookup")


class OrderLookupInput(BaseModel):
    order_number: Optional[str] = Field(None, description="The order number or tracking reference (e.g. ORD-1001).")
    customer_identifier: Optional[str] = Field(None, description="Customer email address or phone number.")


class OrderLookupTool(Tool):
    """Looks up customer order information in PostgreSQL.
    STRICT TENANT ISOLATION:
    Always filters by context.company_id. Cannot see orders belonging to another company.
    """

    @property
    def name(self) -> str:
        return "order_lookup"

    @property
    def description(self) -> str:
        return "Look up status, items, tracking details, and total for customer orders using an order number or customer email/phone."

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.READ

    @property
    def input_schema(self) -> Dict[str, Any]:
        return OrderLookupInput.model_json_schema()

    async def execute(
        self,
        context: ToolContext,
        arguments: Dict[str, Any],
        session: AsyncSession,
    ) -> ToolResult:
        try:
            validated = OrderLookupInput(**arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                error_code=ToolErrorCode.VALIDATION_ERROR,
                error=f"Invalid arguments: {str(e)}",
                display_message="Please provide a valid order number or customer identifier.",
            )

        if not validated.order_number and not validated.customer_identifier:
            return ToolResult(
                success=False,
                error_code=ToolErrorCode.VALIDATION_ERROR,
                error="Either order_number or customer_identifier must be specified.",
                display_message="Please provide an order number or customer identifier to look up an order.",
            )

        # Build tenant-scoped query
        query = select(Order).where(Order.company_id == context.company_id)
        if validated.order_number:
            clean_num = validated.order_number.strip().upper()
            query = query.where(Order.order_number == clean_num)
        elif validated.customer_identifier:
            clean_ident = validated.customer_identifier.strip().lower()
            query = query.where(Order.customer_identifier == clean_ident)

        result = await session.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            ref = validated.order_number or validated.customer_identifier
            return ToolResult(
                success=False,
                error_code=ToolErrorCode.RESOURCE_NOT_FOUND,
                error=f"Order '{ref}' was not found in company records.",
                display_message=f"No order matching '{ref}' was found for your company.",
            )

        order_data = {
            "order_number": order.order_number,
            "status": order.status,
            "customer_identifier": order.customer_identifier,
            "items": order.items,
            "total": order.total,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
        }

        return ToolResult(
            success=True,
            data=order_data,
            display_message=f"Order {order.order_number} is currently {order.status}.",
        )
