import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, SuperClient
from app.core.config import settings
from app.models.image import Image
from app.models.image_metadata import ImageMetadata
from app.models.image_colors import ImageColor
from app.models.image_tags import ImageTag
from app.schemas.image import (
    ImageMetadataResponse,
    ImagePublicResponse,
    ImageUploadResponse,
    ImagesListResponse,
)
from app.services.background_tasks import process_image_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

# Supabase Storage bucket name
BUCKET_NAME = "images"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def get_image_tags_and_colors(session: any, image_id: UUID) -> tuple[list[str], list[str]]:
    """
    Fetch tags and colors for an image from relationship tables.

    Returns: (tags, colors) tuples
    """
    # Fetch tags
    tags_statement = select(ImageTag).where(ImageTag.image_id == str(image_id))
    image_tags = session.exec(tags_statement).all()
    tags = [tag.tag_name for tag in image_tags]

    # Fetch colors
    colors_statement = select(ImageColor).where(ImageColor.image_id == str(image_id))
    image_colors = session.exec(colors_statement).all()
    colors = [color.color_hex for color in image_colors]

    return tags, colors


@router.post("/upload", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    user: CurrentUser,
    session: SessionDep,
    client: SuperClient,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> ImageUploadResponse:
    """
    Upload an image to Supabase Storage.

    - **file**: Image file (JPG, PNG, GIF, WebP)
    - Returns: ImageUploadResponse with upload details
    - AI processing happens in background (don't block upload)
    """
    try:
        # Validate file type
        allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file.content_type} not allowed. Allowed: {', '.join(allowed_types)}",
            )

        # Validate file size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_PAYLOAD_TOO_LARGE,
                detail=f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB limit",
            )

        # Create unique file path
        file_id = str(UUID(user.id))

        # Generate unique filename to avoid conflicts
        # Format: {original_name_without_ext}_{uuid4}.{ext}
        file_path_obj = Path(file.filename)
        unique_filename = f"{file_path_obj.stem}_{uuid4()}{file_path_obj.suffix}"
        file_path = f"{file_id}/{unique_filename}"

        # Upload to Supabase Storage
        try:
            response = await client.storage.from_(BUCKET_NAME).upload(
                path=file_path,
                file=content,
                file_options={"content-type": file.content_type},
            )
            logger.info(f"File uploaded: {file_path}")
        except Exception as e:
            logger.error(f"Storage upload error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage",
            )

        # Create database record
        db_image = Image(
            filename=file.filename,
            original_path=file_path,
            thumbnail_path=None,
            user_id=UUID(user.id),
        )

        session.add(db_image)
        session.commit()
        session.refresh(db_image)

        logger.info(f"Image record created: {db_image.id}")

        # Create initial metadata record with "pending" status
        db_metadata = ImageMetadata(
            image_id=db_image.id,
            user_id=UUID(user.id),
            ai_processing_status="pending",
        )

        session.add(db_metadata)
        session.commit()
        session.refresh(db_metadata)

        logger.info(f"Image metadata created: {db_metadata.id} with status=pending")

        # Schedule async image processing in background
        # Don't wait for it - return immediately to user
        try:
            res = await client.storage.from_("images").create_signed_url(file_path, 600)
            signed_url = res["signedURL"]

            background_tasks.add_task(
                process_image_async,
                image_id=db_image.id,
                file_path=file_path,
                user_id=UUID(user.id),
                signed_url=signed_url,
            )
            logger.info(f"Scheduled async processing for image {db_image.id}")

        except Exception as e:
            logger.warning(f"Could not schedule AI processing: {str(e)}")
            # Continue anyway - image is uploaded, just won't have AI metadata

        return ImageUploadResponse(
            id=db_image.id,
            filename=db_image.filename,
            original_path=db_image.original_path,
            user_id=db_image.user_id,
            uploaded_at=db_image.uploaded_at,
            ai_processing_status="pending",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload failed",
        )


@router.get("/{image_id}", response_model=ImageMetadataResponse)
async def get_image(
    image_id: str,
    session: SessionDep,
) -> ImageMetadataResponse:
    """
    Get image details by ID with AI metadata.

    - **image_id**: Image UUID
    """
    try:
        statement = select(Image).where(Image.id == UUID(image_id))
        db_image = session.exec(statement).first()

        if not db_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found",
            )

        # Get metadata
        meta_statement = select(ImageMetadata).where(
            ImageMetadata.image_id == UUID(image_id)
        )
        db_metadata = session.exec(meta_statement).first()

        # Get tags and colors
        tags, colors = get_image_tags_and_colors(session, UUID(image_id))

        return ImageMetadataResponse(
            id=db_image.id,
            filename=db_image.filename,
            original_path=db_image.original_path,
            thumbnail_path=db_image.thumbnail_path,
            user_id=db_image.user_id,
            uploaded_at=db_image.uploaded_at,
            description=db_metadata.description if db_metadata else None,
            tags=tags if tags else None,
            colors=colors if colors else None,
            tag_vec=db_metadata.tag_vec if db_metadata else None,
            color_vec=db_metadata.color_vec if db_metadata else None,
            ai_processing_status=db_metadata.ai_processing_status if db_metadata else "pending",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get image error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get image",
        )


@router.get("", response_model=ImagesListResponse)
async def list_images(
    user: CurrentUser,
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
) -> ImagesListResponse:
    """
    List all images for current user with pagination.

    - **skip**: Number of images to skip
    - **limit**: Maximum number of images to return
    """
    try:
        # Get total count
        count_statement = select(Image).where(Image.user_id == UUID(user.id))
        all_images = session.exec(count_statement).all()
        total_count = len(all_images)

        # Get paginated results
        statement = (
            select(Image)
            .where(Image.user_id == UUID(user.id))
            .offset(skip)
            .limit(limit)
            .order_by(Image.uploaded_at.desc())
        )
        db_images = session.exec(statement).all()

        images = []
        for img in db_images:
            # Get metadata for each image
            meta_statement = select(ImageMetadata).where(
                ImageMetadata.image_id == img.id
            )
            db_metadata = session.exec(meta_statement).first()

            # Get tags and colors
            tags, colors = get_image_tags_and_colors(session, img.id)

            images.append(
                ImageMetadataResponse(
                    id=img.id,
                    filename=img.filename,
                    original_path=img.original_path,
                    thumbnail_path=img.thumbnail_path,
                    user_id=img.user_id,
                    uploaded_at=img.uploaded_at,
                    description=db_metadata.description if db_metadata else None,
                    tags=tags if tags else None,
                    colors=colors if colors else None,
                    tag_vec=db_metadata.tag_vec if db_metadata else None,
                    color_vec=db_metadata.color_vec if db_metadata else None,
                    ai_processing_status=db_metadata.ai_processing_status if db_metadata else "pending",
                )
            )

        page = skip // limit + 1 if limit > 0 else 1
        return ImagesListResponse(
            data=images,
            count=len(images),
            total=total_count,
            page=page,
            page_size=limit,
        )

    except Exception as e:
        logger.error(f"List images error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to list images",
        )


@router.get("/download/{image_id}")
async def download_image(
    image_id: str,
    user: CurrentUser,
    session: SessionDep,
    client: SuperClient,
):
    """
    Download an image file from storage.

    - **image_id**: Image UUID
    - Returns: File download
    """
    try:
        # Verify image exists and belongs to user
        statement = select(Image).where(Image.id == UUID(image_id))
        db_image = session.exec(statement).first()

        if not db_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found",
            )

        if db_image.user_id != UUID(user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to download this image",
            )

        # Download from storage
        try:
            file_data = await client.storage.from_(BUCKET_NAME).download(
                db_image.original_path
            )

            return {
                "filename": db_image.filename,
                "content": file_data.decode("utf-8", errors="ignore"),
                "size": len(file_data),
            }

        except Exception as e:
            logger.error(f"Storage download error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to download file from storage",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Download failed",
        )


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: str,
    user: CurrentUser,
    session: SessionDep,
    client: SuperClient,
) -> None:
    """
    Delete an image and remove from storage.

    - **image_id**: Image UUID
    """
    try:
        # Get image
        statement = select(Image).where(Image.id == UUID(image_id))
        db_image = session.exec(statement).first()

        if not db_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found",
            )

        # Verify ownership
        if db_image.user_id != UUID(user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this image",
            )

        # Delete from storage
        try:
            await client.storage.from_(BUCKET_NAME).remove([db_image.original_path])
            logger.info(f"File deleted from storage: {db_image.original_path}")
        except Exception as e:
            logger.warning(f"Storage delete warning: {str(e)}")
            # Continue with database deletion even if storage fails

        # Delete from database (will cascade delete metadata)
        session.delete(db_image)
        session.commit()

        logger.info(f"Image deleted: {image_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delete failed",
        )


@router.get("/public-url/{image_id}", response_model=ImagePublicResponse)
async def get_public_url(
    image_id: str,
    session: SessionDep,
) -> ImagePublicResponse:
    """
    Get public URL for an image with metadata.

    - **image_id**: Image UUID
    - Returns: Public URL and image metadata
    """
    try:
        statement = select(Image).where(Image.id == UUID(image_id))
        db_image = session.exec(statement).first()

        if not db_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found",
            )

        # Get metadata
        meta_statement = select(ImageMetadata).where(
            ImageMetadata.image_id == UUID(image_id)
        )
        db_metadata = session.exec(meta_statement).first()

        # Get tags and colors
        tags, colors = get_image_tags_and_colors(session, UUID(image_id))

        # Construct public URL
        public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{db_image.original_path}"

        return ImagePublicResponse(
            id=db_image.id,
            filename=db_image.filename,
            user_id=db_image.user_id,
            uploaded_at=db_image.uploaded_at,
            url=public_url,
            description=db_metadata.description if db_metadata else None,
            tags=tags if tags else None,
            colors=colors if colors else None,
            tag_vec=db_metadata.tag_vec if db_metadata else None,
            color_vec=db_metadata.color_vec if db_metadata else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get public URL error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get public URL",
        )
