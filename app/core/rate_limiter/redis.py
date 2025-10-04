import time
from typing import Optional
from redis.asyncio import Redis
from app.core.rate_limiter.base import RateLimiterBackend


class RedisRateLimiter(RateLimiterBackend):
    """Redis-based rate limiter using sliding window with sorted sets"""

    def __init__(self, redis_client: Redis):
        """
        Initialize Redis rate limiter

        Args:
            redis_client: Async Redis client instance
        """
        self.redis = redis_client

    def _get_key(self, key: str) -> str:
        """Generate Redis key with prefix"""
        return f"rate_limit:{key}"

    async def is_allowed(
        self, key: str, limit: int, window: int
    ) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed using Redis sorted set

        Args:
            key: Unique identifier for the rate limit
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        redis_key = self._get_key(key)
        current_time = time.time()
        cutoff_time = current_time - window

        # Use pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove expired entries
        pipe.zremrangebyscore(redis_key, 0, cutoff_time)

        # Count current requests
        pipe.zcard(redis_key)

        # Execute pipeline
        _, current_count = await pipe.execute()

        # Check if limit exceeded
        if current_count >= limit:
            # Get oldest request timestamp
            oldest = await self.redis.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                oldest_timestamp = oldest[0][1]
                retry_after = int(oldest_timestamp + window - current_time) + 1
                return False, retry_after
            return False, window

        # Add current request
        await self.redis.zadd(redis_key, {str(current_time): current_time})

        # Set expiration on key
        await self.redis.expire(redis_key, window)

        return True, None

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key"""
        redis_key = self._get_key(key)
        await self.redis.delete(redis_key)

    async def get_remaining(self, key: str, limit: int) -> int:
        """Get remaining requests for a key"""
        redis_key = self._get_key(key)
        current_count = await self.redis.zcard(redis_key)
        return max(0, limit - current_count)
