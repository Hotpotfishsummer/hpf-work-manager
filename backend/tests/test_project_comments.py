"""项目评论（工作方向指示）+ 任务分类端到端测试。

覆盖：项目评论 CRUD、已处理标记、跨用户隔离、MCP 评论工具（任务/项目双锚点）、
get_project_state 带 directions、任务分类校验与 MCP 贯通。
"""

import json

import pytest

pytestmark = pytest.mark.asyncio


def _sse_json(txt: str) -> dict | None:
    for line in txt.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return None


# ---------- REST ----------


async def test_project_comment_lifecycle(auth_client, test_project):
    base = f"/api/projects/{test_project.id}/comments"

    # 空列表
    r = await auth_client.get(base)
    assert r.status_code == 200 and r.json() == []

    # 创建
    r = await auth_client.post(base, json={"content": "  下一步优先做备份恢复演练  "})
    assert r.status_code == 201
    c = r.json()
    assert c["content"] == "下一步优先做备份恢复演练"  # 两端空白被裁掉
    assert c["project_id"] == test_project.id and c["task_id"] is None
    assert c["is_direction"] is True and c["resolved"] is False

    # 列表
    r = await auth_client.get(base)
    assert [x["id"] for x in r.json()] == [c["id"]]

    # 标记已处理 → 默认列表不再返回，include_resolved 仍可见
    r = await auth_client.post(f"/api/comments/{c['id']}/resolve")
    assert r.status_code == 200 and r.json()["resolved"] is True
    assert (await auth_client.get(base)).json() == []
    r = await auth_client.get(base, params={"include_resolved": True})
    assert len(r.json()) == 1 and r.json()[0]["resolved"] is True

    # 撤销已处理
    r = await auth_client.post(
        f"/api/comments/{c['id']}/resolve", json={"resolved": False}
    )
    assert r.status_code == 200 and r.json()["resolved"] is False
    assert len((await auth_client.get(base)).json()) == 1

    # 概览
    r = await auth_client.get("/api/comments/project-summary")
    assert r.status_code == 200
    row = next(x for x in r.json() if x["project_id"] == test_project.id)
    assert row["open_count"] == 1 and row["total_count"] == 1
    assert "备份恢复演练" in row["latest"]["content"]

    # 删除
    r = await auth_client.delete(f"/api/comments/{c['id']}")
    assert r.status_code == 204
    assert (await auth_client.get(base)).json() == []


async def test_project_comment_validation(auth_client, test_project):
    base = f"/api/projects/{test_project.id}/comments"
    assert (
        await auth_client.post(base, json={"content": "   "})
    ).status_code == 422
    assert (
        await auth_client.post(base, json={"content": "x" * 2001})
    ).status_code == 422


async def test_project_comment_isolation(other_auth_client, test_project, db_session):
    # 他人项目：读、写、概览都看不到
    base = f"/api/projects/{test_project.id}/comments"
    assert (await other_auth_client.get(base)).status_code == 404
    assert (
        await other_auth_client.post(base, json={"content": "越权"})
    ).status_code == 404
    assert (
        await other_auth_client.post("/api/comments/999999/resolve")
    ).status_code == 404
    r = await other_auth_client.get("/api/comments/project-summary")
    assert all(x["project_id"] != test_project.id for x in r.json())


async def test_task_comment_cannot_resolve(auth_client, test_task):
    r = await auth_client.post(
        f"/api/tasks/{test_task.id}/comments", json={"content": "任务评论"}
    )
    cid = r.json()["id"]
    r = await auth_client.post(f"/api/comments/{cid}/resolve")
    assert r.status_code == 400


# ---------- MCP ----------


async def _open_session(mcp_client) -> str:
    """初始化一次 MCP 会话，返回 session id（在响应头里，不在正文）。"""
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
    return resp.headers["mcp-session-id"]


async def _mcp_call(mcp_client, headers, name, arguments, rid):
    resp = await mcp_client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": rid,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    assert resp.status_code == 200
    data = _sse_json(resp.text)
    return data["result"]


async def test_mcp_project_comments_and_state(mcp_client, test_project):
    """项目指示：add → state 能读到 → list 过滤已处理 → resolve 后不再下发。"""
    headers = {**mcp_client.headers, "mcp-session-id": await _open_session(mcp_client)}

    async def call(name, args, rid):
        result = await _mcp_call(mcp_client, headers, name, args, rid)
        assert result.get("isError") is not True, result
        # 优先用结构化返回：列表型结果会被拆成多个文本块，拼文本再猜容易错
        if result.get("structuredContent") and "result" in result["structuredContent"]:
            return result["structuredContent"]["result"]
        return json.loads("".join(b["text"] for b in result["content"]))

    pid = test_project.id
    r = await call(
        "add_comment", {"project_id": pid, "content": "方向A：先补测试"}, rid=10
    )
    assert r["comment"]["project_id"] == pid and r["resolved_ids"] == []
    id_a = r["comment"]["id"]
    r = await call(
        "add_comment", {"project_id": pid, "content": "方向B：再动迁移"}, rid=11
    )
    id_b = r["comment"]["id"]

    # get_project_state 必须带上未处理指示，且按时间顺序
    state = await call("get_project_state", {"project_id": pid}, rid=12)
    assert [d["content"] for d in state["directions"]] == [
        "方向A：先补测试",
        "方向B：再动迁移",
    ]

    # list_projects / get_project 带未处理数
    projects = await call("list_projects", {}, rid=13)
    assert next(p for p in projects if p["id"] == pid)["open_directions"] == 2

    # 只结单不写评论；旧指示不再下发
    r = await call(
        "add_comment", {"project_id": pid, "resolve_ids": [id_a]}, rid=14
    )
    assert r["comment"] is None and r["resolved_ids"] == [id_a]
    state = await call("get_project_state", {"project_id": pid}, rid=15)
    assert [d["id"] for d in state["directions"]] == [id_b]

    # list_comments：默认只看未处理，include_resolved 看全量
    assert len(await call("list_comments", {"project_id": pid}, rid=16)) == 1
    assert (
        len(
            await call(
                "list_comments",
                {"project_id": pid, "include_resolved": True},
                rid=17,
            )
        )
        == 2
    )


async def test_mcp_comment_tool_validation(mcp_client, test_project, test_task):
    headers = {**mcp_client.headers, "mcp-session-id": await _open_session(mcp_client)}

    async def call(name, args, rid):
        return await _mcp_call(mcp_client, headers, name, args, rid)

    # 锚点二选一
    for args in ({}, {"task_id": test_task.id, "project_id": test_project.id}):
        r = await call("add_comment", {**args, "content": "x"}, rid=20)
        assert r["isError"] is True
    # 内容为空且无 resolve_ids
    r = await call("add_comment", {"project_id": test_project.id}, rid=21)
    assert r["isError"] is True
    # 任务评论仍然可用（向后兼容）
    r = await call("add_comment", {"task_id": test_task.id, "content": "任务评论"}, rid=22)
    assert r["isError"] is not True
    body = json.loads(r["content"][0]["text"])
    assert body["comment"]["task_id"] == test_task.id
    # 任务评论不能被标记已处理
    r = await call(
        "add_comment",
        {"project_id": test_project.id, "resolve_ids": [body["comment"]["id"]]},
        rid=23,
    )
    assert r["isError"] is True


# ---------- 任务分类 ----------


async def test_task_category(auth_client, test_project):
    pid = test_project.id
    r = await auth_client.post(
        f"/api/projects/{pid}/tasks",
        json={"name": "补测试", "category": "testing"},
    )
    assert r.status_code == 201 and r.json()["category"] == "testing"

    tid = r.json()["id"]
    r = await auth_client.put(f"/api/tasks/{tid}", json={"category": "devops"})
    assert r.status_code == 200 and r.json()["category"] == "devops"

    # 显式置空 = 改回未分类
    r = await auth_client.put(f"/api/tasks/{tid}", json={"category": None})
    assert r.status_code == 200 and r.json()["category"] is None

    # 非法值
    r = await auth_client.put(f"/api/tasks/{tid}", json={"category": "whatever"})
    assert r.status_code == 422
    r = await auth_client.post(
        f"/api/projects/{pid}/tasks", json={"name": "x", "category": "nope"}
    )
    assert r.status_code == 422


async def test_migration_category_backfill_keyword_order():
    """迁移里的关键词回填按固定优先级匹配，全部不中则保持未分类。"""
    from importlib import util

    path = "alembic/versions/0007_project_comments_category.py"
    spec = util.spec_from_file_location("m0007", path)
    m = util.module_from_spec(spec)
    spec.loader.exec_module(m)

    sql = m._backfill_sql().lower()
    order = [sql.index(f"then '{c}'") for c in ("testing", "docs", "bugfix", "devops", "refactor", "feature")]
    assert order == sorted(order)
    assert "else null" in sql
