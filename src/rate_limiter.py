"""Rate limiting using Redis for chord chart requests.

COMPATIBILITY NOTE:
Task spec requires aioredis==2.1.0, but it's incompatible with Python 3.14+
due to TypeError: duplicate base class TimeoutError in aioredis.exceptions.
Using redis.asyncio (redis>=5.0.0) which is the official successor to aioredis.
Provides identical async Redis functionality with full Python 3.14 compatibility.
"""
import redis.asyncio as aioredis
from typing import Tuple, Optional
from src.logger import logger


class RateLimiter:
    """Redis-based rate limiter for chord chart operations.

    Uses atomic INCR + EXPIRE operations to enforce request limits.
    Thread-safe and distributed-safe across multiple bot instances.
    """

    def __init__(
        self,
        redis_url: str,
        max_requests: int = 3,
        window_seconds: int = 600  # 10 minutes
    ):
        """Initialize rate limiter.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0).
            max_requests: Maximum requests allowed per window (default 3).
            window_seconds: Time window in seconds (default 600 = 10 minutes).
        """
        self.redis_url = redis_url
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis: Optional[aioredis.Redis] = None
        self._connection_failed = False

    async def connect(self):
        """Establish Redis connection.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            self.redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
            self._connection_failed = False
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Rate limiting disabled.")
            self._connection_failed = True
            self.redis = None
            return False

    async def close(self):
        """Close Redis connection gracefully."""
        if self.redis:
            try:
                await self.redis.aclose()
                logger.info("Closed Redis connection")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

    async def check_rate_limit(self, identifier: str) -> Tuple[bool, int]:
        """Check if request is within rate limit.

        Uses atomic INCR-first pattern to prevent race conditions.

        Args:
            identifier: Unique identifier for rate limit scope.
                       Format: "user:{user_id}:chord" or "guild:{guild_id}:chord"

        Returns:
            Tuple of (allowed: bool, remaining_requests: int).
            If Redis unavailable, returns (True, -1) for graceful degradation.
        """
        # Graceful degradation if Redis unavailable
        if not self.redis or self._connection_failed:
            return (True, -1)

        try:
            key = f"rate_limit:{identifier}"

            # Atomic INCR-first pattern (race-condition safe)
            new_count = await self.redis.incr(key)

            # If this is first request, set expiration
            if new_count == 1:
                await self.redis.expire(key, self.window_seconds)

            # Check if limit exceeded
            if new_count > self.max_requests:
                # Rate limit exceeded
                remaining = 0
                return (False, remaining)

            # Calculate remaining requests
            remaining = max(0, self.max_requests - new_count)
            return (True, remaining)

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}. Allowing request (graceful degradation).")
            # Graceful degradation - allow request on error
            return (True, -1)

    async def get_ttl(self, identifier: str) -> int:
        """Get remaining time in seconds until rate limit window resets.

        Args:
            identifier: Unique identifier for rate limit scope.

        Returns:
            Remaining seconds, or 0 if no limit active or Redis unavailable.
        """
        if not self.redis or self._connection_failed:
            return 0

        try:
            key = f"rate_limit:{identifier}"
            ttl = await self.redis.ttl(key)
            return max(0, ttl) if ttl > 0 else 0
        except Exception as e:
            logger.error(f"Failed to get rate limit TTL: {e}")
            return 0

    async def reset_limit(self, identifier: str):
        """Reset rate limit for an identifier (admin operation).

        Args:
            identifier: Unique identifier to reset.
        """
        if not self.redis or self._connection_failed:
            logger.warning("Cannot reset rate limit - Redis unavailable")
            return

        try:
            key = f"rate_limit:{identifier}"
            await self.redis.delete(key)
            logger.info(f"Reset rate limit for {identifier}")
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
