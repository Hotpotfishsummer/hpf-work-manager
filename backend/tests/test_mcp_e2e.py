"""MCP Server 端到端验证（SSE 流式响应 + Streamable HTTP）。

基于 SQLite 内存库，验证：认证 → initialize → tools/list → 工具调用（create 项目/任务、update 状态）。
"""

import json
import re

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def parse_sse_text(txt: str) -> dict | None:
    for line in txt.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return None


@pytest.mark.asyncio
async def test_mcp_auth_initialize(mcp_client):
    """Test MCP authentication and initialization."""
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
    assert sid, "缺少 mcp-session-id"
    return sid


@pytest.mark.asyncio
async def test_mcp_tools_list(mcp_client):
    """Test MCP tools/list."""
    sid = await test_mcp_auth_initialize(mcp_client)
    headers = {**mcp_client.headers, "mcp-session-id": sid}

    resp = await mcp_client.post(
        "/mcp/", headers=headers, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    data = parse_sse_text(resp.text)
    names = [t["name"] for t in data["result"]["tools"]]

    assert "update_task" in names
    assert "list_projects" in names
    assert "create_project" in names
    assert "create_task" in names


@pytest.mark.asyncio
async def test_mcp_create_project(mcp_client):
    """Test MCP create_project tool."""
    sid = await test_mcp_auth_initialize(mcp_client)
    headers = {**mcp_client.headers, "mcp-session-id": sid}

    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "create_project", "arguments": {"name": "P1"}},
        },
    )
    content = parse_sse_text(resp.text)["result"]["content"][0]["text"]
    assert '"name": "P1"' in content


@pytest.mark.asyncio
async def test_mcp_create_task(mcp_client):
    """Test MCP create_task tool."""
    sid = await test_mcp_auth_initialize(mcp_client)
    headers = {**mcp_client.headers, "mcp-session-id": sid}

    # First create a project
    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "create_project", "arguments": {"name": "P1"}},
        },
    )

    # Create task
    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "create_task", "arguments": {"project_id": 1, "name": "T1", "status": "todo"}},
        },
    )
    content = parse_sse_text(resp.text)["result"]["content"][0]["text"]
    tid = int(re.search(r'"id": (\d+)', content).group(1))
    assert tid > 0
    return tid


@pytest.mark.asyncio
async def test_mcp_update_task_status(mcp_client):
    """Test MCP update_task tool with status transition."""
    sid = await test_mcp_auth_initialize(mcp_client)
    headers = {**mcp_client.headers, "mcp-session-id": sid}

    # Create project and task
    await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "create_project", "arguments": {"name": "P1"}},
        },
    )
    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "create_task", "arguments": {"project_id": 1, "name": "T1", "status": "todo"}},
        },
    )
    tid = int(re.search(r'"id": (\d+)', parse_sse_text(resp.text)["result"]["content"][0]["text"]).group(1))

    # Update task to done
    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "update_task", "arguments": {"task_id": tid, "status": "done"}},
        },
    )
    content = parse_sse_text(resp.text)["result"]["content"][0]["text"]
    assert '"progress": 100' in content
    assert '"status": "done"' in content


@pytest.mark.asyncio
async def test_mcp_unauthorized_access(client):
    """Test that unauthenticated MCP access is rejected."""
    resp = await client.post(
        "/mcp/",
        headers={"Accept": "application/json, text/event-stream"},
        json={"jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": {}},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_mcp_invalid_tool(mcp_client):
    """Test MCP invalid tool call."""
    sid = await test_mcp_auth_initialize(mcp_client)
    headers = {**mcp_client.headers, "mcp-session-id": sid}

    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        },
    )
    # Should return error in JSON-RPC response
    data = parse_sse_text(resp.text)
    result = (data or {}).get("result") or {}
    assert resp.status_code != 200 or "error" in data or result.get("isError")


@pytest.mark.asyncio
async def test_mcp_list_projects(mcp_client, test_project):
    """Test MCP list_projects tool."""
    sid = await test_mcp_auth_initialize(mcp_client)
    headers = {**mcp_client.headers, "mcp-session-id": sid}

    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "list_projects", "arguments": {}}},
    )
    data = parse_sse_text(resp.text)
    projects = data["result"]["content"][0]["text"]
    assert test_project.name in projects


@pytest.mark.asyncio
async def test_mcp_list_tasks(mcp_client, test_project, test_task):
    """Test MCP list_tasks tool."""
    sid = await test_mcp_auth_initialize(mcp_client)
    headers = {**mcp_client.headers, "mcp-session-id": sid}

    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {"name": "list_tasks", "arguments": {"project_id": test_project.id}},
        },
    )
    data = parse_sse_text(resp.text)
    tasks = data["result"]["content"][0]["text"]
    assert test_task.name in tasks


@pytest.mark.asyncio
async def test_mcp_task_status_filter(mcp_client, test_project):
    """Test MCP list_tasks with status filter."""
    from app.models import Task

    # Create tasks with different statuses
    for status in ["todo", "in_progress", "done"]:
        task = Task(project_id=test_project.id, name=f"Task {status}", status=status, progress=0)
        if status == "done":
            task.progress = 100
        test_project.__dict__["db"].add(task) if hasattr(test_project, "db") else None

    # Use the test database directly
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        for status in ["todo", "in_progress", "done"]:
            task = Task(project_id=test_project.id, name=f"Task {status}", status=status, progress=0)
            if status == "done":
                task.progress = 100
            db.add(task)
        await db.commit()

    sid = await test_mcp_auth_initialize(mcp_client)
    headers = {**mcp_client.headers, "mcp-session-id": sid}

    # Filter by status
    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {"name": "list_tasks", "arguments": {"project_id": test_project.id, "status": "done"}},
        },
    )
    data = parse_sse_text(resp.text)
    tasks = data["result"]["content"][0]["text"]
    assert "Task done" in tasks
    assert "Task todo" not in tasks

@pytest.mark.asyncio
async def test_mcp_list_task_dependencies(mcp_client, test_project, test_task):
    """Test MCP list_task_dependencies tool (P2-1 补齐)."""
    from app.database import AsyncSessionLocal
    from app.models import Task, TaskDependency

    async with AsyncSessionLocal() as db:
        dep = Task(project_id=test_project.id, name="前置任务", status="todo", progress=0)
        db.add(dep)
        await db.flush()
        dep_id = dep.id
        db.add(TaskDependency(task_id=test_task.id, depends_on_task_id=dep_id))
        await db.commit()

    sid = await test_mcp_auth_initialize(mcp_client)
    headers = {**mcp_client.headers, "mcp-session-id": sid}

    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 30,
            "method": "tools/call",
            "params": {"name": "list_task_dependencies", "arguments": {"task_id": test_task.id}},
        },
    )
    data = parse_sse_text(resp.text)
    assert resp.status_code == 200
    result = data["result"]
    assert result.get("isError") is not True
    content = result["content"][0]["text"]
    assert "前置任务" in content
    assert str(dep_id) in content


@pytest.mark.asyncio
async def test_mcp_list_tools_pagination_and_search(mcp_client, test_project):
    """P2-2: MCP list 工具 offset/limit 分页与 search 模糊搜索。"""
    from app.database import AsyncSessionLocal
    from app.models import Task

    async with AsyncSessionLocal() as db:
        for i in range(5):
            db.add(Task(project_id=test_project.id, name=f"分页任务{i}", status="todo", progress=0))
        db.add(Task(project_id=test_project.id, name="特殊搜索目标", description="关键词xyz", status="todo", progress=0))
        await db.commit()

    sid = await test_mcp_auth_initialize(mcp_client)
    headers = {**mcp_client.headers, "mcp-session-id": sid}

    async def call(name, arguments):
        resp = await mcp_client.post(
            "/mcp/",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 40,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
        )
        assert resp.status_code == 200
        data = parse_sse_text(resp.text)
        assert data["result"].get("isError") is not True, data
        # list 返回值为多个 content 块（每项一块），合并后再断言
        return "".join(b.get("text", "") for b in data["result"]["content"])

    # 分页：limit=2, offset=0 vs offset=2 不重叠
    page0 = await call("list_tasks", {"project_id": test_project.id, "limit": 2, "offset": 0})
    page1 = await call("list_tasks", {"project_id": test_project.id, "limit": 2, "offset": 2})
    names0 = re.findall(r'"name": "([^"]+)"', page0)
    names1 = re.findall(r'"name": "([^"]+)"', page1)
    assert len(names0) == 2 and len(names1) == 2
    assert not set(names0) & set(names1)

    # 搜索命中名称与描述
    searched = await call("list_tasks", {"project_id": test_project.id, "search": "xyz"})
    assert "特殊搜索目标" in searched
    searched2 = await call("list_tasks", {"project_id": test_project.id, "search": "分页任务"})
    assert "分页任务0" in searched2
