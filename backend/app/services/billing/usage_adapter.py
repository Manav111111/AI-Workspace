from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("app.services.billing.usage_adapter")


@dataclass
class StandardizedUsage:
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    total_tokens: int
    usage_source: str  # "PROVIDER_REPORTED", "TOKENIZER_ESTIMATED", "UNKNOWN"


class UsageAdapter:
    """Normalizes raw provider usage payloads into a consistent, authoritative schema.
    Guarantees strict distinction between actual provider-reported measurements and estimates.
    """

    @classmethod
    def extract_usage(
        cls,
        provider: Any,
        raw_usage: Optional[Dict[str, Any]],
        messages: Optional[List[Dict[str, str]]] = None,
        generated_text: Optional[str] = None,
    ) -> StandardizedUsage:
        """Extracts token usage from provider payload or produces an explicitly labeled estimate."""
        clean_provider = str(provider).lower().strip() if isinstance(provider, str) else "unknown"


        if raw_usage and isinstance(raw_usage, dict):
            # 1. Google Gemini format: usageMetadata
            # { "promptTokenCount": 120, "candidatesTokenCount": 45, "totalTokenCount": 165, "cachedContentTokenCount": 0 }
            if "promptTokenCount" in raw_usage or "candidatesTokenCount" in raw_usage:
                prompt_tok = int(raw_usage.get("promptTokenCount") or 0)
                cand_tok = int(raw_usage.get("candidatesTokenCount") or 0)
                total_tok = int(raw_usage.get("totalTokenCount") or (prompt_tok + cand_tok))
                cached_tok = int(raw_usage.get("cachedContentTokenCount") or 0)
                return StandardizedUsage(
                    input_tokens=prompt_tok,
                    output_tokens=cand_tok,
                    cached_tokens=cached_tok,
                    total_tokens=total_tok,
                    usage_source="PROVIDER_REPORTED",
                )

            # 2. OpenAI format: usage
            # { "prompt_tokens": 120, "completion_tokens": 45, "total_tokens": 165, "prompt_tokens_details": {"cached_tokens": 0} }
            if "prompt_tokens" in raw_usage or "completion_tokens" in raw_usage:
                prompt_tok = int(raw_usage.get("prompt_tokens") or 0)
                comp_tok = int(raw_usage.get("completion_tokens") or 0)
                total_tok = int(raw_usage.get("total_tokens") or (prompt_tok + comp_tok))
                details = raw_usage.get("prompt_tokens_details") or {}
                cached_tok = int(details.get("cached_tokens") or 0)
                return StandardizedUsage(
                    input_tokens=prompt_tok,
                    output_tokens=comp_tok,
                    cached_tokens=cached_tok,
                    total_tokens=total_tok,
                    usage_source="PROVIDER_REPORTED",
                )

            # 3. Generic standard format (if already normalized)
            if "input_tokens" in raw_usage and "output_tokens" in raw_usage:
                in_tok = int(raw_usage.get("input_tokens") or 0)
                out_tok = int(raw_usage.get("output_tokens") or 0)
                cached_tok = int(raw_usage.get("cached_tokens") or 0)
                tot_tok = int(raw_usage.get("total_tokens") or (in_tok + out_tok))
                source = str(raw_usage.get("usage_source") or "PROVIDER_REPORTED")
                return StandardizedUsage(
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    cached_tokens=cached_tok,
                    total_tokens=tot_tok,
                    usage_source=source,
                )

        # 4. Tokenizer fallback estimation (1 token ≈ 4 characters)
        if messages or generated_text:
            input_chars = sum(len(m.get("content", "")) for m in (messages or []))
            output_chars = len(generated_text or "")
            est_input = max(1, input_chars // 4)
            est_output = max(1, output_chars // 4) if generated_text else 0
            return StandardizedUsage(
                input_tokens=est_input,
                output_tokens=est_output,
                cached_tokens=0,
                total_tokens=est_input + est_output,
                usage_source="TOKENIZER_ESTIMATED",
            )

        # 5. Unknown
        return StandardizedUsage(
            input_tokens=0,
            output_tokens=0,
            cached_tokens=0,
            total_tokens=0,
            usage_source="UNKNOWN",
        )
