import logging
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
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


# get token from cookies
def get_token_from_cookie(access_token: str | None = Cookie(None)) -> str:
    """Extract access token from cookie"""
    if not access_token:
        raise HTTPException(status_code=401, detail="Access token not found")
    return access_token


TokenDep = Annotated[str, Depends(get_token_from_cookie)]


async def get_current_user(token: TokenDep, super_client: SuperClient) -> UserIn:
    """get current user from token and validate same time"""
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
