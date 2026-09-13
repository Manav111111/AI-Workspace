from abc import ABC, abstractmethod
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent.models import ToolContext, ToolPermission, ToolResult


class Tool(ABC):
    """Abstract interface for all AI Employee business tools.
    Every tool receives an immutable server-generated ToolContext
    and executes inside a tenant transaction.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed description informing the LLM when and how to invoke this tool."""
        pass

    @property
    @abstractmethod
    def permission(self) -> ToolPermission:
        """Permission tier: READ (auto-executed) or WRITE (requires confirmation)."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON schema defining the expected arguments for the tool."""
        pass

    @abstractmethod
    async def execute(
        self,
        context: ToolContext,
        arguments: Dict[str, Any],
        session: AsyncSession,
    ) -> ToolResult:
        """Executes the tool logic with strict tenant scoping."""
        pass
