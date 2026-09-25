import asyncio
from contextvars import ContextVar
import datetime
import logging
import secrets
import time
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.observability import TraceSummary
from app.services.observability.redactor import TelemetryRedactor

logger = logging.getLogger("app.services.observability.tracer")

# ContextVar tracking the current active Span for async execution context propagation
_current_span: ContextVar[Optional["Span"]] = ContextVar("current_span", default=None)
# ContextVar tracking all spans collected within the active trace
_active_trace_collector: ContextVar[Optional["TraceCollector"]] = ContextVar("active_trace_collector", default=None)


def generate_trace_id() -> str:
    """Generates a standard 32-character W3C-compliant hexadecimal trace ID."""
    return secrets.token_hex(16)


def generate_span_id() -> str:
    """Generates a standard 16-character W3C-compliant hexadecimal span ID."""
    return secrets.token_hex(8)


class Span:
    """OpenTelemetry-compatible representation of an execution unit of work."""

    def __init__(
        self,
        name: str,
        trace_id: str,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.trace_id = trace_id
        self.span_id = span_id or generate_span_id()
        self.parent_span_id = parent_span_id
        self.start_time = time.perf_counter()
        self.start_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0
        self.status = "OK"  # "OK" or "ERROR"
        self.status_description: Optional[str] = None
        self.attributes: Dict[str, Any] = TelemetryRedactor.redact_attributes(attributes or {})
        self.events: List[Dict[str, Any]] = []
        self._prev_span: Optional["Span"] = None
        self._token: Optional[Any] = None

    def set_attribute(self, key: str, value: Any) -> "Span":
        """Adds a redacted attribute to the span."""
        if TelemetryRedactor._is_sensitive_key(key):
            self.attributes[key] = "[REDACTED]"
        else:
            self.attributes[key] = TelemetryRedactor.redact_dict(value)
        return self

    def set_attributes(self, attrs: Dict[str, Any]) -> "Span":
        """Adds multiple redacted attributes to the span."""
        for k, v in attrs.items():
            self.set_attribute(k, v)
        return self

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> "Span":
        """Adds an event to the span with safe attributes."""
        self.events.append({
            "name": name,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "attributes": TelemetryRedactor.redact_attributes(attributes or {}),
        })
        return self

    def set_status(self, status: str, description: Optional[str] = None) -> "Span":
        """Sets the span status ("OK" or "ERROR") with optional description."""
        self.status = "ERROR" if status.upper() == "ERROR" else "OK"
        if description:
            self.status_description = TelemetryRedactor.redact_string(str(description))
        return self

    def record_exception(self, exception: Exception) -> "Span":
        """Records an exception as a span event and sets status to ERROR."""
        self.set_status("ERROR", str(exception))
        self.add_event("exception", {
            "exception.type": type(exception).__name__,
            "exception.message": TelemetryRedactor.redact_string(str(exception)),
        })
        return self

    def end(self) -> None:
        """Finalizes span execution and computes elapsed latency."""
        if self.end_time is None:
            self.end_time = time.perf_counter()
            self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes span data for trace summaries."""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "status_description": self.status_description,
            "attributes": self.attributes,
            "events": self.events,
            "start_time": self.start_timestamp,
        }

    async def __aenter__(self) -> "Span":
        self._prev_span = _current_span.get()
        self._token = _current_span.set(self)
        collector = _active_trace_collector.get()
        if collector:
            collector.add_span(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_val:
            self.record_exception(exc_val)
        self.end()
        if self._token:
            _current_span.reset(self._token)

    def __enter__(self) -> "Span":
        self._prev_span = _current_span.get()
        self._token = _current_span.set(self)
        collector = _active_trace_collector.get()
        if collector:
            collector.add_span(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_val:
            self.record_exception(exc_val)
        self.end()
        if self._token:
            _current_span.reset(self._token)


class TraceCollector:
    """Collects all spans generated for a single logical request."""

    def __init__(
        self,
        trace_id: str,
        company_id: uuid.UUID,
        ai_employee_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        request_type: str = "CHAT",
    ):
        self.trace_id = trace_id
        self.company_id = company_id
        self.ai_employee_id = ai_employee_id
        self.conversation_id = conversation_id
        self.request_type = request_type
        self.spans: List[Span] = []
        self.metadata: Dict[str, Any] = {}
        self.start_time = time.perf_counter()
        self._token: Optional[Any] = None

    def add_span(self, span: Span) -> None:
        self.spans.append(span)

    def set_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = TelemetryRedactor.redact_dict(value)

    def __enter__(self) -> "TraceCollector":
        self._token = _active_trace_collector.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._token:
            _active_trace_collector.reset(self._token)

    async def __aenter__(self) -> "TraceCollector":
        self._token = _active_trace_collector.set(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._token:
            _active_trace_collector.reset(self._token)

    def build_summary(self, error: Optional[str] = None) -> TraceSummary:
        total_latency_ms = round((time.perf_counter() - self.start_time) * 1000, 2)
        has_error = bool(error) or any(s.status == "ERROR" for s in self.spans)
        spans_serialized = [s.to_dict() for s in self.spans]

        return TraceSummary(
            company_id=self.company_id,
            ai_employee_id=self.ai_employee_id,
            conversation_id=self.conversation_id,
            trace_id=self.trace_id,
            request_type=self.request_type,
            status="ERROR" if has_error else "SUCCESS",
            total_latency_ms=total_latency_ms,
            spans_count=len(self.spans),
            spans_data=spans_serialized,
            safe_metadata=TelemetryRedactor.redact_attributes(self.metadata),
            error_message=TelemetryRedactor.redact_string(error) if error else None,
        )


class Tracer:
    """OpenTelemetry-compatible Tracer providing hierarchical span management and W3C context."""

    def __init__(self, service_name: str = "avtaar-ai-employee"):
        self.service_name = service_name

    def get_current_span(self) -> Optional[Span]:
        """Returns the currently active span in the async context."""
        return _current_span.get()

    def get_current_trace_id(self) -> Optional[str]:
        """Returns the active trace_id if one exists."""
        span = self.get_current_span()
        if span:
            return span.trace_id
        collector = _active_trace_collector.get()
        if collector:
            return collector.trace_id
        return None

    def start_span(
        self,
        name: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> Span:
        """Starts a new span without making it the current active span."""
        active = self.get_current_span()
        resolved_trace_id = trace_id or (active.trace_id if active else generate_trace_id())
        resolved_parent_id = parent_span_id or (active.span_id if active else None)

        span = Span(
            name=name,
            trace_id=resolved_trace_id,
            parent_span_id=resolved_parent_id,
            attributes=attributes,
        )
        return span

    def start_as_current_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> Span:
        """Starts a span and returns an async context manager that sets it as active."""
        active = self.get_current_span()
        resolved_trace_id = trace_id or (active.trace_id if active else None)
        if not resolved_trace_id:
            collector = _active_trace_collector.get()
            resolved_trace_id = collector.trace_id if collector else generate_trace_id()

        resolved_parent_id = active.span_id if active else None
        span = Span(
            name=name,
            trace_id=resolved_trace_id,
            parent_span_id=resolved_parent_id,
            attributes=attributes,
        )
        return span

    @classmethod
    def format_traceparent(cls, trace_id: str, span_id: str, sampled: bool = True) -> str:
        """Formats W3C traceparent header: version-trace_id-parent_id-trace_flags."""
        flags = "01" if sampled else "00"
        return f"00-{trace_id}-{span_id}-{flags}"

    @classmethod
    def parse_traceparent(cls, header: str) -> Optional[Dict[str, str]]:
        """Parses W3C traceparent header string."""
        if not header:
            return None
        parts = header.strip().split("-")
        if len(parts) == 4 and parts[0] == "00" and len(parts[1]) == 32 and len(parts[2]) == 16:
            return {
                "version": parts[0],
                "trace_id": parts[1],
                "span_id": parts[2],
                "sampled": parts[3] == "01",
            }
        return None


# Global tracer instance
tracer = Tracer()
