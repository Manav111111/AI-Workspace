from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional


@dataclass
class LLMResponse:
    """Normalized response schema from an LLM provider."""
    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


class LLMProvider(ABC):
    """Abstract interface for LLM completion providers.
    Decouples the conversational brain from any specific model vendor (OpenAI, Anthropic, Ollama, vLLM).
    """

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """Generates a non-streaming grounded response for the provided message sequence."""
        pass

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ) -> AsyncIterator[str]:
        """Future-ready interface for streaming tokens."""
        raise NotImplementedError("Streaming is not yet implemented for this provider")
