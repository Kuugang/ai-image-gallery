import pytest
from httpx import AsyncClient

from app.main import app

BASE_URL = "http://test"


@pytest.mark.asyncio
async def test_signup_success():
    """Test successful user signup"""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        response = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": f"test_signup_{pytest.timestamp}@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["email"] is not None


@pytest.mark.asyncio
async def test_signup_invalid_email():
    """Test signup with invalid email"""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        response = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": "not_an_email",
                "password": "password123",
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_short_password():
    """Test signup with password too short"""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        response = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": "test@example.com",
                "password": "short",
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(test_user_email: str, test_user_password: str):
    """Test successful login"""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_email,
                "password": test_user_password,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user_id"] is not None


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(test_access_token: str):
    """Test getting current user info"""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {test_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] is not None
        assert data["email"] is not None


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Test getting current user with invalid token"""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_success(test_refresh_token: str):
    """Test refreshing access token"""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": test_refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


@pytest.mark.asyncio
async def test_refresh_token_invalid():
    """Test refreshing with invalid refresh token"""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_refresh_token"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_success(test_access_token: str):
    """Test successful logout"""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {test_access_token}"},
        )
        assert response.status_code == 204


@pytest.mark.asyncio
async def test_logout_invalid_token():
    """Test logout with invalid token"""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code in [401, 400]


@pytest.mark.asyncio
async def test_password_reset_request():
    """Test password reset request"""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        response = await client.post(
            "/api/v1/auth/password-reset",
            json={"email": "test@example.com"},
        )
        assert response.status_code == 202
        data = response.json()
        assert "message" in data
