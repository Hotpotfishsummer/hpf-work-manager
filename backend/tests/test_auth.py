"""Auth endpoints tests: register, login, me."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_register_success(client):
    """Test successful user registration."""
    resp = await client.post(
        "/api/auth/register",
        json={"username": "newuser", "email": "new@example.com", "password": "password123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["username"] == "newuser"
    assert data["user"]["email"] == "new@example.com"
    assert "id" in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_username(client, test_user):
    """Test registration with duplicate username fails."""
    resp = await client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "different@example.com", "password": "password123"},
    )
    assert resp.status_code == 400
    assert "用户名或邮箱已被注册" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client, test_user):
    """Test registration with duplicate email fails."""
    resp = await client.post(
        "/api/auth/register",
        json={"username": "different", "email": "test@example.com", "password": "password123"},
    )
    assert resp.status_code == 400
    assert "用户名或邮箱已被注册" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_invalid_data(client):
    """Test registration with invalid data fails."""
    # Missing username
    resp = await client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert resp.status_code == 422

    # Missing email
    resp = await client.post(
        "/api/auth/register",
        json={"username": "testuser", "password": "password123"},
    )
    assert resp.status_code == 422

    # Missing password
    resp = await client.post(
        "/api/auth/register",
        json={"username": "testuser", "email": "test@example.com"},
    )
    assert resp.status_code == 422

    # Empty username
    resp = await client.post(
        "/api/auth/register",
        json={"username": "", "email": "test@example.com", "password": "password123"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client, test_user):
    """Test successful login."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["username"] == "testuser"


@pytest.mark.asyncio
async def test_login_wrong_password(client, test_user):
    """Test login with wrong password fails."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    assert "用户名或密码错误" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    """Test login with nonexistent user fails."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "nonexistent", "password": "password123"},
    )
    assert resp.status_code == 401
    assert "用户名或密码错误" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_invalid_data(client):
    """Test login with invalid data fails."""
    # Missing username
    resp = await client.post("/api/auth/login", json={"password": "password123"})
    assert resp.status_code == 422

    # Missing password
    resp = await client.post("/api/auth/login", json={"username": "testuser"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_me_endpoint(auth_client, test_user):
    """Test /auth/me endpoint with valid token."""
    resp = await auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_me_endpoint_unauthorized(client):
    """Test /auth/me endpoint without token fails."""
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint_invalid_token(client):
    """Test /auth/me endpoint with invalid token fails."""
    client.headers.update({"Authorization": "Bearer invalid_token"})
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_token_format(client, test_user):
    """Test that token is JWT format (three parts separated by dots)."""
    resp = await client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    parts = token.split(".")
    assert len(parts) == 3  # JWT has 3 parts: header.payload.signature