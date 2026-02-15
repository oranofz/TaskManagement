"""Redis client for caching."""
import json
from typing import Any, Optional
from redis.asyncio import Redis
from app.config import settings
from loguru import logger


class RedisClient:
    """Redis client wrapper for caching operations."""

    def __init__(self) -> None:
        """Initialize Redis client."""
        self.redis: Optional[Redis] = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self.redis = Redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        await self.redis.ping()
        logger.info("Redis connected successfully")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis disconnected")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        if not self.redis:
            return False

        try:
            serialized = json.dumps(value)
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.redis:
            return False

        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self.redis:
            return 0

        try:
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis DELETE PATTERN error for pattern {pattern}: {e}")
            return 0


redis_client = RedisClient()

