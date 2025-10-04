from abc import ABC, abstractmethod
from typing import Optional


class RateLimiterBackend(ABC):
    """Abstract base class for rate limiter backends"""

    @abstractmethod
    async def is_allowed(
        self, key: str, limit: int, window: int
    ) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed under rate limit

        Args:
            key: Unique identifier for the rate limit (e.g., IP address, user ID)
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        pass

    @abstractmethod
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key"""
        pass

    @abstractmethod
    async def get_remaining(self, key: str, limit: int) -> int:
        """Get remaining requests for a key"""
        pass
