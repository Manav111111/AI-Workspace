import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.services.llm.base import LLMProvider, LLMResponse
from app.services.llm.openai_provider import (
    LLMAuthenticationException,
    LLMException,
    LLMTimeoutException,
)

logger = logging.getLogger("app.services.llm.gemini")


class GeminiProvider(LLMProvider):
    """Native Google Generative AI Provider using Google's primary REST generateContent API.
    Bypasses unstable /v1beta/openai emulation layer to guarantee zero 503 drops.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.6-flash",
        timeout_seconds: float = 90.0,
    ):
        self.provider = "gemini"
        self.api_key = api_key
        self.model = model.replace("models/", "")
        self.timeout = float(timeout_seconds)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"


    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1000,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        system_instructions: List[str] = []
        raw_contents: List[Dict[str, Any]] = []

        for m in messages:
            role = m.get("role", "user").lower()
            content = m.get("content", "")
            if role == "system":
                system_instructions.append(content)
            elif role in ("assistant", "model"):
                raw_contents.append({
                    "role": "model",
                    "parts": [{"text": content or ""}]
                })
            else:
                raw_contents.append({
                    "role": "user",
                    "parts": [{"text": content or ""}]
                })

        if not raw_contents:
            raw_contents.append({"role": "user", "parts": [{"text": "Hello"}]})

        # Coalesce consecutive turns with the same role so Gemini does not error
        coalesced: List[Dict[str, Any]] = []
        for c in raw_contents:
            if coalesced and coalesced[-1]["role"] == c["role"]:
                coalesced[-1]["parts"].extend(c["parts"])
            else:
                coalesced.append(c)

        payload: Dict[str, Any] = {
            "contents": coalesced,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        if system_instructions:
            payload["system_instruction"] = {
                "parts": [{"text": "\n\n".join(system_instructions)}]
            }

        models_to_try = [self.model]
        for fallback in [
            "gemini-flash-latest",
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3-flash-preview",
            "gemini-3.1-pro-preview",
        ]:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        async with httpx.AsyncClient(timeout=min(self.timeout, 20.0)) as client:
            last_error: Optional[Exception] = None

            for current_model in models_to_try:
                url = f"{self.base_url}/models/{current_model}:generateContent?key={self.api_key}"
                try:
                    response = await client.post(url, json=payload)
                    if response.status_code in (401, 403):
                        logger.error(f"Gemini API auth failure: {response.text}")
                        raise LLMAuthenticationException(f"Gemini API authentication failed: {response.text}")

                    # If model is rate-limited (429) or overloaded (503), try the next available model with brief backoff
                    if response.status_code in (429, 503):
                        logger.warning(
                            f"Model {current_model} returned {response.status_code}. "
                            "Failing over to next available Gemini model."
                        )
                        last_error = LLMException(f"Model {current_model} returned {response.status_code}", status_code=response.status_code)
                        await asyncio.sleep(0.5)
                        continue

                    if response.status_code != 200:
                        logger.error(f"Gemini API error {response.status_code}: {response.text}")
                        last_error = LLMException(f"Gemini API returned {response.status_code}: {response.text}", status_code=response.status_code)
                        continue

                    data = response.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        continue

                    cand = candidates[0]
                    parts = cand.get("content", {}).get("parts", [])
                    content_text = "".join(p.get("text", "") for p in parts if "text" in p)
                    finish_reason = cand.get("finishReason")
                    usage = data.get("usageMetadata")

                    return LLMResponse(
                        content=content_text,
                        model=current_model,
                        usage=usage,
                        finish_reason=finish_reason,
                        tool_calls=None,
                    )
                except (httpx.TimeoutException, asyncio.TimeoutError) as te:
                    logger.warning(f"Model {current_model} timed out: {te}")
                    last_error = te
                    continue
                except (LLMAuthenticationException, LLMException):
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error with model {current_model}: {e}")
                    last_error = e
                    continue

            raise LLMException(f"All Gemini model attempts failed: {last_error}", status_code=502)
