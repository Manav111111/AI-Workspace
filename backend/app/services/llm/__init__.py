from typing import Optional
from app.core.config import settings
from app.services.llm.base import LLMProvider, LLMResponse
from app.services.llm.mock_provider import MockLLMProvider
from app.services.llm.openai_provider import OpenAIProvider


def get_llm_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMProvider:
    """Factory to instantiate the configured LLMProvider.
    Defaults to OpenAIProvider if configured, or falls back cleanly to MockLLMProvider
    if provider is 'mock' or no API key is set in test/dev environments.
    """
    chosen = (provider_name or settings.LLM_PROVIDER).lower()
    chosen_key = api_key or settings.OPENAI_API_KEY
    chosen_base = base_url or settings.OPENAI_API_BASE
    chosen_model = model or settings.LLM_MODEL

    if chosen == "openai":
        if chosen_key:
            return OpenAIProvider(
                api_key=chosen_key,
                base_url=chosen_base,
                model=chosen_model,
                timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
            )
        # Fallback to mock provider in dev/test when no key is supplied
        return MockLLMProvider(model=f"mock-{chosen_model}")

    if chosen == "mock":
        return MockLLMProvider(model=f"mock-{chosen_model}")

    # Fallback default
    return MockLLMProvider(model=chosen_model)


__all__ = ["LLMProvider", "LLMResponse", "OpenAIProvider", "MockLLMProvider", "get_llm_provider"]
