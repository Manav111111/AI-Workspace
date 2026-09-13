import pytest
from app.services.agent.base_tool import Tool
from app.services.agent.models import ToolContext, ToolPermission, ToolResult
from app.services.agent.tool_registry import ToolRegistry, tool_registry


def test_default_tool_registry_contains_initial_tools():
    """Verify that the ToolRegistry initializes with the four core Phase 3 tools."""
    tools = tool_registry.list_available_tools()
    tool_names = {t.name for t in tools}

    assert "product_search" in tool_names
    assert "order_lookup" in tool_names
    assert "create_lead" in tool_names
    assert "create_support_ticket" in tool_names


def test_tool_permissions_classification():
    """Verify READ vs WRITE permission classification on core tools."""
    prod_tool = tool_registry.get("product_search")
    assert prod_tool is not None
    assert prod_tool.permission == ToolPermission.READ

    order_tool = tool_registry.get("order_lookup")
    assert order_tool is not None
    assert order_tool.permission == ToolPermission.READ

    lead_tool = tool_registry.get("create_lead")
    assert lead_tool is not None
    assert lead_tool.permission == ToolPermission.WRITE

    ticket_tool = tool_registry.get("create_support_ticket")
    assert ticket_tool is not None
    assert ticket_tool.permission == ToolPermission.WRITE


def test_tool_schema_export():
    """Verify input schemas are properly exported as JSON Schema dictionaries."""
    order_tool = tool_registry.get("order_lookup")
    assert order_tool is not None
    schema = order_tool.input_schema

    assert isinstance(schema, dict)
    assert "properties" in schema
    assert "order_number" in schema["properties"]
    assert "customer_identifier" in schema["properties"]


def test_filter_tools_for_employee():
    """Verify that get_tools_for_employee only returns explicitly assigned tools."""
    registry = ToolRegistry()

    # Employee assigned only product_search
    eng_tools = registry.get_tools_for_employee(["product_search"])
    assert len(eng_tools) == 1
    assert eng_tools[0].name == "product_search"

    # Support employee assigned order_lookup and create_support_ticket
    supp_tools = registry.get_tools_for_employee(["order_lookup", "create_support_ticket"])
    assert len(supp_tools) == 2
    names = {t.name for t in supp_tools}
    assert names == {"order_lookup", "create_support_ticket"}

    # Employee with unassigned tools gets empty list
    empty_tools = registry.get_tools_for_employee([])
    assert len(empty_tools) == 0
