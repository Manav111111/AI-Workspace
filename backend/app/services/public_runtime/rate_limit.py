import logging
from typing import Optional
from fastapi import Request
from app.services.rate_limit import (
    DistributedRateLimiter,
    RateLimitException,
    RateLimitResult,
    distributed_rate_limiter,
    get_client_ip as base_get_client_ip,
)

logger = logging.getLogger("app.services.public_runtime.rate_limit")


class SlidingWindowRateLimiter:
    """Distributed Redis-backed sliding-window rate limiter with local fallback.
    Preserves backward-compatible interface for public runtime endpoints.
    """

    def __init__(self, limiter: Optional[DistributedRateLimiter] = None):
        self._limiter = limiter or distributed_rate_limiter

    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60,
        fail_mode: str = "fail_open_with_local",
    ) -> bool:
        res = self._limiter.is_allowed(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
            fail_mode=fail_mode,
        )
        return res.allowed

    def check_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        action_name: str,
        fail_mode: str = "fail_open_with_local",
    ) -> None:
        self._limiter.check_limit(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
            action_name=action_name,
            fail_mode=fail_mode,
        )


rate_limiter = SlidingWindowRateLimiter()


def get_client_ip(request: Request) -> str:
    return base_get_client_ip(request)
