"""Error response tests for 4xx status codes."""

import os
from datetime import UTC

import pytest

_mcp_disabled = os.environ.get("MCP_ENABLED", "true").lower() == "false"
_requires_mcp = pytest.mark.skipif(_mcp_disabled, reason="MCP_ENABLED=false in this test run")




class Test400Errors:
    """Test 400 Bad Request errors."""

    @pytest.mark.asyncio
    async def test_create_project_invalid_dates(self, auth_client):
        """Test creating project with start_date > end_date returns 400."""
        resp = await auth_client.post(
            "/api/projects",
            json={
                "name": "Test",
                "start_date": "2025-12-31",
                "end_date": "2025-01-01",
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        # Pydantic v2 returns detail as array of {type, loc, msg}
        if isinstance(detail, list):
            detail = detail[0]["msg"] if detail else ""
        assert "开始日期晚于截止日期" in detail

    @pytest.mark.asyncio
    async def test_task_self_dependency(self, auth_client, test_project, test_task):
        """Test adding task dependency on itself returns 400."""
        resp = await auth_client.post(
            f"/api/tasks/{test_task.id}/dependencies",
            json={"depends_on_task_id": test_task.id},
        )
        assert resp.status_code == 400
        assert "任务不能依赖自身" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_duplicate_task_dependency(self, auth_client, test_project, db_session):
        """Test adding duplicate task dependency returns 400."""
        from app.models import Task

        task1 = Task(project_id=test_project.id, name="Task 1", status="todo", progress=0)
        task2 = Task(project_id=test_project.id, name="Task 2", status="todo", progress=0)
        db_session.add_all([task1, task2])
        await db_session.commit()
        await db_session.refresh(task1)
        await db_session.refresh(task2)

        # Add first dependency
        resp = await auth_client.post(
            f"/api/tasks/{task1.id}/dependencies",
            json={"depends_on_task_id": task2.id},
        )
        assert resp.status_code == 204

        # Add duplicate
        resp = await auth_client.post(
            f"/api/tasks/{task1.id}/dependencies",
            json={"depends_on_task_id": task2.id},
        )
        assert resp.status_code == 400
        assert "依赖关系已存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_resolve_non_todo_blocker_log(self, auth_client, test_project):
        """Test resolving non-todo/blocker log returns 400."""
        from app.models import DevLog

        log = DevLog(
            project_id=test_project.id,
            entry_type="progress",
            title="Progress log",
            author="testuser",
        )
        # Need to add via db_session
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            db.add(log)
            await db.commit()
            await db.refresh(log)

        resp = await auth_client.post(f"/api/logs/{log.id}/resolve")
        assert resp.status_code == 400
        assert "仅 todo / blocker 条目可标记完成" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_dev_log_invalid_related_task(self, auth_client, test_project):
        """Test creating dev log with non-existent related task returns 400."""
        resp = await auth_client.post(
            f"/api/projects/{test_project.id}/logs",
            json={"entry_type": "progress", "title": "Test", "related_task_ids": [99999]},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    @_requires_mcp
    async def test_mcp_invalid_project_id(self, mcp_client):
        """Test MCP tool with invalid project_id returns error."""
        sid = await test_mcp_auth_initialize(mcp_client)
        headers = {**mcp_client.headers, "mcp-session-id": sid}

        resp = await mcp_client.post(
            "/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "create_task", "arguments": {"project_id": 99999, "name": "Test"}},
            },
        )
        data = parse_sse_text(resp.text)
        result = (data or {}).get("result") or {}
        assert resp.status_code != 200 or "error" in data or result.get("isError")


class Test401Errors:
    """Test 401 Unauthorized errors."""

    @pytest.mark.asyncio
    async def test_unauthorized_auth_me(self, client):
        """Test /auth/me without token returns 401."""
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthorized_projects_list(self, client):
        """Test /projects without token returns 401."""
        resp = await client.get("/api/projects")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthorized_tasks_list(self, client, test_project):
        """Test /tasks without token returns 401."""
        resp = await client.get(f"/api/projects/{test_project.id}/tasks")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthorized_dev_logs(self, client, test_project):
        """Test /dev-logs without token returns 401."""
        resp = await client.get(f"/api/projects/{test_project.id}/logs")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    @_requires_mcp
    async def test_unauthorized_mcp(self, client):
        """Test MCP without authentication returns 401."""
        resp = await client.post(
            "/mcp/",
            headers={"Accept": "application/json, text/event-stream"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_jwt_token(self, client):
        """Test invalid JWT token returns 401."""
        client.headers.update({"Authorization": "Bearer invalid.token.here"})
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_jwt_token(self, auth_client, test_user):
        """Test expired JWT token returns 401."""
        resp = await auth_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6MTAwMDAwMDAwMH0.invalid"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_api_key_exchange(self, auth_client):
        """Test exchanging invalid API key returns 401."""
        resp = await auth_client.post("/api/keys/exchange", json={"key": "invalid_key"})
        assert resp.status_code == 401
        assert "无效的 API Key" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_revoked_api_key_exchange(self, auth_client, db_session, test_user):
        """Test exchanging revoked API key returns 401."""
        from datetime import datetime

        from app.core.apikey import generate_api_key
        from app.models import ApiKey

        raw, prefix, key_hash = generate_api_key(test_user.id)
        key = ApiKey(
            user_id=test_user.id,
            name="revoked",
            prefix=prefix,
            key_hash=key_hash,
            revoked_at=datetime.now(UTC),
        )
        db_session.add(key)
        await db_session.commit()

        resp = await auth_client.post("/api/keys/exchange", json={"key": raw})
        assert resp.status_code == 401
        assert "无效的 API Key" in resp.json()["detail"]


class Test404Errors:
    """Test 404 Not Found errors."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_project(self, auth_client):
        """Test getting nonexistent project returns 404."""
        resp = await auth_client.get("/api/projects/99999")
        assert resp.status_code == 404
        assert "项目不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_nonexistent_project(self, auth_client):
        """Test updating nonexistent project returns 404."""
        resp = await auth_client.put("/api/projects/99999", json={"name": "New"})
        assert resp.status_code == 404
        assert "项目不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_nonexistent_project(self, auth_client):
        """Test deleting nonexistent project returns 404."""
        resp = await auth_client.delete("/api/projects/99999")
        assert resp.status_code == 404
        assert "项目不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, auth_client, test_project):
        """Test getting nonexistent task returns 404."""
        resp = await auth_client.get("/api/tasks/99999")
        assert resp.status_code == 404
        assert "任务不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_nonexistent_task(self, auth_client, test_project):
        """Test updating nonexistent task returns 404."""
        resp = await auth_client.put("/api/tasks/99999", json={"name": "New"})
        assert resp.status_code == 404
        assert "任务不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_nonexistent_task(self, auth_client, test_project):
        """Test deleting nonexistent task returns 404."""
        resp = await auth_client.delete("/api/tasks/99999")
        assert resp.status_code == 404
        assert "任务不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_dev_log(self, auth_client):
        """Test getting nonexistent dev log returns 404."""
        resp = await auth_client.get("/api/logs/99999")
        assert resp.status_code == 404
        assert "记录不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_nonexistent_dev_log(self, auth_client):
        """Test updating nonexistent dev log returns 404."""
        resp = await auth_client.put("/api/logs/99999", json={"title": "New"})
        assert resp.status_code == 404
        assert "记录不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_nonexistent_dev_log(self, auth_client):
        """Test deleting nonexistent dev log returns 404."""
        resp = await auth_client.delete("/api/logs/99999")
        assert resp.status_code == 404
        assert "记录不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_dev_log(self, auth_client):
        """Test resolving nonexistent dev log returns 404."""
        resp = await auth_client.post("/api/logs/99999/resolve")
        assert resp.status_code == 404
        assert "记录不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, auth_client):
        """Test getting nonexistent session returns 404."""
        resp = await auth_client.post("/api/sessions/99999/end", json={"summary": "End"})
        assert resp.status_code == 404
        assert "会话不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_api_key(self, auth_client):
        """Test revoking nonexistent API key returns 404."""
        resp = await auth_client.delete("/api/keys/99999")
        assert resp.status_code == 404
        assert "API Key 不存在" in resp.json()["detail"]

    @pytest.mark.asyncio
    @_requires_mcp
    async def test_mcp_nonexistent_project(self, mcp_client):
        """Test MCP tool with nonexistent project returns error."""
        sid = await test_mcp_auth_initialize(mcp_client)
        headers = {**mcp_client.headers, "mcp-session-id": sid}

        resp = await mcp_client.post(
            "/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "get_project", "arguments": {"project_id": 99999}},
            },
        )
        data = parse_sse_text(resp.text)
        result = (data or {}).get("result") or {}
        assert resp.status_code != 200 or "error" in data or result.get("isError")
        if "error" in data:
            assert "不存在" in data["error"]["message"]
        else:
            text = (result.get("content") or [{}])[0].get("text", "")
            assert "不存在" in text


class Test422Errors:
    """Test 422 Unprocessable Entity errors."""

    @pytest.mark.asyncio
    async def test_create_project_missing_name(self, auth_client):
        """Test creating project without name returns 422."""
        resp = await auth_client.post("/api/projects", json={"description": "Test"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_task_missing_name(self, auth_client, test_project):
        """Test creating task without name returns 422."""
        resp = await auth_client.post(
            f"/api/projects/{test_project.id}/tasks", json={"description": "Test"}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_task_invalid_status(self, auth_client, test_project):
        """Test creating task with invalid status returns 422."""
        resp = await auth_client.post(
            f"/api/projects/{test_project.id}/tasks",
            json={"name": "Test", "status": "invalid"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_task_invalid_priority(self, auth_client, test_project):
        """Test creating task with invalid priority returns 422."""
        resp = await auth_client.post(
            f"/api/projects/{test_project.id}/tasks",
            json={"name": "Test", "priority": "invalid"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_task_invalid_progress(self, auth_client, test_project):
        """Test creating task with invalid progress returns 422."""
        resp = await auth_client.post(
            f"/api/projects/{test_project.id}/tasks",
            json={"name": "Test", "progress": 150},
        )
        assert resp.status_code == 422

        resp = await auth_client.post(
            f"/api/projects/{test_project.id}/tasks",
            json={"name": "Test", "progress": -10},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_dev_log_invalid_entry_type(self, auth_client, test_project):
        """Test creating dev log with invalid entry_type returns 422."""
        resp = await auth_client.post(
            f"/api/projects/{test_project.id}/logs",
            json={"entry_type": "invalid", "title": "Test"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_dev_log_invalid_status(self, auth_client, test_project):
        """Test creating dev log with invalid status returns 422."""
        resp = await auth_client.post(
            f"/api/projects/{test_project.id}/logs",
            json={"entry_type": "todo", "title": "Test", "status": "invalid"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_dev_log_invalid_severity(self, auth_client, test_project):
        """Test creating dev log with invalid severity returns 422."""
        resp = await auth_client.post(
            f"/api/projects/{test_project.id}/logs",
            json={"entry_type": "difficulty", "title": "Test", "severity": "invalid"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_milestone_missing_name(self, auth_client, test_project):
        """Test creating milestone without name returns 422."""
        resp = await auth_client.post(
            f"/api/projects/{test_project.id}/milestones", json={"due_date": "2025-12-31"}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_create_api_key_missing_name(self, auth_client):
        """Test creating API key without name returns 422."""
        resp = await auth_client.post("/api/keys", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_add_dependency_missing_depends_on(self, auth_client, test_task):
        """Test adding dependency without depends_on_task_id returns 422."""
        resp = await auth_client.post(
            f"/api/tasks/{test_task.id}/dependencies", json={}
        )
        assert resp.status_code == 422
        assert "缺少 depends_on_task_id" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_remove_dependency_missing_depends_on(self, auth_client, test_task):
        """Test removing dependency without depends_on_task_id returns 422."""
        resp = await auth_client.request(
            "DELETE", f"/api/tasks/{test_task.id}/dependencies", json={}
        )
        assert resp.status_code == 422
        assert "缺少 depends_on_task_id" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_bulk_update_empty_ids(self, auth_client):
        """Test bulk update with empty ids returns 422."""
        resp = await auth_client.post(
            "/api/tasks/bulk", json={"ids": [], "data": {"status": "done"}}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_pagination_limit_too_high(self, auth_client):
        """Test pagination with limit > 200 returns 422."""
        resp = await auth_client.get("/api/projects", params={"limit": 201})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_pagination_limit_zero(self, auth_client):
        """Test pagination with limit = 0 returns 422."""
        resp = await auth_client.get("/api/projects", params={"limit": 0})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_pagination_negative_offset(self, auth_client):
        """Test pagination with negative offset returns 422."""
        resp = await auth_client.get("/api/projects", params={"offset": -1})
        assert resp.status_code == 422


def parse_sse_text(txt: str) -> dict | None:
    import json
    for line in txt.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return None


@_requires_mcp
async def test_mcp_auth_initialize(mcp_client):
    """Helper to initialize MCP session."""
    resp = await mcp_client.post(
        "/mcp/",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "t", "version": "1"},
            },
        },
    )
    assert resp.status_code == 200
    return resp.headers.get("mcp-session-id")