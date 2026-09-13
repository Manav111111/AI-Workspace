import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.middleware.logging")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        
        # Request ID propagation
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Call next middleware/endpoint
        try:
            response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000
            
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"

            # Structured logging
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} ({process_time:.2f}ms)",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(process_time, 2),
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )
            return response
        except Exception as exc:
            process_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Unhandled error processing {request.method} {request.url.path}: {str(exc)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(process_time, 2),
                },
                exc_info=True,
            )
            raise exc
