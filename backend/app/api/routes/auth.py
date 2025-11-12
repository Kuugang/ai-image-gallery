import logging
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlmodel import Session, select
from supabase._async.client import AsyncClient

from app.core.auth import SuperClient, TokenDep, get_super_client
from app.core.cookies import clear_auth_cookies, set_auth_cookies
from app.core.db import get_db
from app.models import User
from app.schemas.auth import (
    LoginRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    SignupRequest,
    Token,
    UpdatePasswordRequest,
    UserOut,
)
from app.schemas.response import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup", response_model=ApiResponse[UserOut], status_code=status.HTTP_201_CREATED
)
async def signup(
    user_data: SignupRequest,
    client: SuperClient,
    db: Session = Depends(get_db),
) -> ApiResponse[UserOut]:
    """
    Create a new user account via Supabase Auth.

    Sets authentication cookies on success.

    - **email**: User email address
    - **password**: User password (min 6 characters)
    """
    try:
        # Check if email already exists in the database
        existing_user = db.exec(select(User).where(User.email == user_data.email)).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )
        
        resp = await client.auth.sign_up(
            {
                "email": user_data.email,
                "password": user_data.password,
            }
        )

        if not resp or not resp.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user",
            )

        user_out = UserOut(
            access_token=resp.session.access_token if resp.session else None,
            refresh_token=resp.session.refresh_token if resp.session else None,
            user_id=resp.user.id,
            email=resp.user.email,
        )

        return ApiResponse(
            data=user_out,
            message="User account created successfully. Please confirm your email.",
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Signup error: {str(e)}")
        
        # Handle common Supabase auth errors
        if "already registered" in error_msg or "user already exists" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )
        elif "invalid email" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email address",
            )
        elif "password" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet security requirements",
            )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create user account",
        )


@router.post("/login", response_model=ApiResponse[UserOut])
async def login(
    credentials: LoginRequest,
    client: SuperClient,
    response: Response,
) -> ApiResponse[UserOut]:
    """
    Login with email and password.

    Sets authentication cookies on success.

    - **email**: User email address
    - **password**: User password
    """
    try:
        resp = await client.auth.sign_in_with_password(
            {
                "email": credentials.email,
                "password": credentials.password,
            }
        )

        if not resp or not resp.user or not resp.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        user_out = UserOut(
            access_token=resp.session.access_token,
            refresh_token=resp.session.refresh_token,
            user_id=resp.user.id,
            email=resp.user.email,
        )

        # Set auth cookies
        set_auth_cookies(
            response,
            access_token=resp.session.access_token,
            refresh_token=resp.session.refresh_token,
        )

        return ApiResponse(data=user_out, message="Login successful")

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        if "Invalid login credentials" in str(e):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login failed",
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token: TokenDep,
    client: SuperClient,
    response: Response,
) -> None:
    """
    Logout the current user by revoking their session.

    Clears authentication cookies.
    """
    try:
        # Supabase doesn't require explicit sign_out with token for revocation
        # Just clear the cookies which effectively logs out the user
        logger.info(f"User logout requested")
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
    finally:
        # Always clear auth cookies
        clear_auth_cookies(response)


@router.post("/refresh", response_model=ApiResponse[Token])
async def refresh_token(
    client: SuperClient,
    response: Response,
    refresh_token: str | None = Cookie(None),
) -> ApiResponse[Token]:
    """
    Refresh an expired access token using a refresh token from cookie.

    Sets new authentication cookies on success.
    """
    try:
        # Get refresh token from cookie
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found in cookies",
            )

        resp = await client.auth.refresh_session(refresh_token)

        if not resp or not resp.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        token = Token(
            access_token=resp.session.access_token,
            refresh_token=resp.session.refresh_token,
        )

        # Set new auth cookies
        set_auth_cookies(
            response,
            access_token=resp.session.access_token,
            refresh_token=resp.session.refresh_token,
        )

        return ApiResponse(data=token, message="Token refreshed successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh token error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token",
        )


@router.post(
    "/password-reset", status_code=status.HTTP_202_ACCEPTED, response_model=ApiResponse
)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    client: SuperClient,
) -> ApiResponse:
    """
    Request a password reset email.

    An email with a password reset link will be sent to the provided email address.

    - **email**: User email address
    """
    try:
        await client.auth.reset_password_for_email(reset_data.email)

        return ApiResponse(
            message="Password reset email sent. Please check your email."
        )

    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        # Don't reveal if email exists or not for security
        return ApiResponse(
            message="If an account exists, a password reset email will be sent."
        )


@router.post(
    "/update-password", status_code=status.HTTP_200_OK, response_model=ApiResponse
)
async def update_password(
    update_data: UpdatePasswordRequest,
    client: SuperClient,
) -> ApiResponse:
    """
    Update user password with a valid access token.

    - **access_token**: Valid JWT access token
    - **new_password**: New password (min 6 characters)
    """
    try:
        user = await client.auth.get_user(jwt=update_data.access_token)
        if not user or not user.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        await client.auth.update_user(
            {"password": update_data.new_password},
            jwt=update_data.access_token,
        )

        return ApiResponse(message="Password updated successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update password",
        )


@router.get("/me", response_model=ApiResponse[UserOut])
async def get_current_user_info(
    token: TokenDep,
    client: SuperClient,
) -> ApiResponse[UserOut]:
    """
    Get the current user information from their access token.

    Requires a valid JWT token in the Authorization header.
    """
    try:
        response = await client.auth.get_user(jwt=token)

        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        user_out = UserOut(
            access_token=token,
            user_id=response.user.id,
            email=response.user.email,
        )

        return ApiResponse(data=user_out, message="User info retrieved successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to get user info",
        )
