from typing import Callable, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.rate_limiter.base import RateLimiterBackend


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""

    def __init__(
        self,
        app,
        backend: RateLimiterBackend,
        limit: int = 100,
        window: int = 60,
        key_func: Optional[Callable[[Request], str]] = None,
        exclude_paths: Optional[list[str]] = None,
    ):
        """
        Initialize rate limit middleware

        Args:
            app: FastAPI application
            backend: Rate limiter backend (memory or Redis)
            limit: Maximum requests per window
            window: Time window in seconds
            key_func: Function to extract rate limit key from request
            exclude_paths: List of paths to exclude from rate limiting
        """
        super().__init__(app)
        self.backend = backend
        self.limit = limit
        self.window = window
        self.key_func = key_func or self._default_key_func
        self.exclude_paths = exclude_paths or []

    def _default_key_func(self, request: Request) -> str:
        """Default key function using client IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from rate limiting"""
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""

        # Skip rate limiting for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)

        # Get rate limit key
        key = self.key_func(request)

        # Check rate limit
        is_allowed, retry_after = await self.backend.is_allowed(
            key, self.limit, self.window
        )

        # Get remaining requests
        remaining = await self.backend.get_remaining(key, self.limit)

        if not is_allowed:
            # Rate limit exceeded
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": retry_after,
                },
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                    "Retry-After": str(retry_after),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining - 1)
        response.headers["X-RateLimit-Window"] = str(self.window)

        return response
