import logging
import sys
from typing import Any, Dict


SENSITIVE_KEYS = {"password", "token", "access_token", "secret", "authorization", "cookie"}


class StructuredFormatter(logging.Formatter):
    """Custom formatter ensuring structured key-value / JSON-like logging."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extra_fields = []
        for key, value in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                "message", "msg", "name", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName"
            ):
                if any(sens in key.lower() for sens in SENSITIVE_KEYS):
                    value = "[REDACTED]"
                extra_fields.append(f"{key}={value}")
        if extra_fields:
            return f"{base} | {' '.join(extra_fields)}"
        return base


def setup_logging(log_level: str = "INFO") -> None:
    """Configures application-wide structured logging."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    formatter = StructuredFormatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Suppress verbose third-party loggers
    logging.getLogger("uvicorn.access").handlers = [console_handler]
