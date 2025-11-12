"""Background tasks for image processing."""

import asyncio
import logging
from uuid import UUID

from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models.image import Image
from app.models.image_colors import Color, ImageColor
from app.models.image_metadata import ImageMetadata
from app.models.image_tags import ImageTag, Tag
from app.services.everypixel import EveryPixelService
from app.utils.vectors import color_vector, tag_vector

logger = logging.getLogger(__name__)


async def process_image_async(
    image_id: UUID,
    file_path: str,
    user_id: UUID,
    signed_url: str,
) -> None:
    """
    Process image with AI in background.

    - Extract keywords, colors, and caption
    - Update image_metadata with results
    - Mark as completed
    """
    try:
        logger.info(f"Starting async image processing for {image_id}")

        service = EveryPixelService(
            settings.EVERYPIXEL_API_BASE_URL,
            settings.EVERYPIXEL_CLIENT_ID,
            settings.EVERYPIXEL_CLIENT_SECRET,
        )

        keywording_data = await service.keywords_by_url(
            signed_url,
            num_keywords=5,
            colors=True,
            num_colors=3,
            lang="en",
        )

        captioning_data = await service.captions_by_url(signed_url)

        # Extract keywords and colors
        keywords = []
        colors_hex = []
        caption = None

        if keywording_data and keywording_data.get("status") == "ok":
            if keywording_data.get("keywords"):
                keywords = [kw["keyword"] for kw in keywording_data["keywords"]]

            if keywording_data.get("colors"):
                colors_hex = [color["hex"] for color in keywording_data["colors"]]

            logger.info(
                f"Extracted {len(keywords)} keywords and {len(colors_hex)} colors for {image_id}"
            )

        if captioning_data and captioning_data.get("status"):
            caption = captioning_data.get("result", {}).get("caption")
            logger.info(f"Extracted caption for {image_id}")

        # Generate vectors for semantic search
        tag_vec = tag_vector(keywords) if keywords else None
        color_vec = color_vector(colors_hex) if colors_hex else None

        logger.info(
            f"Generated vectors for {image_id}: "
            f"tag_vec={len(tag_vec) if tag_vec else 0}d, "
            f"color_vec={len(color_vec) if color_vec else 0}d"
        )

        # Update database with results
        with Session(engine) as session:
            # Get or create metadata
            statement = select(ImageMetadata).where(ImageMetadata.image_id == image_id)
            db_metadata = session.exec(statement).first()

            if not db_metadata:
                db_metadata = ImageMetadata(
                    image_id=image_id,
                    user_id=user_id,
                )

            # Update with AI results and vectors
            db_metadata.description = caption
            db_metadata.tag_vec = tag_vec
            db_metadata.color_vec = color_vec
            db_metadata.ai_processing_status = "completed"

            session.add(db_metadata)
            session.commit()

            # Save keywords to tags table
            for keyword in keywords:
                # Get or create tag
                tag_statement = select(Tag).where(Tag.name == keyword.lower())
                db_tag = session.exec(tag_statement).first()

                if not db_tag:
                    db_tag = Tag(name=keyword.lower())
                    session.add(db_tag)
                    session.commit()

                # Create relationship between image and tag
                image_tag_statement = select(ImageTag).where(
                    (ImageTag.image_id == str(image_id))
                    & (ImageTag.tag_name == keyword.lower())
                )
                if not session.exec(image_tag_statement).first():
                    db_image_tag = ImageTag(
                        image_id=str(image_id),
                        tag_name=keyword.lower(),
                    )
                    session.add(db_image_tag)

            session.commit()

            # Save colors to colors table
            for color_hex in colors_hex:
                # Get or create color
                color_statement = select(Color).where(Color.hex == color_hex.lower())
                db_color = session.exec(color_statement).first()

                if not db_color:
                    db_color = Color(hex=color_hex.lower())
                    session.add(db_color)
                    session.commit()

                # Create relationship between image and color
                image_color_statement = select(ImageColor).where(
                    (ImageColor.image_id == str(image_id))
                    & (ImageColor.color_hex == color_hex.lower())
                )
                if not session.exec(image_color_statement).first():
                    db_image_color = ImageColor(
                        image_id=str(image_id),
                        color_hex=color_hex.lower(),
                    )
                    session.add(db_image_color)

            session.commit()

            logger.info(
                f"Image processing completed for {image_id}. "
                f"Extracted {len(keywords)} keywords and {len(colors_hex)} colors"
            )

    except Exception as e:
        logger.error(f"Error processing image {image_id}: {str(e)}")
        # Update status to failed
        try:
            with Session(engine) as session:
                statement = select(ImageMetadata).where(
                    ImageMetadata.image_id == image_id
                )
                db_metadata = session.exec(statement).first()
                if db_metadata:
                    db_metadata.ai_processing_status = "failed"
                    session.add(db_metadata)
                    session.commit()
        except Exception as e2:
            logger.error(f"Error updating metadata status: {str(e2)}")


def process_image_background(
    image_id: UUID,
    file_path: str,
    user_id: UUID,
    signed_url: str,
) -> None:
    """Sync wrapper for async image processing to work with BackgroundTasks."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(
        process_image_async(image_id, file_path, user_id, signed_url)
    )
