from typing import Annotated

from fastapi import Depends
from sqlmodel import Session
from supabase._async.client import AsyncClient

from app.core.auth import get_current_user, get_super_client, reusable_oauth2
from app.core.config import settings
from app.core.db import get_db
from app.schemas.auth import UserIn
from app.services.everypixel import EveryPixelService

CurrentUser = Annotated[UserIn, Depends(get_current_user)]
SessionDep = Annotated[Session, Depends(get_db)]
SuperClient = Annotated[AsyncClient, Depends(get_super_client)]

TokenDep = Annotated[str, Depends(reusable_oauth2)]

everypixel = EveryPixelService(
    base_url=settings.EVERYPIXEL_API_BASE_URL,
    client_id=settings.EVERYPIXEL_CLIENT_ID,
    client_secret=settings.EVERYPIXEL_CLIENT_SECRET,
)
