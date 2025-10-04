from functools import wraps
from typing import Callable, Optional
from fastapi import Request, HTTPException, status
from app.core.rate_limiter.base import RateLimiterBackend


def rate_limit(
    backend: Optional[RateLimiterBackend] = None,
    limit: int = 10,
    window: int = 60,
    key_func: Optional[Callable[[Request], str]] = None,
):
    """
    Decorator for rate limiting individual endpoints

    Args:
        backend: Rate limiter backend
        limit: Maximum requests per window
        window: Time window in seconds
        key_func: Function to extract rate limit key from request

    Example:
        @router.post("/evaluate")
        @rate_limit(backend=rate_limiter, limit=5, window=60)
        async def create_evaluation(request: Request, ...):
            ...
    """

    def _default_key_func(request: Request) -> str:
        """Default key function using client IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    actual_key_func = key_func or _default_key_func

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            if not request:
                raise ValueError("Request object not found in function arguments")

            if (
                not backend
                or not isinstance(backend, RateLimiterBackend)
                or backend is None
            ):
                raise ValueError("RateLimiterBackend instance must be provided")

            # Get rate limit key
            key = actual_key_func(request)

            # Check rate limit
            is_allowed, retry_after = await backend.is_allowed(key, limit, window)

            if not is_allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "Retry-After": str(retry_after),
                    },
                )

            # Get remaining requests
            remaining = await backend.get_remaining(key, limit)

            # Call original function
            response = await func(*args, **kwargs)

            # Add rate limit headers if response supports it
            if hasattr(response, "headers"):
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = str(remaining - 1)
                response.headers["X-RateLimit-Window"] = str(window)

            return response

        return wrapper

    return decorator
