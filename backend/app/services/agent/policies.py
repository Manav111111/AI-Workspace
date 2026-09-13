import hashlib
import json
from typing import Any, Dict
import uuid
from app.services.agent.base_tool import Tool
from app.services.agent.models import ToolPermission


class ToolPolicy:
    """Policy rules governing tool execution safety, confirmation, and idempotency."""

    @staticmethod
    def requires_confirmation(tool: Tool, arguments: Dict[str, Any]) -> bool:
        """Determines whether a tool execution requires explicit user confirmation.
        Default Phase 3 Policy:
        - READ operations execute automatically.
        - WRITE operations require confirmation.
        """
        return tool.permission == ToolPermission.WRITE

    @staticmethod
    def compute_idempotency_key(
        company_id: uuid.UUID,
        conversation_id: uuid.UUID,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> str:
        """Generates a deterministic hash for deduplicating identical write operations."""
        canonical_args = json.dumps(arguments, sort_keys=True)
        raw = f"{company_id}:{conversation_id}:{tool_name}:{canonical_args}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
