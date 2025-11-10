from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import CITEXT
from sqlmodel import Field, SQLModel


class Color(SQLModel, table=True):
    __tablename__ = "colors"
    hex: str = Field(sa_column=Column(CITEXT(), primary_key=True))  # '#RRGGBB'


class ImageColor(SQLModel, table=True):
    __tablename__ = "image_colors"
    image_id: str = Field(sa_column=Column(ForeignKey("images.id"), primary_key=True))
    color_hex: str = Field(
        sa_column=Column(CITEXT(), ForeignKey("colors.hex"), primary_key=True)
    )
