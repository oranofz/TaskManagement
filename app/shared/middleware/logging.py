"""Request logging middleware."""
import time
from typing import Callable
from uuid import uuid4
from fastapi import Request, Response
from loguru import logger
from app.shared.context import set_correlation_id


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """
    Request logging middleware.

    Args:
        request: FastAPI request
        call_next: Next middleware/handler

    Returns:
        Response
    """
    # Generate correlation ID
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    set_correlation_id(correlation_id)

    # Log request
    start_time = time.time()
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        correlation_id=correlation_id,
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else None
    )

    # Process request
    response = await call_next(request)

    # Log response
    duration = time.time() - start_time
    logger.info(
        f"Request completed: {request.method} {request.url.path}",
        correlation_id=correlation_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2)
    )

    # Add correlation ID to response headers
    response.headers["X-Correlation-ID"] = correlation_id

    return response

