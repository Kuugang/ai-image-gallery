from datetime import datetime, timezone

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import CITEXT
from sqlmodel import Field, SQLModel


class Tag(SQLModel, table=True):
    __tablename__ = "tags"
    name: str = Field(sa_column=Column(CITEXT(), primary_key=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ImageTag(SQLModel, table=True):
    __tablename__ = "image_tags"

    image_id: str = Field(
        sa_column=Column(
            ForeignKey(
                "images.id",
                onupdate="CASCADE",
                ondelete="CASCADE",
            ),
            primary_key=True,
        ),
    )
    tag_name: str = Field(
        sa_column=Column(CITEXT(), ForeignKey("tags.name"), primary_key=True)
    )
