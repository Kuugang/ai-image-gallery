"""Standardized API response schemas."""
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    Standardized API response wrapper.
    
    All API endpoints should return data wrapped in this format:
    {
        "data": <actual response data>,
        "message": "Human-readable message"
    }
    
    Example:
    {
        "data": {
            "id": "123",
            "name": "John",
            ...
        },
        "message": "User retrieved successfully"
    }
    """

    data: Optional[T] = None
    message: str = "Success"


class PaginatedResponse(BaseModel, Generic[T]):
    """Response for paginated list endpoints."""

    data: list[T]
    count: int  # Items in current page
    total: int  # Total items available
    page: int  # Current page number
    page_size: int  # Items per page
    message: str = "Items retrieved successfully"
