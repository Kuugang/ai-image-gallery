import logging
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

import numpy as np
from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep, SuperClient
from app.core.config import settings
from app.models.image import Image
from app.models.image_colors import ImageColor
from app.models.image_metadata import ImageMetadata
from app.models.image_tags import ImageTag
from app.schemas.image import (
    ImageMetadataResponse,
    ImagePublicResponse,
    ImagesListResponse,
    ImageUploadResponse,
)
from app.schemas.response import ApiResponse
from app.services.background_tasks import process_image_async
from app.utils.vectors import color_query_one_hot, color_vector, tag_vector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

# Supabase Storage bucket name
BUCKET_NAME = "images"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def get_image_tags_and_colors(
    session: any, image_id: UUID
) -> tuple[list[str], list[str]]:
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


@router.post(
    "/upload",
    response_model=ApiResponse[list[ImageUploadResponse] | ImageUploadResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    user: CurrentUser,
    session: SessionDep,
    client: SuperClient,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
) -> ApiResponse[list[ImageUploadResponse] | ImageUploadResponse]:
    """
    Upload one or more images to Supabase Storage.

    - **files**: Image file(s) (JPG, PNG, GIF, WebP)
    - Can upload single file or multiple files
    - Returns: Wrapped response with uploaded image metadata
    - AI processing happens in background (don't block upload)
    """
    try:
        # Ensure files is always a list
        if not isinstance(files, list):
            files = [files]

        allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        responses = []

        for file in files:
            try:
                # Validate file type
                if file.content_type not in allowed_types:
                    logger.warning(
                        f"Invalid file type for {file.filename}: {file.content_type}"
                    )
                    continue

                # Validate file size
                content = await file.read()
                if len(content) > MAX_FILE_SIZE:
                    logger.warning(
                        f"File too large: {file.filename} ({len(content) / 1024 / 1024:.1f}MB)"
                    )
                    continue

                # Create unique file path
                file_id = str(UUID(user.id))

                # Generate unique filename to avoid conflicts
                # Format: {original_name_without_ext}_{uuid4}.{ext}
                file_path_obj = Path(file.filename)
                unique_filename = (
                    f"{file_path_obj.stem}_{uuid4()}{file_path_obj.suffix}"
                )
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
                    logger.error(f"Storage upload error for {file.filename}: {str(e)}")
                    continue

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

                logger.info(
                    f"Image metadata created: {db_metadata.id} with status=pending"
                )

                # Schedule async image processing in background
                try:
                    res = await client.storage.from_("images").create_signed_url(
                        file_path, 600
                    )
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

                responses.append(
                    ImageUploadResponse(
                        id=db_image.id,
                        filename=db_image.filename,
                        original_path=db_image.original_path,
                        user_id=db_image.user_id,
                        uploaded_at=db_image.uploaded_at,
                        ai_processing_status="pending",
                    )
                )

            except Exception as e:
                logger.error(f"Error uploading {file.filename}: {str(e)}")
                continue

        # Return single response or list based on input
        if len(responses) == 1:
            return ApiResponse(data=responses[0], message="Image uploaded successfully")
        return ApiResponse(
            data=responses, message=f"{len(responses)} images uploaded successfully"
        )

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload failed",
        )


@router.get("/{image_id}", response_model=ApiResponse[ImageMetadataResponse])
async def get_image(
    image_id: str,
    session: SessionDep,
) -> ApiResponse[ImageMetadataResponse]:
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

        response_data = ImageMetadataResponse(
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
            ai_processing_status=(
                db_metadata.ai_processing_status if db_metadata else "pending"
            ),
        )

        return ApiResponse(data=response_data, message="Image retrieved successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get image error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get image",
        )


@router.get("", response_model=ImagesListResponse)
async def get_images(
    user: CurrentUser,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tag: Optional[str] = Query(
        None, description="Filter by tag name(s) - comma separated (e.g., person,women)"
    ),
    desc: Optional[str] = Query(None, description="Search by description text"),
    color: Optional[str] = Query(
        None,
        description="Filter by color(s) - comma separated (e.g., red,blue or #FF0000,#0000FF)",
    ),
) -> ImagesListResponse:
    """
    Get images for current user with optional filtering.

    - **skip**: Number of images to skip
    - **limit**: Maximum number of images to return
    - **tag**: Optional tag filter(s) - comma separated (e.g., person,women)
    - **desc**: Optional description search text
    - **color**: Optional color filter(s) - comma separated (e.g., red,blue or #FF0000,#0000FF)

    If no query params: Returns images sorted by upload date (newest first)
    """
    try:
        user_uuid = UUID(user.id)

        # Parse comma-separated values
        tag_list = [t.strip() for t in tag.split(",")] if tag else None
        color_list = [c.strip() for c in color.split(",")] if color else None

        # Handle tag and/or description filtering
        tag_matched_ids = None
        desc_matched_ids = None
        color_matched_ids = None

        # Search by tag name(s)
        if tag_list:
            tag_image_ids_list = []
            for tag_name in tag_list:
                tag_results = session.exec(
                    select(ImageTag.image_id).where(
                        ImageTag.tag_name.ilike(f"%{tag_name}%")
                    )
                )
                tag_image_ids_list.append({row for row in tag_results.all()})

            # Combine all tag results with OR logic
            tag_matched_ids = (
                set().union(*tag_image_ids_list) if tag_image_ids_list else set()
            )

        # Search by description
        if desc:
            description_query = (
                select(Image)
                .join(ImageMetadata)
                .where(
                    Image.user_id == user_uuid,
                    ImageMetadata.description.ilike(f"%{desc}%"),
                )
            )
            desc_results = session.exec(description_query)
            desc_matched_ids = {img.id for img in desc_results.all()}

        # Handle color filter
        if color_list:
            # Get all user's images with metadata and colors
            all_images_query = (
                select(Image, ImageMetadata, ImageColor)
                .join(ImageMetadata, Image.id == ImageMetadata.image_id)
                .outerjoin(ImageColor, Image.id == ImageColor.image_id)
                .where(Image.user_id == user_uuid)
            )
            result = session.exec(all_images_query)
            rows = result.all()

            # Find images matching any of the colors (without scoring)
            color_matched_ids = set()

            for color_query_str in color_list:
                try:
                    query_vec = color_query_one_hot(color_query_str)
                    query_vec_np = np.array(query_vec, dtype=np.float32)

                    for row in rows:
                        img, metadata, color = row[0], row[1], row[2]
                        if metadata.color_vec is not None:
                            stored_vec = np.array(metadata.color_vec, dtype=np.float32)
                            # Use a threshold to determine if colors match
                            similarity = float(np.dot(query_vec_np, stored_vec))
                            if similarity >= 0.3:  # Color match threshold
                                color_matched_ids.add(img.id)
                except ValueError:
                    logger.warning(f"Invalid color: {color_query_str}")
                    continue

            if not color_matched_ids:
                return ImagesListResponse(
                    data=[],
                    count=0,
                    total=0,
                    page=skip // limit + 1 if limit > 0 else 1,
                    page_size=limit,
                )

        # Combine all filters
        if (
            tag_matched_ids is not None
            or desc_matched_ids is not None
            or color_matched_ids is not None
        ):
            # Determine which IDs to include based on what filters are active
            if (
                tag_matched_ids is not None
                and desc_matched_ids is not None
                and color_matched_ids is not None
            ):
                # All three: AND logic
                matched_ids = tag_matched_ids & desc_matched_ids & color_matched_ids
            elif tag_matched_ids is not None and desc_matched_ids is not None:
                # Tag and description: AND logic
                matched_ids = tag_matched_ids & desc_matched_ids
            elif tag_matched_ids is not None and color_matched_ids is not None:
                # Tag and color: AND logic
                matched_ids = tag_matched_ids & color_matched_ids
            elif desc_matched_ids is not None and color_matched_ids is not None:
                # Description and color: AND logic
                matched_ids = desc_matched_ids & color_matched_ids
            elif tag_matched_ids is not None:
                # Only tag filter
                matched_ids = tag_matched_ids
            elif desc_matched_ids is not None:
                # Only description filter
                matched_ids = desc_matched_ids
            else:
                # Only color filter
                matched_ids = color_matched_ids

            if not matched_ids:
                return ImagesListResponse(
                    data=[],
                    count=0,
                    total=0,
                    page=skip // limit + 1 if limit > 0 else 1,
                    page_size=limit,
                )

            # Get total count
            count_query = select(Image).where(
                Image.user_id == user_uuid,
                Image.id.in_(list(matched_ids)),
            )
            count_result = session.exec(count_query)
            total = len(count_result.all())

            # Get paginated results
            statement = (
                select(Image)
                .where(
                    Image.user_id == user_uuid,
                    Image.id.in_(list(matched_ids)),
                )
                .order_by(Image.uploaded_at.desc())
                .offset(skip)
                .limit(limit)
            )
            db_images = session.exec(statement).all()

            # Build response
            items = []
            for img in db_images:
                # Get metadata
                meta_query = select(ImageMetadata).where(ImageMetadata.image_id == img.id)
                db_metadata = session.exec(meta_query).first()

                # Get tags and colors
                tags, colors_list = get_image_tags_and_colors(session, img.id)

                items.append(
                    ImageMetadataResponse(
                        id=img.id,
                        filename=img.filename,
                        original_path=img.original_path,
                        thumbnail_path=img.thumbnail_path,
                        user_id=img.user_id,
                        uploaded_at=img.uploaded_at,
                        description=db_metadata.description if db_metadata else None,
                        tags=tags if tags else None,
                        colors=colors_list if colors_list else None,
                        tag_vec=db_metadata.tag_vec if db_metadata else None,
                        color_vec=db_metadata.color_vec if db_metadata else None,
                        ai_processing_status=(
                            db_metadata.ai_processing_status
                            if db_metadata
                            else "pending"
                        ),
                    )
                )

            page = skip // limit + 1 if limit > 0 else 1
            return ImagesListResponse(
                data=items,
                count=len(items),
                total=total,
                page=page,
                page_size=limit,
            )

        # Default: list all images sorted by upload date
        else:
            # Get total count
            count_statement = select(Image).where(Image.user_id == user_uuid)
            all_images = session.exec(count_statement).all()
            total = len(all_images)

            # Get paginated results sorted by upload date (newest first)
            statement = (
                select(Image)
                .where(Image.user_id == user_uuid)
                .order_by(Image.uploaded_at.desc())
                .offset(skip)
                .limit(limit)
            )
            db_images = session.exec(statement).all()

            # Build response
            items = []
            for img in db_images:
                # Get metadata
                meta_query = select(ImageMetadata).where(ImageMetadata.image_id == img.id)
                db_metadata = session.exec(meta_query).first()

                # Get tags and colors
                tags, colors_list = get_image_tags_and_colors(session, img.id)

                items.append(
                    ImageMetadataResponse(
                        id=img.id,
                        filename=img.filename,
                        original_path=img.original_path,
                        thumbnail_path=img.thumbnail_path,
                        user_id=img.user_id,
                        uploaded_at=img.uploaded_at,
                        description=db_metadata.description if db_metadata else None,
                        tags=tags if tags else None,
                        colors=colors_list if colors_list else None,
                        tag_vec=db_metadata.tag_vec if db_metadata else None,
                        color_vec=db_metadata.color_vec if db_metadata else None,
                        ai_processing_status=(
                            db_metadata.ai_processing_status
                            if db_metadata
                            else "pending"
                        ),
                    )
                )

            page = skip // limit + 1 if limit > 0 else 1
            return ImagesListResponse(
                data=items,
                count=len(items),
                total=total,
                page=page,
                page_size=limit,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List images error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to list images",
        )


@router.get("/similar", response_model=ImagesListResponse)
async def get_similar_images(
    user: CurrentUser,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tag: Optional[str] = Query(
        None, description="Filter by tag name(s) - comma separated (e.g., person,women)"
    ),
    desc: Optional[str] = Query(None, description="Search by description text"),
    color: Optional[str] = Query(
        None,
        description="Filter by color(s) - comma separated (e.g., red,blue or #FF0000,#0000FF)",
    ),
    threshold: float = Query(
        0.5, ge=0.0, le=1.0, description="Similarity threshold (0.0-1.0) for matching"
    ),
) -> ImagesListResponse:
    """
    Get similar images based on tag vectors and optional filters.

    - **skip**: Number of images to skip
    - **limit**: Maximum number of images to return
    - **tag**: Optional tag filter(s) - comma separated (e.g., person,women)
    - **desc**: Optional description search text
    - **color**: Optional color filter(s) - comma separated (e.g., red,blue or #FF0000,#0000FF)
    - **threshold**: Similarity threshold (0.0-1.0) for tag matching (default: 0.5)

    Returns images sorted by tag similarity (highest first), optionally filtered by other criteria.
    """
    try:
        user_uuid = UUID(user.id)

        # Parse comma-separated values
        tag_list = [t.strip() for t in tag.split(",")] if tag else None
        color_list = [c.strip() for c in color.split(",")] if color else None

        # Get all user's images with metadata and colors
        all_images_query = (
            select(Image, ImageMetadata, ImageColor)
            .join(ImageMetadata, Image.id == ImageMetadata.image_id)
            .outerjoin(ImageColor, Image.id == ImageColor.image_id)
            .where(Image.user_id == user_uuid)
        )
        result = session.exec(all_images_query)
        rows = result.all()

        if not rows:
            return ImagesListResponse(
                data=[],
                count=0,
                total=0,
                page=skip // limit + 1 if limit > 0 else 1,
                page_size=limit,
            )

        # Calculate similarity scores for all images based on tag vectors
        image_scores = []

        for row in rows:
            img, metadata, color = row[0], row[1], row[2]

            # Skip images without tag vectors
            if metadata.tag_vec is None:
                continue

            stored_vec = np.array(metadata.tag_vec, dtype=np.float32)

            # If tag filters provided, check if image matches them first
            tag_match = True
            if tag_list:
                img_tags, _ = get_image_tags_and_colors(session, img.id)
                matches = [
                    tag.lower() in [t.lower() for t in img_tags] for tag in tag_list
                ]
                tag_match = any(matches)  # OR logic: match any tag

            if not tag_match:
                continue

            # If description filter provided, check it
            desc_match = True
            if desc:
                if (
                    metadata.description is None
                    or desc.lower() not in metadata.description.lower()
                ):
                    desc_match = False

            if not desc_match:
                continue

            # If color filter provided, check it
            color_match = True
            if color_list:
                if metadata.color_vec is None:
                    color_match = False
                else:
                    color_matched = False
                    for color_query_str in color_list:
                        try:
                            query_vec = color_query_one_hot(color_query_str)
                            query_vec_np = np.array(query_vec, dtype=np.float32)
                            color_vec_np = np.array(
                                metadata.color_vec, dtype=np.float32
                            )
                            similarity = float(np.dot(query_vec_np, color_vec_np))
                            if similarity >= 0.3:
                                color_matched = True
                                break
                        except ValueError:
                            continue
                    color_match = color_matched

            if not color_match:
                continue

            # Calculate average similarity across all tag vectors
            # Since we don't have a query image, use the vector magnitude as a proxy
            # or just use a default high score for all that pass filters
            similarity_score = float(np.linalg.norm(stored_vec))

            image_scores.append((img, metadata, similarity_score))

        if not image_scores:
            return ImagesListResponse(
                data=[],
                count=0,
                total=0,
                page=skip // limit + 1 if limit > 0 else 1,
                page_size=limit,
            )

        # Sort by similarity score descending
        sorted_images = sorted(image_scores, key=lambda x: x[2], reverse=True)

        # Apply pagination
        total = len(sorted_images)
        paginated = sorted_images[skip : skip + limit]

        # Build response
        items = []
        for img, metadata, score in paginated:
            tags, colors_list = get_image_tags_and_colors(session, img.id)
            items.append(
                ImageMetadataResponse(
                    id=img.id,
                    filename=img.filename,
                    original_path=img.original_path,
                    thumbnail_path=img.thumbnail_path,
                    user_id=img.user_id,
                    uploaded_at=img.uploaded_at,
                    description=metadata.description,
                    tags=tags if tags else None,
                    colors=colors_list if colors_list else None,
                    tag_vec=metadata.tag_vec,
                    color_vec=metadata.color_vec,
                    ai_processing_status=metadata.ai_processing_status,
                )
            )

        return ImagesListResponse(
            data=items,
            count=len(items),
            total=total,
            page=skip // limit + 1 if limit > 0 else 1,
            page_size=limit,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Similar images error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to get similar images",
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
