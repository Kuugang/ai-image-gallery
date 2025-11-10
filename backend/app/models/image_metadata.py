import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel

from app.models.base import InDBBase

# If you might run on SQLite locally, see the JSON fallback below.


# Shared properties
class ImageMetadataBase(SQLModel):
    description: Optional[str] = None

    # Postgres ARRAY types (correct)
    tags: Optional[list[str]] = Field(
        default=None, sa_column=Column(ARRAY(String))  # ARRAY(TEXT) equivalent
    )
    colors: Optional[list[str]] = Field(
        default=None, sa_column=Column(ARRAY(String(7)))  # "#RRGGBB"
    )

    ai_processing_status: str = Field(max_length=20, default="pending")


class ImageMetadataCreate(ImageMetadataBase):
    pass


class ImageMetadataUpdate(ImageMetadataBase):
    pass


class ImageMetadata(InDBBase, ImageMetadataBase, table=True):
    # If you need ON DELETE CASCADE, define it via SQLAlchemy ForeignKey:

    __tablename__ = "image_metadata"

    image_id: uuid.UUID = Field(
        sa_column=Column(
            # Use UUID if you’re importing it from sqlalchemy.dialects.postgresql
            # Otherwise, keep it as String and cast in your app.
            ForeignKey("images.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("auth.users.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ImageMetadataPublic(ImageMetadataBase):
    id: uuid.UUID
    image_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime


class ImageMetadataListPublic(SQLModel):
    data: list[ImageMetadataPublic]
    count: int
