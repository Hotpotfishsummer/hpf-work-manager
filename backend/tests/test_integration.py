"""端到端集成验证：API Key 认证、任务状态机、SSE 事件、MCP（基于 SQLite）。

在不依赖 Docker/Postgres 的环境下，用 aiosqlite 覆盖 DB 层验证核心链路。
"""

import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_api_key_generation_and_validation():
    """Test API key generation and validation."""
    from app.core.apikey import generate_api_key, validate_api_key, API_KEY_PREFIX

    raw, prefix, key_hash = generate_api_key(1)
    assert validate_api_key(raw) == key_hash
    assert validate_api_key("bad") is None
    assert raw.startswith(f"{API_KEY_PREFIX}_")
    assert len(prefix) == 6  # 3 bytes = 6 hex chars


@pytest.mark.asyncio
async def test_user_creation_and_auth(db_session):
    """Test user creation and password hashing."""
    from app.core.security import hash_password, verify_password
    from app.models import User

    user = User(
        username="alice",
        email="a@b.co",
        hashed_password=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert verify_password("password123", user.hashed_password)
    assert not verify_password("wrong", user.hashed_password)


@pytest.mark.asyncio
async def test_project_creation(db_session, test_user):
    """Test project creation."""
    from app.models import Project

    proj = Project(owner_id=test_user.id, name="P1")
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)

    assert proj.id is not None
    assert proj.name == "P1"
    assert proj.owner_id == test_user.id


@pytest.mark.asyncio
async def test_task_state_machine(db_session, test_project):
    """Test task state machine: done -> progress=100, completed_at."""
    from app.models import Task
    from app.services.tasks import apply_task_update
    from app.utils.time import utcnow

    task = Task(project_id=test_project.id, name="T1", status="todo", progress=0)
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # Transition to done
    apply_task_update(task, {"status": "done"})
    assert task.progress == 100
    assert task.completed_at is not None

    # Transition away from done
    apply_task_update(task, {"status": "in_progress"})
    assert task.completed_at is None
    await db_session.commit()


@pytest.mark.asyncio
async def test_sse_event_publish_subscribe(db_session, test_project):
    """Test SSE event publish/subscribe."""
    from app.core.events import publish, subscribe
    from app.models import Task
    from app.services.tasks import apply_task_update

    task = Task(project_id=test_project.id, name="T1", status="todo", progress=0)
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    q = asyncio.Queue(maxsize=10)
    await subscribe(test_project.id, q)
    await publish(test_project.id, "updated", "task", task.id)

    msg = await asyncio.wait_for(q.get(), timeout=2)
    data = json.loads(msg)
    assert data["entity"] == "task"
    assert data["project_id"] == test_project.id
    assert data["entity_id"] == task.id


@pytest.mark.asyncio
async def test_api_key_auth_flow(client, test_user, db_session):
    """Test API key creation and exchange for JWT."""
    from app.core.apikey import generate_api_key
    from app.models import ApiKey

    # Create API key via REST
    raw, prefix, key_hash = generate_api_key(test_user.id)
    key = ApiKey(user_id=test_user.id, name="claude", prefix=prefix, key_hash=key_hash)
    db_session.add(key)
    await db_session.commit()

    # Exchange API key for JWT
    resp = await client.post("/api/keys/exchange", json={"key": raw})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_invalid_api_key_rejected(client):
    """Test that invalid API key is rejected."""
    resp = await client.post("/api/keys/exchange", json={"key": "invalid_key"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_jwt_auth_me_endpoint(auth_client):
    """Test /auth/me endpoint with valid JWT."""
    resp = await auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"


@pytest.mark.asyncio
async def test_unauthorized_access_rejected(client):
    """Test that unauthenticated requests are rejected."""
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401