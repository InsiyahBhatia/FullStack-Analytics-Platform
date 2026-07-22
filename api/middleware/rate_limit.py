"""
Sliding-window rate limiter using Redis sorted sets.

Applied as a FastAPI middleware — all requests are rate-limited by client IP.
Default: 100 requests per 60-second window.
"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
    _redis = aioredis.from_url(
        "redis://redis:6379/0",
        decode_responses=True,
        socket_connect_timeout=2,
    )
except Exception:
    _redis = None
    logger.warning("Redis unavailable — rate limiting disabled")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if _redis is None:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"
        now = time.time()
        window_start = now - self.window_seconds

        try:
            async with _redis.pipeline(transaction=True) as pipe:
                await pipe.zremrangebyscore(key, 0, window_start)
                await pipe.zcard(key)
                await pipe.zadd(key, {f"{now}": now})
                await pipe.expire(key, self.window_seconds)
                results = await pipe.execute()

            count = results[1]
            if count >= self.max_requests:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"Rate limit exceeded. Max {self.max_requests} per {self.window_seconds}s",
                        "retry_after": self.window_seconds,
                    },
                )
        except Exception:
            logger.warning("Rate limit check failed — allowing request")

        response = await call_next(request)
        remaining = max(0, self.max_requests - count - 1) if _redis else self.max_requests
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
