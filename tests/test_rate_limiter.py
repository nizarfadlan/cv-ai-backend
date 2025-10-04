import pytest
import asyncio
from app.core.rate_limiter import InMemoryRateLimiter


@pytest.mark.asyncio
class TestInMemoryRateLimiter:
    async def test_allows_requests_under_limit(self):
        limiter = InMemoryRateLimiter()
        key = "test_key"
        limit = 5
        window = 60

        # Should allow all 5 requests
        for _ in range(limit):
            is_allowed, retry_after = await limiter.is_allowed(key, limit, window)
            assert is_allowed is True
            assert retry_after is None

    async def test_blocks_requests_over_limit(self):
        limiter = InMemoryRateLimiter()
        key = "test_key"
        limit = 3
        window = 60

        # Make 3 allowed requests
        for _ in range(limit):
            is_allowed, _ = await limiter.is_allowed(key, limit, window)
            assert is_allowed is True

        # 4th request should be blocked
        is_allowed, retry_after = await limiter.is_allowed(key, limit, window)
        assert is_allowed is False
        assert retry_after is not None
        assert retry_after > 0

    async def test_sliding_window(self):
        limiter = InMemoryRateLimiter()
        key = "test_key"
        limit = 2
        window = 2  # 2 second window

        # Make 2 requests
        await limiter.is_allowed(key, limit, window)
        await limiter.is_allowed(key, limit, window)

        # 3rd request should be blocked
        is_allowed, retry_after = await limiter.is_allowed(key, limit, window)
        assert is_allowed is False

        # Wait for window to expire
        await asyncio.sleep(2.1)

        # Should be allowed again
        is_allowed, _ = await limiter.is_allowed(key, limit, window)
        assert is_allowed is True

    async def test_different_keys_independent(self):
        limiter = InMemoryRateLimiter()
        limit = 2
        window = 60

        # Exhaust limit for key1
        await limiter.is_allowed("key1", limit, window)
        await limiter.is_allowed("key1", limit, window)
        is_allowed, _ = await limiter.is_allowed("key1", limit, window)
        assert is_allowed is False

        # key2 should still be allowed
        is_allowed, _ = await limiter.is_allowed("key2", limit, window)
        assert is_allowed is True

    async def test_reset(self):
        limiter = InMemoryRateLimiter()
        key = "test_key"
        limit = 2
        window = 60

        # Exhaust limit
        await limiter.is_allowed(key, limit, window)
        await limiter.is_allowed(key, limit, window)
        is_allowed, _ = await limiter.is_allowed(key, limit, window)
        assert is_allowed is False

        # Reset
        await limiter.reset(key)

        # Should be allowed again
        is_allowed, _ = await limiter.is_allowed(key, limit, window)
        assert is_allowed is True

    async def test_get_remaining(self):
        limiter = InMemoryRateLimiter()
        key = "test_key"
        limit = 5
        window = 60

        # Initially should have full limit
        remaining = await limiter.get_remaining(key, limit)
        assert remaining == limit

        # After one request
        await limiter.is_allowed(key, limit, window)
        remaining = await limiter.get_remaining(key, limit)
        assert remaining == limit - 1

        # After multiple requests
        await limiter.is_allowed(key, limit, window)
        await limiter.is_allowed(key, limit, window)
        remaining = await limiter.get_remaining(key, limit)
        assert remaining == limit - 3

    def test_cleanup_expired(self):
        limiter = InMemoryRateLimiter()

        # Add some entries
        limiter._requests["key1"].append(1000.0)  # Old timestamp
        limiter._requests["key2"].append(9999999999.0)  # Future timestamp
        limiter._requests["key3"].append(1000.0)  # Old timestamp

        # Cleanup with window of 60 seconds
        limiter.cleanup_expired(window=60)

        # Old entries should be removed
        assert "key1" not in limiter._requests
        assert "key3" not in limiter._requests
        # Recent entry should remain
        assert "key2" in limiter._requests

    async def test_concurrent_requests(self):
        limiter = InMemoryRateLimiter()
        key = "test_key"
        limit = 10
        window = 60

        # Make concurrent requests
        tasks = [limiter.is_allowed(key, limit, window) for _ in range(15)]
        results = await asyncio.gather(*tasks)

        # Count allowed requests
        allowed_count = sum(1 for is_allowed, _ in results if is_allowed)

        # Should allow exactly 'limit' requests
        assert allowed_count == limit

    async def test_retry_after_accuracy(self):
        limiter = InMemoryRateLimiter()
        key = "test_key"
        limit = 1
        window = 5

        # First request allowed
        await limiter.is_allowed(key, limit, window)

        # Second request should be blocked with retry_after
        is_allowed, retry_after = await limiter.is_allowed(key, limit, window)
        assert is_allowed is False
        assert retry_after is not None
        assert 0 < retry_after <= window + 1
