from typing import Optional
from app.core.rate_limiter.base import RateLimiterBackend

rate_limiter: Optional[RateLimiterBackend] = None


def get_rate_limiter() -> Optional[RateLimiterBackend]:
    return rate_limiter


def set_rate_limiter(limiter: RateLimiterBackend) -> None:
    global rate_limiter
    rate_limiter = limiter
