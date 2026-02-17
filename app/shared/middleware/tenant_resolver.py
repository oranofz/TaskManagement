"""Tenant resolution middleware."""
from typing import Callable, Optional
from uuid import UUID
from fastapi import Request, Response, HTTPException, status
from loguru import logger
from app.shared.context import set_tenant_id, get_correlation_id
from app.shared.cache.redis_client import redis_client


def extract_subdomain(host: str) -> Optional[str]:
    """
    Extract subdomain from host header.

    Supports patterns like:
    - tenant1.example.com -> tenant1
    - tenant1.api.example.com -> tenant1
    - localhost:8000 -> None (no subdomain for localhost)
    - api.example.com -> None (api is a reserved subdomain)

    Args:
        host: Host header value

    Returns:
        Subdomain string or None if not found/applicable
    """
    # Remove port if present
    host = host.split(":")[0]

    # Skip localhost - no subdomain resolution
    if host == "localhost" or host == "127.0.0.1":
        return None

    parts = host.split(".")

    # Need at least 3 parts for subdomain (e.g., tenant.example.com)
    if len(parts) < 3:
        return None

    # Reserved subdomains that shouldn't be treated as tenant identifiers
    reserved_subdomains = {"www", "api", "app", "admin", "mail", "smtp", "ftp"}

    subdomain = parts[0].lower()

    if subdomain in reserved_subdomains:
        return None

    return subdomain


async def resolve_tenant_from_subdomain(subdomain: str) -> Optional[UUID]:
    """
    Resolve tenant ID from subdomain using cache or database lookup.

    Args:
        subdomain: Subdomain to look up

    Returns:
        Tenant UUID or None if not found
    """
    # Try cache first
    cache_key = f"tenant:subdomain:{subdomain}"

    try:
        if redis_client.redis:
            cached_tenant_id = await redis_client.redis.get(cache_key)
            if cached_tenant_id:
                logger.debug(
                    "Tenant resolved from cache",
                    subdomain=subdomain,
                    tenant_id=cached_tenant_id.decode() if isinstance(cached_tenant_id, bytes) else cached_tenant_id,
                    correlation_id=get_correlation_id()
                )
                return UUID(cached_tenant_id.decode() if isinstance(cached_tenant_id, bytes) else cached_tenant_id)
    except Exception as e:
        logger.warning(
            "Failed to fetch tenant from cache",
            subdomain=subdomain,
            error=str(e),
            correlation_id=get_correlation_id()
        )

    # Fall back to database lookup
    try:
        from app.tenant.repository import TenantRepository
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.shared.database import engine

        async with AsyncSession(engine) as session:
            repository = TenantRepository(session)
            tenant = await repository.get_tenant_by_subdomain(subdomain)

            if tenant and tenant.is_active:
                tenant_id = tenant.id

                # Cache for 5 minutes
                try:
                    if redis_client.redis:
                        await redis_client.redis.setex(
                            cache_key,
                            300,  # 5 minutes TTL
                            str(tenant_id)
                        )
                except Exception as cache_error:
                    logger.warning(
                        "Failed to cache tenant subdomain mapping",
                        subdomain=subdomain,
                        error=str(cache_error),
                        correlation_id=get_correlation_id()
                    )

                logger.debug(
                    "Tenant resolved from database",
                    subdomain=subdomain,
                    tenant_id=str(tenant_id),
                    correlation_id=get_correlation_id()
                )
                return tenant_id
    except Exception as e:
        logger.error(
            "Failed to resolve tenant from database",
            subdomain=subdomain,
            error=str(e),
            correlation_id=get_correlation_id()
        )

    return None


async def tenant_resolver_middleware(request: Request, call_next: Callable) -> Response:
    """
    Tenant resolution middleware.

    Extracts tenant_id using the following resolution strategies (in order of precedence):
    1. Subdomain (e.g., tenant1.example.com)
    2. X-Tenant-ID header
    3. JWT token claim (handled by auth middleware)

    Args:
        request: FastAPI request
        call_next: Next middleware/handler

    Returns:
        Response
    """
    # Skip tenant resolution for public endpoints
    public_paths = ["/", "/health", "/ready", "/live", "/docs", "/openapi.json", "/redoc"]
    if request.url.path in public_paths:
        return await call_next(request)

    tenant_id: Optional[UUID] = None
    resolution_method: Optional[str] = None

    # Strategy 1: Try to get tenant_id from subdomain
    host = request.headers.get("host", "")
    subdomain = extract_subdomain(host)

    if subdomain:
        tenant_id = await resolve_tenant_from_subdomain(subdomain)
        if tenant_id:
            resolution_method = "subdomain"
            logger.debug(
                "Tenant resolved from subdomain",
                subdomain=subdomain,
                tenant_id=str(tenant_id),
                correlation_id=get_correlation_id()
            )

    # Strategy 2: Try to get tenant_id from header
    if not tenant_id:
        tenant_id_str = request.headers.get("X-Tenant-ID")

        if tenant_id_str:
            try:
                tenant_id = UUID(tenant_id_str)
                resolution_method = "header"
                logger.debug(
                    "Tenant resolved from header",
                    tenant_id=str(tenant_id),
                    correlation_id=get_correlation_id()
                )
            except ValueError:
                logger.warning(
                    "Invalid tenant ID in header",
                    tenant_id=tenant_id_str,
                    correlation_id=get_correlation_id()
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid tenant ID format"
                )

    # Set tenant context if resolved
    if tenant_id:
        set_tenant_id(tenant_id)

        # Store resolution method in request state for debugging/metrics
        request.state.tenant_resolution_method = resolution_method

        logger.info(
            "Tenant context set",
            tenant_id=str(tenant_id),
            resolution_method=resolution_method,
            correlation_id=get_correlation_id()
        )

    response = await call_next(request)
    return response

