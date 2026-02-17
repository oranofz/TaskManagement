"""Error handling middleware."""
from typing import Callable
from fastapi import Request, Response, status, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger
from app.shared.context import get_correlation_id
from app.shared.response import create_error_response


async def error_handler_middleware(request: Request, call_next: Callable) -> Response:
    """
    Global error handler middleware.

    Args:
        request: FastAPI request
        call_next: Next middleware/handler

    Returns:
        Response
    """
    try:
        response = await call_next(request)
        return response
    except HTTPException:
        # Re-raise HTTPException to let FastAPI's exception handler deal with it
        raise
    except Exception as e:
        correlation_id = get_correlation_id()

        logger.error(
            f"Unhandled exception: {str(e)}",
            correlation_id=correlation_id,
            path=request.url.path,
            method=request.method,
            exc_info=True
        )

        error_response = create_error_response(
            error_message="An internal server error occurred",
            error_code="INTERNAL_SERVER_ERROR"
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump()
        )

