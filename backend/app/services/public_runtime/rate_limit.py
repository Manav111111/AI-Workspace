from collections import defaultdict
import logging
import time
from typing import Dict, List
from fastapi import HTTPException, Request, status

logger = logging.getLogger("app.services.public_runtime.rate_limit")


class SlidingWindowRateLimiter:
    """Sliding-window in-memory rate limiter with clean fail-open fallback if Redis is unavailable.
    Protects public endpoints against session spam and rapid message flooding.
    """

    def __init__(self):
        # Maps key -> list of float timestamps
        self._windows: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int = 60) -> bool:
        now = time.time()
        window_start = now - window_seconds

        # Prune older requests
        reqs = self._windows[key]
        self._windows[key] = [t for t in reqs if t > window_start]

        if len(self._windows[key]) >= max_requests:
            return False

        self._windows[key].append(now)
        return True

    def check_limit(self, key: str, max_requests: int, window_seconds: int, action_name: str) -> None:
        if not self.is_allowed(key, max_requests, window_seconds):
            logger.warning(f"Rate limit exceeded for {action_name} by key '{key}' ({max_requests}/{window_seconds}s)")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {action_name}. Please wait a moment before trying again.",
            )


rate_limiter = SlidingWindowRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract real client IP considering forwarded proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"
