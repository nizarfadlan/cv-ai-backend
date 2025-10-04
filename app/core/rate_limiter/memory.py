import time
from collections import defaultdict, deque
from typing import Optional
from app.core.rate_limiter.base import RateLimiterBackend


class InMemoryRateLimiter(RateLimiterBackend):
    """In-memory rate limiter using sliding window algorithm"""

    def __init__(self):
        # Store timestamps of requests for each key
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    async def is_allowed(
        self, key: str, limit: int, window: int
    ) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed using sliding window algorithm

        Args:
            key: Unique identifier for the rate limit
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        current_time = time.time()
        cutoff_time = current_time - window

        # Remove expired timestamps
        while self._requests[key] and self._requests[key][0] < cutoff_time:
            self._requests[key].popleft()

        # Check if limit exceeded
        if len(self._requests[key]) >= limit:
            # Calculate retry_after based on oldest request in window
            oldest_request = self._requests[key][0]
            retry_after = int(oldest_request + window - current_time) + 1
            return False, retry_after

        # Allow request and record timestamp
        self._requests[key].append(current_time)
        return True, None

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key"""
        if key in self._requests:
            del self._requests[key]

    async def get_remaining(self, key: str, limit: int) -> int:
        """Get remaining requests for a key"""
        current_count = len(self._requests.get(key, []))
        return max(0, limit - current_count)

    def cleanup_expired(self, window: int) -> None:
        """
        Cleanup expired entries to prevent memory bloat
        Should be called periodically by a background task
        """
        current_time = time.time()
        cutoff_time = current_time - window

        keys_to_delete = []
        for key, timestamps in self._requests.items():
            # Remove expired timestamps
            while timestamps and timestamps[0] < cutoff_time:
                timestamps.popleft()

            # Mark empty queues for deletion
            if not timestamps:
                keys_to_delete.append(key)

        # Delete empty entries
        for key in keys_to_delete:
            del self._requests[key]
