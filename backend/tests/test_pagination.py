"""Pagination tests for list endpoints that support pagination."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.mark.asyncio
async def test_list_dev_logs_pagination(auth_client, db_session, test_project):
    """Test dev logs list pagination with total count."""
    from app.models import DevLog

    # Create multiple dev logs
    for i in range(12):
        log = DevLog(
            project_id=test_project.id,
            entry_type="progress",
            title=f"Log {i}",
            author="testuser",
        )
        db_session.add(log)
    await db_session.commit()

    # Test first page
    resp = await auth_client.get(
        f"/api/projects/{test_project.id}/logs", params={"limit": 5, "offset": 0}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5

    # Test second page
    resp = await auth_client.get(
        f"/api/projects/{test_project.id}/logs", params={"limit": 5, "offset": 5}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5

    # Test third page
    resp = await auth_client.get(
        f"/api/projects/{test_project.id}/logs", params={"limit": 5, "offset": 10}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_dev_logs_pagination_with_filters(auth_client, db_session, test_project):
    """Test dev logs list pagination with entry_type and status filters."""
    from app.models import DevLog

    # Create logs with different types and statuses
    for i in range(4):
        log = DevLog(
            project_id=test_project.id,
            entry_type="progress",
            title=f"Progress {i}",
            author="testuser",
            status="open",
        )
        db_session.add(log)
    for i in range(3):
        log = DevLog(
            project_id=test_project.id,
            entry_type="todo",
            title=f"Todo {i}",
            author="testuser",
            status="open",
        )
        db_session.add(log)
    for i in range(2):
        log = DevLog(
            project_id=test_project.id,
            entry_type="todo",
            title=f"Done Todo {i}",
            author="testuser",
            status="done",
        )
        db_session.add(log)
    await db_session.commit()

    # Filter by entry_type
    resp = await auth_client.get(
        f"/api/projects/{test_project.id}/logs", params={"entry_type": "progress", "limit": 10, "offset": 0}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4
    assert all(l["entry_type"] == "progress" for l in data)

    # Filter by status
    resp = await auth_client.get(
        f"/api/projects/{test_project.id}/logs", params={"status": "done", "limit": 10, "offset": 0}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(l["status"] == "done" for l in data)

    # Combined filter
    resp = await auth_client.get(
        f"/api/projects/{test_project.id}/logs",
        params={"entry_type": "todo", "status": "open", "limit": 10, "offset": 0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert all(l["entry_type"] == "todo" and l["status"] == "open" for l in data)


@pytest.mark.asyncio
async def test_pagination_limit_validation(auth_client):
    """Test pagination limit validation (max 200) on dev logs endpoint."""
    # Limit too high
    resp = await auth_client.get("/api/projects/1/logs", params={"limit": 201, "offset": 0})
    assert resp.status_code == 422

    # Limit zero
    resp = await auth_client.get("/api/projects/1/logs", params={"limit": 0, "offset": 0})
    assert resp.status_code == 422

    # Negative offset
    resp = await auth_client.get("/api/projects/1/logs", params={"limit": 10, "offset": -1})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_pagination_default_values(auth_client, db_session, test_project):
    """Test pagination default values on dev logs endpoint."""
    from app.models import DevLog

    # Create 3 dev logs
    for i in range(3):
        log = DevLog(
            project_id=test_project.id,
            entry_type="progress",
            title=f"Log {i}",
            author="testuser",
        )
        db_session.add(log)
    await db_session.commit()

    # Default limit=50, offset=0
    resp = await auth_client.get(f"/api/projects/{test_project.id}/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3