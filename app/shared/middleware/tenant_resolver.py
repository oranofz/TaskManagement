"""Tenant resolution middleware."""
from typing import Callable
from uuid import UUID
from fastapi import Request, Response, HTTPException, status
from loguru import logger
from app.shared.context import set_tenant_id, get_correlation_id


async def tenant_resolver_middleware(request: Request, call_next: Callable) -> Response:
    """
    Tenant resolution middleware.
    Extracts tenant_id from header or JWT token.

    Args:
        request: FastAPI request
        call_next: Next middleware/handler

    Returns:
        Response
    """
    # Skip tenant resolution for public endpoints
    public_paths = ["/health", "/docs", "/openapi.json", "/redoc"]
    if request.url.path in public_paths:
        return await call_next(request)

    # Try to get tenant_id from header
    tenant_id_str = request.headers.get("X-Tenant-ID")

    if tenant_id_str:
        try:
            tenant_id = UUID(tenant_id_str)
            set_tenant_id(tenant_id)

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

    response = await call_next(request)
    return response

