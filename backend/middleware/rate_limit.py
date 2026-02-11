"""In-memory rate limiter middleware."""

import time
from collections import defaultdict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limits audit creation to prevent abuse."""

    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._settings = get_settings()

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, client_ip: str) -> bool:
        now = time.time()
        window = 3600  # 1 hour
        limit = self._settings.rate_limit_per_hour

        # Clean old entries
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < window
        ]

        if len(self._requests[client_ip]) >= limit:
            return True

        self._requests[client_ip].append(now)
        return False

    async def dispatch(self, request: Request, call_next):
        # Only rate limit audit creation
        if request.url.path == "/api/audits/create" and request.method == "POST":
            client_ip = self._get_client_ip(request)
            if self._is_rate_limited(client_ip):
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Maximum {self._settings.rate_limit_per_hour} audits per hour.",
                )

        return await call_next(request)
