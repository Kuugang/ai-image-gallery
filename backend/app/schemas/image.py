"""Image schemas for API requests/responses."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ImageUploadResponse(BaseModel):
    """Response after image upload (before AI processing)."""

    id: UUID
    filename: str
    original_path: str
    user_id: UUID
    uploaded_at: datetime
    ai_processing_status: str = Field(default="pending")

    class Config:
        from_attributes = True


class ImageMetadataResponse(BaseModel):
    """Complete image with AI-processed metadata."""

    id: UUID
    filename: str
    original_path: str
    thumbnail_path: Optional[str] = None
    user_id: UUID
    uploaded_at: datetime
    description: Optional[str] = None
    tags: Optional[list[str]] = None  # Tag names from tags table
    colors: Optional[list[str]] = None  # Hex values from colors table
    tag_vec: Optional[list[float]] = None  # 4096-dim vector for semantic search
    color_vec: Optional[list[float]] = None  # 12-dim color histogram vector
    ai_processing_status: str

    class Config:
        from_attributes = True


class PaginatedImagesResponse(BaseModel):
    """Paginated list of images with standardized response format."""

    data: list[ImageMetadataResponse]
    count: int  # Items in current page
    total: int  # Total items available
    page: int  # Current page number
    page_size: int  # Items per page
    message: str = "Images retrieved successfully"


# Legacy alias for backward compatibility
ImagesListResponse = PaginatedImagesResponse


class ImagePublicResponse(BaseModel):
    """Public image info with public URL."""

    id: UUID
    filename: str
    user_id: UUID
    uploaded_at: datetime
    url: str
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    colors: Optional[list[str]] = None
    tag_vec: Optional[list[float]] = None
    color_vec: Optional[list[float]] = None

    class Config:
        from_attributes = True
