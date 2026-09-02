"""开发记录（DevLog/DevSession）端到端验证：服务层 + REST API + MCP 工具。

基于 SQLite 内存库，验证：条目 CRUD/类型/severity 约束、会话 start/end、统计、
汇报生成、关联任务越权校验，以及 MCP 的 log_*/get_dev_report/get_project_state 链路。
"""

import json
import os

import pytest

_mcp_disabled = os.environ.get("MCP_ENABLED", "true").lower() == "false"
_requires_mcp = pytest.mark.skipif(_mcp_disabled, reason="MCP_ENABLED=false in this test run")


def parse_sse_text(txt: str) -> dict | None:
    for line in txt.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return None


@pytest.mark.asyncio
async def test_dev_log_service_layer(db_session, test_project, test_task):
    """Test DevLog service layer operations."""
    from app.models import DevLog, DevSession
    from app.schemas.dev_log import DevLogCreate
    from app.services.dev_logs import (
        apply_log_update,
        get_dev_log_stats,
        get_dev_report,
        get_project_state,
        to_dict,
    )

    # 1. Create various entry types
    log = DevLog(
        project_id=test_project.id,
        entry_type="progress",
        title="完成登录模块",
        content="实现 JWT 签发与校验",
        git_ref="abc1234",
        related_task_ids=[test_task.id],
        author="claude",
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    assert log.id is not None
    d = to_dict(log)
    assert d["entry_type"] == "progress"
    assert d["git_ref"] == "abc1234"
    assert d["related_task_ids"] == [test_task.id]

    # 2. Severity validation (Pydantic layer)
    with pytest.raises(ValueError, match="severity 仅可用于"):
        DevLogCreate(entry_type="progress", title="x", severity="high")

    # 3. Todo entry + resolve
    todo = DevLog(project_id=test_project.id, entry_type="todo", title="待办 A", author="claude")
    db_session.add(todo)
    await db_session.commit()
    await db_session.refresh(todo)

    apply_log_update(todo, {"status": "done"})
    assert todo.resolved_at is not None
    await db_session.commit()

    # 4. Session
    s = DevSession(project_id=test_project.id, title="会话1", author="claude")
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    s.ended_at = s.started_at
    await db_session.commit()

    # 5. Statistics
    stats = await get_dev_log_stats(db_session, test_project.id)
    assert stats.total >= 2
    assert stats.type_counts["progress"] >= 1
    assert stats.type_counts["todo"] >= 1

    # 6. Report generation
    report = await get_dev_report(db_session, test_project.id, None, None)
    assert "开发汇报" in report
    assert "完成登录模块" in report

    # 7. Context aggregation
    state = await get_project_state(db_session, test_project.id)
    assert state["project"]["name"] == "Test Project"
    assert len(state["recent_progress"]) >= 1


@pytest.mark.asyncio
async def test_dev_log_rest_api(auth_client, test_project, test_task):
    """Test DevLog REST API endpoints."""
    # Create todo entry (resolvable)
    resp = await auth_client.post(
        f"/api/projects/{test_project.id}/logs",
        json={"entry_type": "todo", "title": "待办 REST"},
    )
    assert resp.status_code == 201
    todo_id = resp.json()["id"]

    # List logs
    resp = await auth_client.get(f"/api/projects/{test_project.id}/logs")
    assert resp.status_code == 200
    assert any(x["id"] == todo_id for x in resp.json())

    # Filter by entry_type
    resp = await auth_client.get(
        f"/api/projects/{test_project.id}/logs", params={"entry_type": "todo"}
    )
    assert resp.status_code == 200
    assert all(x["entry_type"] == "todo" for x in resp.json())

    # Statistics
    resp = await auth_client.get(f"/api/projects/{test_project.id}/logs/stats")
    assert resp.status_code == 200
    assert "type_counts" in resp.json()

    # Update log
    resp = await auth_client.put(
        f"/api/logs/{todo_id}", json={"content": "更新后的内容"}
    )
    assert resp.status_code == 200
    assert resp.json()["content"] == "更新后的内容"

    # Resolve todo
    resp = await auth_client.post(f"/api/logs/{todo_id}/resolve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"

    # Non todo/blocker cannot be resolved
    resp = await auth_client.post(
        f"/api/projects/{test_project.id}/logs",
        json={"entry_type": "decision", "title": "决策 REST"},
    )
    assert resp.status_code == 201
    decision_id = resp.json()["id"]

    resp = await auth_client.post(f"/api/logs/{decision_id}/resolve")
    assert resp.status_code == 400

    # Related task authorization check
    resp = await auth_client.post(
        f"/api/projects/{test_project.id}/logs",
        json={"entry_type": "progress", "title": "x", "related_task_ids": [99999]},
    )
    assert resp.status_code == 400

    # Session start/end/list
    resp = await auth_client.post(
        f"/api/projects/{test_project.id}/sessions", json={"title": "REST 会话"}
    )
    assert resp.status_code == 201
    sess_id = resp.json()["id"]

    resp = await auth_client.post(
        f"/api/sessions/{sess_id}/end", json={"summary": "收口总结"}
    )
    assert resp.status_code == 200
    assert resp.json()["summary"] == "收口总结"

    resp = await auth_client.get(f"/api/projects/{test_project.id}/sessions")
    assert resp.status_code == 200
    assert any(x["id"] == sess_id for x in resp.json())

    # Report
    resp = await auth_client.post(
        f"/api/projects/{test_project.id}/logs/report",
        json={"start": None, "end": None},
    )
    assert resp.status_code == 200
    assert "开发汇报" in resp.json()["text"]

    # Delete
    resp = await auth_client.delete(f"/api/logs/{decision_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
@pytest.mark.skipif(os.environ.get("MCP_ENABLED","true").lower()=="false", reason="no MCP")
async def test_dev_log_mcp_tools(mcp_client, test_project, test_task):
    """Test DevLog MCP tools."""
    # Initialize MCP session
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
    sid = resp.headers.get("mcp-session-id")
    assert sid

    headers = {**mcp_client.headers, "mcp-session-id": sid}

    # List tools
    resp = await mcp_client.post(
        "/mcp/", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    data = parse_sse_text(resp.text)
    names = [t["name"] for t in data["result"]["tools"]]

    expected_tools = [
        "log_progress",
        "log_difficulty",
        "log_todo",
        "log_decision",
        "log_blocker",
        "log_note",
        "start_dev_session",
        "end_dev_session",
        "list_dev_logs",
        "get_dev_log_stats_mcp",
        "get_project_state",
        "get_dev_report",
        "update_dev_log",
        "delete_dev_log",
        "resolve_dev_log",
    ]
    for expect in expected_tools:
        assert expect in names, f"缺少 MCP 工具 {expect}"

    # Session + entry chain
    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "start_dev_session", "arguments": {"project_id": test_project.id, "title": "MCP 会话"}},
        },
    )
    content = parse_sse_text(resp.text)["result"]["content"][0]["text"]
    sid = int(content.split('"id": ')[1].split(",")[0])

    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "log_progress",
                "arguments": {"project_id": test_project.id, "title": "MCP 进展", "git_ref": "abc"},
            },
        },
    )
    assert '"entry_type": "progress"' in parse_sse_text(resp.text)["result"]["content"][0]["text"]

    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "log_difficulty",
                "arguments": {"project_id": test_project.id, "title": "异步坑", "severity": "high"},
            },
        },
    )
    assert '"severity": "high"' in parse_sse_text(resp.text)["result"]["content"][0]["text"]

    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "end_dev_session", "arguments": {"session_id": sid, "summary": "结束"}},
        },
    )
    assert '"ended_at"' in parse_sse_text(resp.text)["result"]["content"][0]["text"]

    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "get_dev_log_stats_mcp", "arguments": {"project_id": test_project.id}},
        },
    )
    assert '"open_difficulties"' in parse_sse_text(resp.text)["result"]["content"][0]["text"]

    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "get_project_state", "arguments": {"project_id": test_project.id}},
        },
    )
    assert "open_todos" in parse_sse_text(resp.text)["result"]["content"][0]["text"]

    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {"name": "get_dev_report", "arguments": {"project_id": test_project.id}},
        },
    )
    assert "开发汇报" in parse_sse_text(resp.text)["result"]["content"][0]["text"]


@pytest.mark.asyncio
async def test_dev_log_enum_validation():
    """Test DevLog enum validation."""
    from app.schemas.dev_log import (
        DEV_LOG_STATUS,
        DEV_LOG_TYPES,
        SEVERITY,
        DevLogCreate,
    )

    # Valid entry types
    for et in DEV_LOG_TYPES:
        log = DevLogCreate(entry_type=et, title="test")
        assert log.entry_type == et

    # Invalid entry type
    with pytest.raises(ValueError, match="entry_type 必须为"):
        DevLogCreate(entry_type="invalid", title="test")

    # Valid status
    for st in DEV_LOG_STATUS:
        log = DevLogCreate(entry_type="todo", title="test", status=st)
        assert log.status == st

    # Invalid status
    with pytest.raises(ValueError, match="status 必须为"):
        DevLogCreate(entry_type="todo", title="test", status="invalid")

    # Valid severity
    for sev in SEVERITY:
        log = DevLogCreate(entry_type="difficulty", title="test", severity=sev)
        assert log.severity == sev

    # Invalid severity
    with pytest.raises(ValueError, match="severity 必须为"):
        DevLogCreate(entry_type="difficulty", title="test", severity="invalid")

    # Severity only for difficulty/blocker
    with pytest.raises(ValueError, match="severity 仅可用于"):
        DevLogCreate(entry_type="progress", title="test", severity="high")

    # Status done only for todo/blocker
    with pytest.raises(ValueError, match="status 仅可用于"):
        DevLogCreate(entry_type="progress", title="test", status="done")

@pytest.mark.asyncio
async def test_list_logs_with_total_envelope(auth_client, test_project, db_session):
    """?with_total=1 返回 {items, total} 信封；total 按筛选条件精确计数。"""
    from app.models import DevLog

    for i in range(7):
        db_session.add(
            DevLog(
                project_id=test_project.id,
                entry_type="note" if i < 3 else "progress",
                title=f"log{i}",
                content="c",
            )
        )
    await db_session.commit()

    # 默认仍是纯列表（向后兼容）
    resp = await auth_client.get(f"/api/projects/{test_project.id}/logs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # 信封：total=7
    resp = await auth_client.get(
        f"/api/projects/{test_project.id}/logs", params={"with_total": "true", "limit": 3}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"items", "total"}
    assert body["total"] == 7
    assert len(body["items"]) == 3

    # 筛选后 total 同步缩小
    resp = await auth_client.get(
        f"/api/projects/{test_project.id}/logs",
        params={"with_total": "true", "entry_type": "note"},
    )
    assert resp.json()["total"] == 3


@pytest.mark.asyncio
async def test_mcp_list_dev_logs_since_timezone_variants(mcp_client):
    """since 参数接受无时区（按 UTC）与 Z 后缀两种形式，不因时区处理崩溃。"""
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
    sid = resp.headers["mcp-session-id"]

    async def call(cid: int, since: str):
        r = await mcp_client.post(
            "/mcp/",
            headers={**mcp_client.headers, "mcp-session-id": sid},
            json={
                "jsonrpc": "2.0",
                "id": cid,
                "method": "tools/call",
                "params": {"name": "list_dev_logs", "arguments": {"project_id": 1, "since": since}},
            },
        )
        return parse_sse_text(r.text)

    # 项目可能不存在（错误返回也算"不崩溃"），关键是无 500/unhandled
    data = await call(2, "2020-01-01T00:00:00")
    assert data is not None
    data = await call(3, "2020-01-01T00:00:00Z")
    assert data is not None
