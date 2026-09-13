import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent.base_tool import Tool
from app.services.agent.models import ToolContext, ToolPermission, ToolResult
from app.services.retrieval import RetrievalService

logger = logging.getLogger("app.services.agent.tools.product_search")


class ProductSearchInput(BaseModel):
    query: str = Field(..., description="Product name, feature, or keyword to search for.")
    category: Optional[str] = Field(None, description="Optional product category to narrow search.")
    max_results: int = Field(default=5, ge=1, le=10, description="Maximum number of products to return.")


class ProductSearchTool(Tool):
    """Searches company product knowledge.
    CRITICAL SECURITY INVARIANT:
    Product Search MUST use the active AI Employee's assigned Knowledge Base IDs
    and enforce both company_id and assigned knowledge_base_id filtering.
    It never searches unassigned company knowledge bases.
    """

    def __init__(self, retrieval_service: Optional[RetrievalService] = None):
        self.retrieval_service = retrieval_service or RetrievalService()

    @property
    def name(self) -> str:
        return "product_search"

    @property
    def description(self) -> str:
        return "Search company products, catalog items, and technical specifications within the employee's assigned knowledge access."

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.READ

    @property
    def input_schema(self) -> Dict[str, Any]:
        return ProductSearchInput.model_json_schema()

    async def execute(
        self,
        context: ToolContext,
        arguments: Dict[str, Any],
        session: AsyncSession,
    ) -> ToolResult:
        # Validate arguments against Pydantic schema
        try:
            validated = ProductSearchInput(**arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Invalid arguments: {str(e)}",
                display_message="Product search arguments failed validation.",
            )

        # STRICT SCOPING: If employee has 0 assigned KBs, return empty (no backdoor!)
        if not context.assigned_kb_ids:
            return ToolResult(
                success=True,
                data={"products": [], "message": "No product knowledge bases assigned to this employee."},
                display_message="No products found (no assigned knowledge bases).",
            )

        search_query = f"{validated.category} {validated.query}".strip() if validated.category else validated.query

        try:
            chunks = await self.retrieval_service.retrieve(
                company_id=context.company_id,
                query=search_query,
                knowledge_base_ids=context.assigned_kb_ids,
            )

            products = []
            for c in chunks[:validated.max_results]:
                products.append({
                    "title": c.header_path or c.source or "Product Information",
                    "snippet": c.text,
                    "score": round(c.score, 3),
                    "source": c.source,
                })

            return ToolResult(
                success=True,
                data={"products": products, "count": len(products)},
                display_message=f"Found {len(products)} relevant product results.",
            )
        except Exception as e:
            logger.error(f"ProductSearchTool execution error: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=str(e),
                display_message="Failed to search products due to an internal error.",
            )
