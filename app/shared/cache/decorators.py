"""Cache decorator for query handlers."""
import functools
import hashlib
from typing import Any, Callable
from app.shared.cache.redis_client import redis_client
from app.shared.context import get_tenant_id
from loguru import logger
from pydantic import BaseModel


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

            # Build a stable key: skip bound `self` if present, then hash args/kwargs
            effective_args = args
            if args:
                try:
                    cls_name = func.__qualname__.split('.')[0]
                    if hasattr(args[0], '__class__') and args[0].__class__.__name__ == cls_name:
                        effective_args = args[1:]
                except Exception:
                    effective_args = args

            try:
                args_repr = [repr(a) for a in effective_args]
                kwargs_repr = {k: repr(v) for k, v in sorted(kwargs.items())}
                key_material = repr((args_repr, kwargs_repr))
                key_hash = hashlib.sha256(key_material.encode('utf-8')).hexdigest()[:16]
            except Exception:
                key_hash = hashlib.sha256(repr((str(effective_args), str(kwargs))).encode('utf-8')).hexdigest()[:16]

            cache_key = f"tenant:{tenant_id}:{key_prefix}:{func.__name__}:{key_hash}"

            # Try to get from cache
            cached_value = await redis_client.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Convert Pydantic models to dict for JSON serialization
            if isinstance(result, BaseModel):
                cache_data = result.model_dump()
            else:
                cache_data = result

            # Store in cache
            await redis_client.set(cache_key, cache_data, ttl)
            logger.debug(f"Cache miss for key: {cache_key}")

            return result

        return wrapper
    return decorator

