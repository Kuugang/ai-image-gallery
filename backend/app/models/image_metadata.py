import uuid
from datetime import datetime, timezone
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, SQLModel

from app.models.base import InDBBase

TAG_DIM = 4096
COLOR_DIM = 12


class ImageMetadataBase(SQLModel):
    description: Optional[str] = None
    tag_vec: list[float] | None = Field(default=None, sa_column=Column(Vector(TAG_DIM)))
    color_vec: list[float] | None = Field(
        default=None, sa_column=Column(Vector(COLOR_DIM))
    )
    ai_processing_status: str = Field(max_length=20, default="pending")


class ImageMetadataCreate(ImageMetadataBase):
    pass


class ImageMetadataUpdate(ImageMetadataBase):
    pass


class ImageMetadata(InDBBase, ImageMetadataBase, table=True):
    __tablename__ = "image_metadata"

    image_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("images.id", ondelete="CASCADE"), nullable=False)
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
        )
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ImageMetadataPublic(ImageMetadataBase):
    id: uuid.UUID
    image_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime


class ImageMetadataListPublic(SQLModel):
    data: list[ImageMetadataPublic]
    count: int
