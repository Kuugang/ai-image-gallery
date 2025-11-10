from typing import Annotated

from fastapi import Depends
from sqlmodel import Session
from supabase._async.client import AsyncClient

from app.core.auth import get_current_user, get_super_client, reusable_oauth2
from app.core.db import get_db
from app.schemas.auth import UserIn

CurrentUser = Annotated[UserIn, Depends(get_current_user)]
SessionDep = Annotated[Session, Depends(get_db)]
SuperClient = Annotated[AsyncClient, Depends(get_super_client)]

TokenDep = Annotated[str, Depends(reusable_oauth2)]
