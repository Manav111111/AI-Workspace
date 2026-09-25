import re
from typing import Any, Dict, List, Set, Union


class TelemetryRedactor:
    """Centralized redaction policy for OpenTelemetry spans, audit logs, and diagnostic traces.
    Strictly scrubs API keys, bearer tokens, passwords, private credentials,
    and sensitive parameters to prevent secret leakage in telemetry backends.
    """

    # Exact or substring key matches that should always have their values redacted
    SENSITIVE_KEY_PATTERNS = {
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "authorization",
        "auth_header",
        "bearer",
        "private_key",
        "credential",
        "client_secret",
        "cookie",
        "session_token",
    }

    # Regex patterns matching high-entropy secrets and credential formats
    SECRET_REGEX_PATTERNS = [
        # Bearer tokens
        (re.compile(r"Bearer\s+([A-Za-z0-9\-\._~\+\/]+=*)", re.IGNORECASE), "Bearer [REDACTED]"),
        # Google API keys (AIza...)
        (re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "[REDACTED_GEMINI_KEY]"),
        # OpenAI API keys (sk-...)
        (re.compile(r"sk-[A-Za-z0-9\-_]{20,}"), "[REDACTED_OPENAI_KEY]"),
        # Basic auth
        (re.compile(r"Basic\s+([A-Za-z0-9\+/]+=*)", re.IGNORECASE), "Basic [REDACTED]"),
        # Password parameter in URLs or query strings
        (re.compile(r"(password|pwd|secret)=([^&\s]+)", re.IGNORECASE), r"\1=[REDACTED]"),
    ]

    @classmethod
    def redact_string(cls, text: str) -> str:
        """Applies regex pattern scrubs to arbitrary string content."""
        if not text:
            return text
        scrubbed = text
        for pattern, replacement in cls.SECRET_REGEX_PATTERNS:
            scrubbed = pattern.sub(replacement, scrubbed)
        return scrubbed

    @classmethod
    def _is_sensitive_key(cls, key: str) -> bool:
        lower_key = str(key).lower().replace("-", "_")
        for sensitive in cls.SENSITIVE_KEY_PATTERNS:
            if sensitive in lower_key:
                return True
        return False

    @classmethod
    def redact_dict(cls, data: Any, max_string_len: int = 1000) -> Any:
        """Recursively traverses dictionaries, lists, and primitives,
        masking sensitive keys and scrubbing sensitive strings.
        """
        if isinstance(data, dict):
            redacted = {}
            for k, v in data.items():
                if cls._is_sensitive_key(str(k)):
                    redacted[k] = "[REDACTED]"
                else:
                    redacted[k] = cls.redact_dict(v, max_string_len=max_string_len)
            return redacted
        elif isinstance(data, list):
            return [cls.redact_dict(item, max_string_len=max_string_len) for item in data]
        elif isinstance(data, tuple):
            return tuple(cls.redact_dict(item, max_string_len=max_string_len) for item in data)
        elif isinstance(data, str):
            scrubbed = cls.redact_string(data)
            if len(scrubbed) > max_string_len:
                return scrubbed[:max_string_len] + "... [TRUNCATED]"
            return scrubbed
        else:
            return data

    @classmethod
    def redact_attributes(cls, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizes span attributes, ensuring all values are safe for telemetry export."""
        if not attributes:
            return {}
        return cls.redact_dict(attributes)
