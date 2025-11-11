import logging
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from supabase import AsyncClientOptions
from supabase._async.client import AsyncClient, create_client

from app.core.config import settings
from app.schemas.auth import UserIn


class TokenExpiredException(Exception):
    """Raised when JWT token is expired or invalid"""

    def __init__(self, message: str = "Token expired or invalid"):
        self.message = message
        super().__init__(self.message)


async def get_super_client() -> AsyncClient:
    """for validation access_token init at life span event"""
    super_client = await create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY,
        options=AsyncClientOptions(
            postgrest_client_timeout=10, storage_client_timeout=10
        ),
    )
    if not super_client:
        raise HTTPException(status_code=500, detail="Super client not initialized")
    return super_client


SuperClient = Annotated[AsyncClient, Depends(get_super_client)]


# auto get token from header
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)
TokenDep = Annotated[str, Depends(reusable_oauth2)]


async def get_current_user(token: TokenDep, super_client: SuperClient) -> UserIn:
    """get current user from token and  validate same time"""
    try:
        user_rsp = await super_client.auth.get_user(jwt=token)
        if not user_rsp:
            logging.error("User not found")
            raise TokenExpiredException("User not found")
        return UserIn(**user_rsp.user.model_dump(), access_token=token)
    except TokenExpiredException:
        raise
    except Exception as e:
        logging.error(f"Auth error: {str(e)}")
        raise TokenExpiredException(f"Authentication failed: {str(e)}")
