from typing import Dict, List, Optional
from app.services.agent.base_tool import Tool
from app.services.agent.models import ToolDefinition
from app.services.agent.tools import (
    ProductSearchTool,
    OrderLookupTool,
    CreateLeadTool,
    CreateSupportTicketTool,
)


class ToolRegistry:
    """Central registry of all available business tools.
    Allows dynamic lookup, validation, and filtering by AI Employee assignments.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        # Register default Phase 3 catalog
        self.register(ProductSearchTool())
        self.register(OrderLookupTool())
        self.register(CreateLeadTool())
        self.register(CreateSupportTicketTool())

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_available_tools(self) -> List[ToolDefinition]:
        """Returns all registered tool schemas in system."""
        return [
            ToolDefinition(
                name=t.name,
                description=t.description,
                permission=t.permission,
                input_schema=t.input_schema,
            )
            for t in self._tools.values()
        ]

    def get_tools_for_employee(self, assigned_names: List[str]) -> List[Tool]:
        """Filters registered tools down strictly to what the active AI Employee has been assigned."""
        name_set = set(assigned_names)
        return [t for name, t in self._tools.items() if name in name_set]


# Global singleton registry instance
tool_registry = ToolRegistry()
