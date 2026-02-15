"""Standard API response wrapper."""
from typing import Any, Optional, Dict
from datetime import datetime, UTC
from pydantic import BaseModel
from app.shared.context import get_correlation_id


class StandardResponse(BaseModel):
    """Standard API response format."""
    success: bool
    data: Optional[Any] = None
    metadata: Dict[str, Any]

    class Config:
        arbitrary_types_allowed = True


def create_success_response(data: Any) -> StandardResponse:
    """
    Create a standardized success response.

    Args:
        data: Response payload

    Returns:
        StandardResponse with success=True
    """
    return StandardResponse(
        success=True,
        data=data,
        metadata={
            "timestamp": datetime.now(UTC).isoformat(),
            "correlation_id": get_correlation_id()
        }
    )


def create_error_response(error_message: str, error_code: Optional[str] = None) -> StandardResponse:
    """
    Create a standardized error response.

    Args:
        error_message: Error message
        error_code: Optional error code

    Returns:
        StandardResponse with success=False
    """
    error_data = {"message": error_message}
    if error_code:
        error_data["code"] = error_code

    return StandardResponse(
        success=False,
        data=error_data,
        metadata={
            "timestamp": datetime.now(UTC).isoformat(),
            "correlation_id": get_correlation_id()
        }
    )

