import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from supabase._async.client import AsyncClient

from app.core.auth import SuperClient, TokenDep, get_super_client
from app.schemas.auth import (
    LoginRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    SignupRequest,
    Token,
    UpdatePasswordRequest,
    UserOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: SignupRequest,
    client: SuperClient,
) -> UserOut:
    """
    Create a new user account via Supabase Auth.

    - **email**: User email address
    - **password**: User password (min 6 characters)
    """
    try:
        response = await client.auth.sign_up(
            {
                "email": user_data.email,
                "password": user_data.password,
            }
        )

        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user",
            )

        return UserOut(
            access_token=response.session.access_token if response.session else None,
            refresh_token=response.session.refresh_token if response.session else None,
            user_id=response.user.id,
            email=response.user.email,
        )

    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=UserOut)
async def login(
    credentials: LoginRequest,
    client: SuperClient,
) -> UserOut:
    """
    Login with email and password.

    - **email**: User email address
    - **password**: User password
    """
    try:
        response = await client.auth.sign_in_with_password(
            {
                "email": credentials.email,
                "password": credentials.password,
            }
        )

        if not response or not response.user or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        return UserOut(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user_id=response.user.id,
            email=response.user.email,
        )

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
) -> None:
    """
    Logout the current user by revoking their session.

    Requires a valid JWT token in the Authorization header.
    """
    try:
        await client.auth.sign_out(jwt=token)
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logout failed",
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    client: SuperClient,
) -> Token:
    """
    Refresh an expired access token using a refresh token.

    - **refresh_token**: Valid refresh token from login/signup
    """
    try:
        response = await client.auth.refresh_session(refresh_data.refresh_token)

        if not response or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        return Token(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
        )

    except Exception as e:
        logger.error(f"Refresh token error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token",
        )


@router.post("/password-reset", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    client: SuperClient,
) -> dict[str, str]:
    """
    Request a password reset email.

    An email with a password reset link will be sent to the provided email address.

    - **email**: User email address
    """
    try:
        await client.auth.reset_password_for_email(reset_data.email)

        return {"message": "Password reset email sent. Please check your email."}

    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        # Don't reveal if email exists or not for security
        return {"message": "If an account exists, a password reset email will be sent."}


@router.post("/update-password", status_code=status.HTTP_200_OK)
async def update_password(
    update_data: UpdatePasswordRequest,
    client: SuperClient,
) -> dict[str, str]:
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

        return {"message": "Password updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update password error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update password",
        )


@router.get("/me", response_model=UserOut)
async def get_current_user_info(
    token: TokenDep,
    client: SuperClient,
) -> UserOut:
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

        return UserOut(
            access_token=token,
            user_id=response.user.id,
            email=response.user.email,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to get user info",
        )
