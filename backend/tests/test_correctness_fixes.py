"""正确性修复回归测试（B1 批次）。

覆盖：
- bulk_update 后 SSE 事件确实发布（此前 publish 缺 await，协程被丢弃）
- MCP list_tasks overdue=False 在 SQL 层过滤，分页语义稳定（此前分页后 Python 过滤导致页大小不稳）
"""

import json
from unittest.mock import AsyncMock

import pytest


def parse_sse_text(txt: str) -> dict | None:
    for line in txt.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return None


async def _mcp_call(mcp_client, sid: str, call_id: int, name: str, arguments: dict) -> dict:
    resp = await mcp_client.post(
        "/mcp/",
        headers={**mcp_client.headers, "mcp-session-id": sid},
        json={
            "jsonrpc": "2.0",
            "id": call_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    # SSE 流可能重放先前通知/响应，按 JSON-RPC id 取本次调用对应的响应
    results = []
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            try:
                msg = json.loads(line[6:])
            except ValueError:
                continue
            if msg.get("id") == call_id and "result" in msg:
                results.append(msg)
    return results[-1]


@pytest.mark.asyncio
async def test_bulk_update_publishes_sse_events(auth_client, test_project, monkeypatch):
    """bulk 更新每张任务都应发布一条 SSE 事件（回归：publish 未 await）。"""
    import app.routers.tasks as tasks_router

    # 造 3 张任务
    ids = []
    for name in ("A", "B", "C"):
        resp = await auth_client.post(
            f"/api/projects/{test_project.id}/tasks", json={"name": name}
        )
        assert resp.status_code in (200, 201)
        ids.append(resp.json()["id"])

    publish_mock = AsyncMock()
    monkeypatch.setattr(tasks_router, "publish", publish_mock)

    resp = await auth_client.post(
        "/api/tasks/bulk",
        json={"ids": ids, "data": {"priority": "high"}},
    )
    assert resp.status_code == 204
    assert publish_mock.await_count == len(ids)
    awaited_ids = [call.args[3] for call in publish_mock.await_args_list]
    assert sorted(awaited_ids) == sorted(ids)


@pytest.mark.asyncio
async def test_mcp_list_tasks_overdue_false_stable_pagination(mcp_client):
    """overdue=False 应在 SQL 层过滤：即使页边界两侧混合逾期任务，页大小也恒定。"""
    from datetime import timedelta

    from app.utils.time import today_utc

    today = today_utc()

    # MCP initialize
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

    # 建项目 + 6 张任务（3 逾期 + 3 未逾期，交错创建）
    data = await _mcp_call(mcp_client, sid, 2, "create_project", {"name": "P-ovd"})
    pid = json.loads(data["result"]["content"][0]["text"])["id"]

    for i in range(6):
        overdue = i % 2 == 0
        due = (today - timedelta(days=1)) if overdue else (today + timedelta(days=7))
        await _mcp_call(
            mcp_client, sid, 10 + i,
            "create_task",
            {"project_id": pid, "name": f"task-{i}", "due_date": due.isoformat()},
        )

    # overdue=False + limit=3：应返回满 3 条且全部未逾期
    data = await _mcp_call(
        mcp_client, sid, 20,
        "list_tasks",
        {"project_id": pid, "overdue": False, "limit": 3},
    )
    tasks = [json.loads(c["text"]) for c in data["result"]["content"]]
    assert len(tasks) == 3, f"页大小应恒为 3（修复前分页后过滤会变少）: {tasks}"
    today_iso = today.isoformat()
    assert all(
        t["status"] == "done" or t["due_date"] is None or t["due_date"] >= today_iso
        for t in tasks
    ), "overdue=False 页内不应出现逾期任务"

    # overdue=True：恰好 3 张
    data = await _mcp_call(
        mcp_client, sid, 21,
        "list_tasks",
        {"project_id": pid, "overdue": True},
    )
    tasks = [json.loads(c["text"]) for c in data["result"]["content"]]
    assert len(tasks) == 3
