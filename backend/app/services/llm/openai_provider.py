import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.core.exceptions import AppException
from app.services.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger("app.services.llm.openai")


class LLMException(AppException):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message=message, status_code=status_code)


class LLMAuthenticationException(AppException):
    def __init__(self, message: str = "Invalid or unauthorized LLM API key"):
        super().__init__(message=message, status_code=401)


class LLMTimeoutException(AppException):
    def __init__(self, message: str = "LLM request timed out"):
        super().__init__(message=message, status_code=504)


class OpenAIProvider(LLMProvider):
    """LLM Provider for OpenAI and OpenAI-compatible endpoints (Ollama, vLLM, DeepSeek, LocalAI).
    Features controlled timeout and 1-attempt retry for transient errors, while immediately failing fast
    on authentication (401), forbidden (403), or validation (422) errors.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
        timeout_seconds: int = 60,
    ):
        self.api_key = api_key
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.model = model
        self.timeout = float(timeout_seconds)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        url = f"{self.base_url}/chat/completions"
        max_attempts = 2  # 1 initial + 1 controlled retry for transient errors

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            last_error: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    response = await client.post(url, headers=headers, json=payload)

                    # Check for non-retryable authentication & client errors
                    if response.status_code in (401, 403):
                        logger.error(f"LLM authentication failure: {response.status_code} - {response.text}")
                        raise LLMAuthenticationException(
                            f"LLM API authentication failed with status {response.status_code}"
                        )
                    if response.status_code == 422:
                        logger.error(f"LLM invalid request payload: {response.text}")
                        raise LLMException(f"Invalid request payload to LLM: {response.text}", status_code=422)

                    # Check for retryable server errors (5xx)
                    if response.status_code >= 500:
                        logger.warning(
                            f"Transient LLM server error on attempt {attempt}/{max_attempts}: {response.status_code}"
                        )
                        if attempt < max_attempts:
                            await asyncio.sleep(1.0)
                            continue
                        raise LLMException(
                            f"LLM upstream server returned {response.status_code}", status_code=502
                        )

                    # Successful response
                    data = response.json()
                    choices = data.get("choices", [])
                    if not choices:
                        raise LLMException("LLM returned empty choices in response", status_code=502)

                    choice = choices[0]
                    message_obj = choice.get("message", {})
                    content = message_obj.get("content") or ""
                    finish_reason = choice.get("finish_reason")
                    usage = data.get("usage")
                    tool_calls = message_obj.get("tool_calls")

                    return LLMResponse(
                        content=content,
                        model=data.get("model", self.model),
                        usage=usage,
                        finish_reason=finish_reason,
                        tool_calls=tool_calls,
                    )

                except (httpx.TimeoutException, asyncio.TimeoutError) as te:
                    logger.warning(f"LLM request timed out on attempt {attempt}/{max_attempts}: {te}")
                    last_error = te
                    if attempt < max_attempts:
                        await asyncio.sleep(1.0)
                        continue
                    raise LLMTimeoutException(f"LLM request timed out after {self.timeout}s")

                except (httpx.NetworkError, httpx.RemoteProtocolError) as ne:
                    logger.warning(f"LLM network error on attempt {attempt}/{max_attempts}: {ne}")
                    last_error = ne
                    if attempt < max_attempts:
                        await asyncio.sleep(1.0)
                        continue
                    raise LLMException(f"LLM network error: {ne}", status_code=502)

                except (LLMAuthenticationException, LLMException):
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error during LLM generation: {e}")
                    raise LLMException(f"Unexpected LLM generation error: {e}", status_code=500)

            raise LLMException(f"Failed to generate response from LLM: {last_error}", status_code=502)
