"""Standard API response wrapper."""
from typing import Any, Optional, Dict, Generic, TypeVar, List
from datetime import datetime, UTC
from pydantic import BaseModel, Field
from app.shared.context import get_correlation_id

T = TypeVar('T')


class ErrorDetail(BaseModel):
    """Error detail structure."""
    code: Optional[str] = None
    message: str


class PaginationMetadata(BaseModel):
    """Pagination metadata."""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class StandardResponse(BaseModel, Generic[T]):
    """
    Standard API response format as per assignment requirements:
    { success: boolean, data: object|array, error: { code: string, message: string }, metadata: { pagination, etc. } }
    """
    success: bool
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


def create_success_response(
    data: Any,
    pagination: Optional[PaginationMetadata] = None
) -> StandardResponse:
    """
    Create a standardized success response.

    Args:
        data: Response payload
        pagination: Optional pagination metadata

    Returns:
        StandardResponse with success=True
    """
    metadata: Dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "correlation_id": get_correlation_id()
    }

    if pagination:
        metadata["pagination"] = pagination.model_dump()

    return StandardResponse(
        success=True,
        data=data,
        error=None,
        metadata=metadata
    )


def create_error_response(
    error_message: str,
    error_code: Optional[str] = None
) -> StandardResponse:
    """
    Create a standardized error response.

    Args:
        error_message: Error message
        error_code: Optional error code

    Returns:
        StandardResponse with success=False
    """
    return StandardResponse(
        success=False,
        data=None,
        error=ErrorDetail(
            code=error_code,
            message=error_message
        ),
        metadata={
            "timestamp": datetime.now(UTC).isoformat(),
            "correlation_id": get_correlation_id()
        }
    )


def create_paginated_response(
    items: List[Any],
    page: int,
    page_size: int,
    total_items: int
) -> StandardResponse:
    """
    Create a standardized paginated response.

    Args:
        items: List of items for current page
        page: Current page number (1-based)
        page_size: Number of items per page
        total_items: Total number of items across all pages

    Returns:
        StandardResponse with pagination metadata
    """
    total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0

    pagination = PaginationMetadata(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )

    return create_success_response(data=items, pagination=pagination)


