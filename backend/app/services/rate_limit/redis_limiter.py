from collections import defaultdict
from dataclasses import dataclass
import logging
import math
import threading
import time
from typing import Dict, List, Optional
from fastapi import HTTPException, Request, status
import redis

from app.core.config import settings

logger = logging.getLogger("app.services.rate_limit")


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int


class RateLimitException(HTTPException):
    def __init__(self, message: str, retry_after: int, limit: int, action_name: str):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "RATE_LIMITED",
                "message": message,
                "retry_after_seconds": retry_after,
                "action": action_name,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )


class DistributedRateLimiter:
    """Production Redis-backed atomic sliding-window rate limiter with transparent
    fail-safe fallback to thread-safe local memory when Redis is offline or degraded.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        timeout_seconds: float = 0.5,
    ):
        self.redis_url = redis_url or settings.REDIS_URL
        self.timeout = timeout_seconds
        self._redis_client: Optional[redis.Redis] = None
        self._redis_available: Optional[bool] = None
        self._last_redis_check: float = 0.0

        # Local fallback state
        self._local_windows: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def _get_redis(self) -> Optional[redis.Redis]:
        """Lazy-initializes Redis client with short connection timeout."""
        now = time.time()
        # If marked unavailable, retry probing every 30 seconds
        if self._redis_available is False and (now - self._last_redis_check) < 30.0:
            return None

        if self._redis_client is None:
            try:
                self._redis_client = redis.Redis.from_url(
                    self.redis_url,
                    socket_timeout=self.timeout,
                    socket_connect_timeout=self.timeout,
                    decode_responses=True,
                )
            except Exception as e:
                logger.warning(f"Could not initialize Redis client: {e}")
                self._redis_available = False
                self._last_redis_check = now
                return None

        return self._redis_client

    def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60,
        fail_mode: str = "fail_open_with_local",
    ) -> RateLimitResult:
        """Evaluates whether the request is within rate limits atomically."""
        r = self._get_redis()
        now = time.time()
        window_start = now - window_seconds

        if r is not None:
            try:
                # Atomic Redis sorted set sliding window
                pipe = r.pipeline()
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zcard(key)
                pipe.zrange(key, 0, 0, withscores=True)
                pipe.expire(key, window_seconds + 10)
                _, current_count, oldest_items, _ = pipe.execute()

                self._redis_available = True

                if current_count >= max_requests:
                    oldest_ts = oldest_items[0][1] if oldest_items else window_start
                    retry_after = max(1, math.ceil(oldest_ts + window_seconds - now))
                    return RateLimitResult(
                        allowed=False,
                        limit=max_requests,
                        remaining=0,
                        retry_after=retry_after,
                    )

                # Record current request
                r.zadd(key, {f"{now}:{time.perf_counter()}": now})
                remaining = max(0, max_requests - current_count - 1)
                return RateLimitResult(
                    allowed=True,
                    limit=max_requests,
                    remaining=remaining,
                    retry_after=0,
                )

            except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as err:
                self._redis_available = False
                self._last_redis_check = now
                logger.warning(
                    f"Redis unavailable for rate-limiting key '{key}': {err}. "
                    f"Applying failure mode: {fail_mode}"
                )

        # Fallback handling
        if fail_mode == "fail_closed":
            return RateLimitResult(
                allowed=False,
                limit=max_requests,
                remaining=0,
                retry_after=15,
            )

        # Fail-open with thread-safe local in-memory sliding window
        with self._lock:
            timestamps = self._local_windows[key]
            valid_timestamps = [t for t in timestamps if t > window_start]

            if len(valid_timestamps) >= max_requests:
                oldest_ts = valid_timestamps[0]
                retry_after = max(1, math.ceil(oldest_ts + window_seconds - now))
                self._local_windows[key] = valid_timestamps
                return RateLimitResult(
                    allowed=False,
                    limit=max_requests,
                    remaining=0,
                    retry_after=retry_after,
                )

            valid_timestamps.append(now)
            self._local_windows[key] = valid_timestamps
            remaining = max(0, max_requests - len(valid_timestamps))
            return RateLimitResult(
                allowed=True,
                limit=max_requests,
                remaining=remaining,
                retry_after=0,
            )

    def check_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        action_name: str,
        fail_mode: str = "fail_open_with_local",
    ) -> None:
        """Enforces rate limit, raising RateLimitException (HTTP 429) if exceeded."""
        res = self.is_allowed(key, max_requests, window_seconds, fail_mode=fail_mode)
        if not res.allowed:
            logger.warning(
                f"Rate limit exceeded for '{action_name}' by key '{key}' "
                f"({res.limit}/{window_seconds}s). Retry-After: {res.retry_after}s"
            )
            raise RateLimitException(
                message=f"Rate limit exceeded for {action_name}. Please retry in {res.retry_after} seconds.",
                retry_after=res.retry_after,
                limit=res.limit,
                action_name=action_name,
            )


# Singleton production rate limiter instance
distributed_rate_limiter = DistributedRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract real client IP considering forwarded proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"
