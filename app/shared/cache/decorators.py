"""Cache decorator for query handlers."""
import functools
from typing import Any, Callable, Optional
from app.shared.cache.redis_client import redis_client
from app.shared.context import get_tenant_id
from loguru import logger


def cached(ttl: int = 300, key_prefix: str = "") -> Callable:
    """
    Cache decorator for query handlers.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tenant_id = get_tenant_id()
            if not tenant_id:
                return await func(*args, **kwargs)

            # Generate cache key from function name and arguments
            cache_key = f"tenant:{tenant_id}:{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            cached_value = await redis_client.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            await redis_client.set(cache_key, result, ttl)
            logger.debug(f"Cache miss for key: {cache_key}")

            return result

        return wrapper
    return decorator

