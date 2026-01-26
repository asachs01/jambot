"""Tests for rate limiting functionality."""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.rate_limiter import RateLimiter


@pytest.fixture
async def fake_redis():
    """Create a fake Redis client for testing."""
    import fakeredis
    redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    yield redis
    await redis.aclose()


@pytest.fixture
async def rate_limiter(fake_redis):
    """Create a rate limiter with fake Redis backend."""
    limiter = RateLimiter(
        redis_url="redis://localhost:6379/0",
        max_requests=3,
        window_seconds=600
    )
    # Replace real Redis with fake
    limiter.redis = fake_redis
    limiter._connection_failed = False
    return limiter


@pytest.mark.asyncio
async def test_rate_limit_basic_allow(rate_limiter):
    """Test basic rate limiting - first 3 requests allowed."""
    identifier = "user:123:chord"

    # First 3 requests should be allowed
    for i in range(3):
        allowed, remaining = await rate_limiter.check_rate_limit(identifier)
        assert allowed is True
        assert remaining == 2 - i  # 2, 1, 0


@pytest.mark.asyncio
async def test_rate_limit_fourth_blocked(rate_limiter):
    """Test that 4th request is blocked."""
    identifier = "user:456:chord"

    # First 3 requests allowed
    for _ in range(3):
        allowed, _ = await rate_limiter.check_rate_limit(identifier)
        assert allowed is True

    # 4th request should be blocked
    allowed, remaining = await rate_limiter.check_rate_limit(identifier)
    assert allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_rate_limit_isolation(rate_limiter):
    """Test that different users have isolated rate limits."""
    user1 = "user:111:chord"
    user2 = "user:222:chord"

    # User 1 uses all 3 requests
    for _ in range(3):
        allowed, _ = await rate_limiter.check_rate_limit(user1)
        assert allowed is True

    # User 1's 4th request blocked
    allowed, _ = await rate_limiter.check_rate_limit(user1)
    assert allowed is False

    # User 2 still has requests available
    allowed, remaining = await rate_limiter.check_rate_limit(user2)
    assert allowed is True
    assert remaining == 2


@pytest.mark.asyncio
async def test_rate_limit_window_expiration(rate_limiter):
    """Test that rate limit resets after window expiration."""
    identifier = "user:789:chord"

    # Use all 3 requests
    for _ in range(3):
        await rate_limiter.check_rate_limit(identifier)

    # 4th blocked
    allowed, _ = await rate_limiter.check_rate_limit(identifier)
    assert allowed is False

    # Manually expire the key
    await rate_limiter.redis.delete(f"rate_limit:{identifier}")

    # Should work again after reset
    allowed, remaining = await rate_limiter.check_rate_limit(identifier)
    assert allowed is True
    assert remaining == 2


@pytest.mark.asyncio
async def test_rate_limit_ttl(rate_limiter):
    """Test TTL retrieval."""
    identifier = "user:999:chord"

    # Make first request
    await rate_limiter.check_rate_limit(identifier)

    # Check TTL is set
    ttl = await rate_limiter.get_ttl(identifier)
    assert ttl > 0
    assert ttl <= 600  # Should be <= window_seconds


@pytest.mark.asyncio
async def test_rate_limit_reset(rate_limiter):
    """Test admin reset functionality."""
    identifier = "user:555:chord"

    # Use all requests
    for _ in range(3):
        await rate_limiter.check_rate_limit(identifier)

    # Verify blocked
    allowed, _ = await rate_limiter.check_rate_limit(identifier)
    assert allowed is False

    # Reset limit
    await rate_limiter.reset_limit(identifier)

    # Should work again
    allowed, remaining = await rate_limiter.check_rate_limit(identifier)
    assert allowed is True
    assert remaining == 2


@pytest.mark.asyncio
async def test_rate_limit_redis_failure_graceful_degradation():
    """Test graceful degradation when Redis is unavailable."""
    limiter = RateLimiter(
        redis_url="redis://localhost:6379/0",
        max_requests=3,
        window_seconds=600
    )
    limiter.redis = None
    limiter._connection_failed = True

    # Should allow all requests when Redis unavailable
    for _ in range(10):
        allowed, remaining = await limiter.check_rate_limit("user:123:chord")
        assert allowed is True
        assert remaining == -1  # Indicates degraded mode


@pytest.mark.asyncio
async def test_rate_limit_connection():
    """Test Redis connection establishment."""
    # This test requires a mock since we don't want real Redis
    limiter = RateLimiter(redis_url="redis://localhost:6379/0")

    with patch('redis.asyncio.from_url') as mock_from_url:
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()
        mock_from_url.return_value = mock_redis

        result = await limiter.connect()

        assert result is True
        assert limiter._connection_failed is False
        mock_from_url.assert_called_once()
        mock_redis.ping.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limit_connection_failure():
    """Test handling of Redis connection failure."""
    limiter = RateLimiter(redis_url="redis://localhost:6379/0")

    with patch('redis.asyncio.from_url') as mock_from_url:
        mock_from_url.side_effect = ConnectionError("Redis unavailable")

        result = await limiter.connect()

        assert result is False
        assert limiter._connection_failed is True
        assert limiter.redis is None


@pytest.mark.asyncio
async def test_rate_limit_close(rate_limiter):
    """Test graceful Redis connection close."""
    await rate_limiter.close()
    # Should not raise exception
    assert True
