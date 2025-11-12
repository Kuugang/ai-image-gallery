"""Cookie utilities for authentication."""
from datetime import datetime, timedelta, timezone

from fastapi import Response


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str | None = None,
    max_age: int = 3600,  # 1 hour for access token
    refresh_max_age: int = 604800,  # 7 days for refresh token
) -> None:
    """
    Set authentication cookies in the response.

    Args:
        response: FastAPI Response object
        access_token: JWT access token
        refresh_token: Refresh token (optional)
        max_age: Access token cookie max age in seconds (default: 1 hour)
        refresh_max_age: Refresh token cookie max age in seconds (default: 7 days)
    """
    # Use UTC timezone for expiry dates
    expires = datetime.now(timezone.utc) + timedelta(seconds=max_age)
    
    # Set access token cookie (HttpOnly, Secure, SameSite)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=max_age,
        expires=expires,
        httponly=True,  # Not accessible from JavaScript
        secure=False,  # Set to True in production (HTTPS only)
        samesite="lax",  # CSRF protection
        path="/",
    )

    # Set refresh token cookie if provided
    if refresh_token:
        refresh_expires = datetime.now(timezone.utc) + timedelta(seconds=refresh_max_age)
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=refresh_max_age,
            expires=refresh_expires,
            httponly=True,
            secure=False,  # Set to True in production
            samesite="lax",
            path="/",
        )


def clear_auth_cookies(response: Response) -> None:
    """
    Clear authentication cookies from the response.

    Args:
        response: FastAPI Response object
    """
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        key="refresh_token",
        path="/",
        httponly=True,
        samesite="lax",
    )
