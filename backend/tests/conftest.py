"""Shared pytest fixtures for backend tests."""

import os
import sys
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("MCP_ALLOWED_HOSTS", "testserver,localhost")
# 测试环境自洽：无论是否存在 .env，pytest 都能以 test 环境启动
# （environment 默认 production 会因默认 SECRET_KEY 触发 fail-fast）
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-0123456789abcdef0123456789abcdef")


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create SQLite in-memory test engine."""
    from app.database import Base

    # Import all models to register their tables

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine):
    """Create a database session for testing."""
    from app.database import AsyncSession

    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def mcp_session_manager():
    """Start MCP session manager for the test session."""
    from app.config import settings
    from app.mcp_server import get_session_manager

    if not settings.mcp_enabled:
        yield None
        return

    _mcp_session_manager = get_session_manager()
    mcp_cm = _mcp_session_manager.run()
    await mcp_cm.__aenter__()
    yield _mcp_session_manager


@pytest_asyncio.fixture(scope="function")
async def client(test_engine, mcp_session_manager):
    """Create AsyncClient for testing FastAPI app."""
    import app.database as database
    import app.mcp_auth as mcp_auth
    import app.mcp_server as mcp_server
    import app.routers.keys as keys_router
    from app.database import AsyncSession
    from app.deps import get_db
    from app.main import app
    from app.routers import dev_logs, events, keys, projects, tasks

    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Override the global AsyncSessionLocal for all modules
    database.AsyncSessionLocal = async_session
    mcp_auth.AsyncSessionLocal = async_session
    mcp_server.AsyncSessionLocal = async_session
    keys_router.AsyncSessionLocal = async_session
    events.AsyncSessionLocal = async_session

    async def get_db_override():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = get_db_override
    projects.get_db = get_db_override
    tasks.get_db = get_db_override
    keys.get_db = get_db_override
    events.get_db = get_db_override
    dev_logs.get_db = get_db_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_client(client, test_user):
    """Create authenticated client with registered user."""
    from app.core.security import create_access_token

    token = create_access_token(test_user.username, test_user.id)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session):
    """Create a test user in the database."""
    from app.core.security import hash_password
    from app.models import User

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("testpass123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def other_user(db_session):
    """第二个用户（跨用户隔离测试用）。"""
    from app.core.security import hash_password
    from app.models import User

    user = User(
        username="otheruser",
        email="other@example.com",
        hashed_password=hash_password("otherpass123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def other_auth_client(client, other_user):
    """以 other_user 身份访问的独立客户端（与 auth_client 同一 app，共享依赖覆盖）。"""
    from httpx import ASGITransport, AsyncClient

    from app.core.security import create_access_token
    from app.main import app

    token = create_access_token(other_user.username, other_user.id)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def test_project(db_session, test_user):
    """Create a test project in the database."""
    from app.models import Project

    project = Project(owner_id=test_user.id, name="Test Project")
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture(scope="function")
async def test_task(db_session, test_project):
    """Create a test task in the database."""
    from app.models import Task

    task = Task(project_id=test_project.id, name="Test Task", status="todo", progress=0)
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture(scope="function")
async def api_key(db_session, test_user):
    """Create an API key for MCP testing."""
    from app.core.apikey import generate_api_key
    from app.models import ApiKey

    raw, prefix, key_hash = generate_api_key(test_user.id)
    key = ApiKey(user_id=test_user.id, name="test-key", prefix=prefix, key_hash=key_hash)
    db_session.add(key)
    await db_session.commit()
    await db_session.refresh(key)
    return raw, key


@pytest_asyncio.fixture(scope="function")
async def mcp_client(client, api_key):
    """Create client with MCP API key authentication."""
    raw, _ = api_key
    client.headers.update(
        {"Authorization": f"Bearer {raw}", "Accept": "application/json, text/event-stream"}
    )
    return client