import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models.base import InDBBase


# Shared properties
class ImageBase(SQLModel):
    filename: Optional[str] = Field(default=None, max_length=1024)
    original_path: str
    thumbnail_path: Optional[str] = None


# Properties to receive on image creation
class ImageCreate(ImageBase):
    pass


# Properties to receive on image update
class ImageUpdate(ImageBase):
    pass


# Database model
class Image(InDBBase, ImageBase, table=True):
    __tablename__ = "images"
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


# Properties to return via API
class ImagePublic(ImageBase):
    id: uuid.UUID
    user_id: uuid.UUID
    uploaded_at: datetime


class ImagesPublic(SQLModel):
    data: list[ImagePublic]
    count: int
