"""Rate limiting middleware."""
import time
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from app.shared.cache.redis_client import redis_client
from app.shared.context import get_tenant_id, get_correlation_id
from app.config import settings
from loguru import logger


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """
    Rate limiting middleware using Redis sliding window.

    Args:
        request: FastAPI request
        call_next: Next middleware/handler

    Returns:
        Response
    """
    # Skip rate limiting for health check
    if request.url.path == "/health":
        return await call_next(request)

    tenant_id = get_tenant_id()
    if not tenant_id:
        return await call_next(request)

    # Create rate limit key
    current_minute = int(time.time() / 60)
    rate_limit_key = f"rate_limit:tenant:{tenant_id}:minute:{current_minute}"

    try:
        # Increment counter
        if redis_client.redis:
            count = await redis_client.redis.incr(rate_limit_key)

            # Set expiry on first request in this minute
            if count == 1:
                await redis_client.redis.expire(rate_limit_key, 60)

            # Check limit
            if count > settings.rate_limit_per_minute:
                logger.warning(
                    "Rate limit exceeded",
                    tenant_id=str(tenant_id),
                    count=count,
                    limit=settings.rate_limit_per_minute,
                    correlation_id=get_correlation_id()
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.critical(
            "Rate limit check failed - Redis unavailable",
            error=str(e),
            tenant_id=str(tenant_id),
            correlation_id=get_correlation_id()
        )

    response = await call_next(request)
    return response

