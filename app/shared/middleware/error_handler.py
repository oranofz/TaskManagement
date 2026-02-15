"""Error handling middleware."""
import traceback
from typing import Callable
from fastapi import Request, Response, status, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger
from app.shared.context import get_correlation_id


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

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred",
                    "details": {}
                },
                "metadata": {
                    "timestamp": None,
                    "correlation_id": correlation_id
                }
            }
        )

