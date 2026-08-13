"""开发记录（DevLog/DevSession）端到端验证：服务层 + REST API + MCP 工具。

基于 SQLite 内存库，验证：条目 CRUD/类型/severity 约束、会话 start/end、统计、
汇报生成、关联任务越权校验，以及 MCP 的 log_*/get_dev_report/get_project_state 链路。
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def parse_sse_text(txt: str) -> dict | None:
    for line in txt.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return None


async def main():
    os.environ.setdefault("MCP_ALLOWED_HOSTS", "testserver,localhost")

    import app.database as database
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.database import Base

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    database.engine = test_engine
    database.AsyncSessionLocal = async_sessionmaker(
        test_engine, class_=database.AsyncSession, expire_on_commit=False
    )
    from app.database import AsyncSessionLocal

    async def get_db_override():
        async with AsyncSessionLocal() as session:
            yield session

    import app.deps as deps
    deps.get_db = get_db_override
    for mod in ["projects", "tasks", "keys", "events", "dev_logs"]:
        import importlib

        m = importlib.import_module(f"app.routers.{mod}")
        m.get_db = get_db_override

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.models import ApiKey, Project, Task, User
    from app.core.apikey import generate_api_key
    from app.core.security import hash_password

    async with AsyncSessionLocal() as db:
        u = User(username="alice", email="a@b.c", hashed_password=hash_password("pw123456"))
        db.add(u)
        await db.commit()
        await db.refresh(u)
        raw, prefix, h = generate_api_key(u.id)
        db.add(ApiKey(user_id=u.id, name="claude", prefix=prefix, key_hash=h))
        proj = Project(owner_id=u.id, name="P1")
        db.add(proj)
        await db.commit()
        await db.refresh(proj)
        task = Task(project_id=proj.id, name="T1")
        db.add(task)
        await db.commit()
        await db.refresh(task)
        project_id, task_id = proj.id, task.id

    # ---- 服务层验证 ----
    from app.services.dev_logs import (
        apply_log_update,
        get_dev_log_stats,
        get_dev_report,
        get_project_state,
        to_dict,
    )
    from app.models import DevLog, DevSession
    from app.schemas.dev_log import DevLogCreate

    async with AsyncSessionLocal() as db:
        # 1. 创建各类型条目
        log = DevLog(
            project_id=project_id,
            entry_type="progress",
            title="完成登录模块",
            content="实现 JWT 签发与校验",
            git_ref="abc1234",
            related_task_ids=[task_id],
            author="claude",
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        assert log.id is not None
        d = to_dict(log)
        assert d["entry_type"] == "progress" and d["git_ref"] == "abc1234"
        assert d["related_task_ids"] == [task_id]

        # 2. severity 校验（Pydantic 层）
        try:
            DevLogCreate(entry_type="progress", title="x", severity="high")
            raise AssertionError("severity 不应允许用于 progress")
        except ValueError:
            pass
        # 3. todo 条目 + resolve
        todo = DevLog(project_id=project_id, entry_type="todo", title="待办 A", author="claude")
        db.add(todo)
        await db.commit()
        await db.refresh(todo)
        apply_log_update(todo, {"status": "done"})
        assert todo.resolved_at is not None
        await db.commit()

        # 4. 会话
        s = DevSession(project_id=project_id, title="会话1", author="claude")
        db.add(s)
        await db.commit()
        await db.refresh(s)
        sid = s.id
        s.ended_at = s.started_at  # 结束
        await db.commit()

        # 5. 统计
        stats = await get_dev_log_stats(db, project_id)
        assert stats.total >= 2
        assert stats.type_counts["progress"] >= 1
        assert stats.type_counts["todo"] >= 1

        # 6. 汇报生成
        report = await get_dev_report(db, project_id, None, None)
        assert "开发汇报" in report and "完成登录模块" in report

        # 7. 上下文聚合
        state = await get_project_state(db, project_id)
        assert state["project"]["name"] == "P1"
        assert len(state["recent_progress"]) >= 1

    # ---- REST API + MCP 验证 ----
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import create_access_token

    with TestClient(app) as c:
        jwt = create_access_token("alice")
        H = {"Authorization": f"Bearer {jwt}"}
        # 创建 todo 条目（可 resolve）
        r = c.post(
            f"/api/projects/{project_id}/logs",
            headers=H,
            json={"entry_type": "todo", "title": "待办 REST"},
        )
        assert r.status_code == 201, r.text
        todo_id = r.json()["id"]
        # 列表
        r = c.get(f"/api/projects/{project_id}/logs", headers=H)
        assert r.status_code == 200 and any(x["id"] == todo_id for x in r.json())
        # 过滤
        r = c.get(f"/api/projects/{project_id}/logs", headers=H, params={"entry_type": "todo"})
        assert all(x["entry_type"] == "todo" for x in r.json())
        # 统计
        r = c.get(f"/api/projects/{project_id}/logs/stats", headers=H)
        assert r.status_code == 200 and "type_counts" in r.json()
        # 更新 + resolve
        r = c.put(f"/api/logs/{todo_id}", headers=H, json={"content": "更新后的内容"})
        assert r.status_code == 200 and r.json()["content"] == "更新后的内容"
        r = c.post(f"/api/logs/{todo_id}/resolve", headers=H)
        assert r.status_code == 200 and r.json()["status"] == "done"
        # 非 todo/blocker 不可 resolve
        r = c.post(
            f"/api/projects/{project_id}/logs",
            headers=H,
            json={"entry_type": "decision", "title": "决策 REST"},
        )
        decision_id = r.json()["id"]
        r = c.post(f"/api/logs/{decision_id}/resolve", headers=H)
        assert r.status_code == 400, r.text
        # 关联任务越权校验
        r = c.post(
            f"/api/projects/{project_id}/logs",
            headers=H,
            json={"entry_type": "progress", "title": "x", "related_task_ids": [99999]},
        )
        assert r.status_code == 400, r.text
        # 会话 start/end/list
        r = c.post(f"/api/projects/{project_id}/sessions", headers=H, json={"title": "REST 会话"})
        assert r.status_code == 201, r.text
        sess_id = r.json()["id"]
        r = c.post(f"/api/sessions/{sess_id}/end", headers=H, json={"summary": "收口总结"})
        assert r.status_code == 200 and r.json()["summary"] == "收口总结"
        r = c.get(f"/api/projects/{project_id}/sessions", headers=H)
        assert any(x["id"] == sess_id for x in r.json())
        # 汇报
        r = c.post(
            f"/api/projects/{project_id}/logs/report", headers=H, json={"start": None, "end": None}
        )
        assert r.status_code == 200 and "开发汇报" in r.json()["text"]
        # 删除
        r = c.delete(f"/api/logs/{decision_id}", headers=H)
        assert r.status_code == 204

        # ---- MCP 工具验证 ----
        HDR = {"Authorization": f"Bearer {raw}", "Accept": "application/json, text/event-stream"}
        r = c.post(
            "/mcp/",
            headers=HDR,
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                             "clientInfo": {"name": "t", "version": "1"}}},
        )
        assert r.status_code == 200
        SHDR = {**HDR, "mcp-session-id": r.headers.get("mcp-session-id")}

        r = c.post("/mcp/", headers=SHDR, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        names = [t["name"] for t in parse_sse_text(r.text)["result"]["tools"]]
        for expect in ["log_progress", "log_difficulty", "log_todo", "log_decision",
                       "log_blocker", "log_note", "start_dev_session", "end_dev_session",
                       "list_dev_logs", "get_dev_log_stats_mcp", "get_project_state",
                       "get_dev_report", "update_dev_log", "delete_dev_log", "resolve_dev_log"]:
            assert expect in names, f"缺少 MCP 工具 {expect}"

        # 会话 + 条目链路
        r = c.post("/mcp/", headers=SHDR, json={"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                                "params": {"name": "start_dev_session",
                                                           "arguments": {"project_id": project_id, "title": "MCP 会话"}}})
        sid = int(parse_sse_text(r.text)["result"]["content"][0]["text"].split('"id": ')[1].split(",")[0])
        r = c.post("/mcp/", headers=SHDR, json={"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                                                "params": {"name": "log_progress",
                                                           "arguments": {"project_id": project_id, "title": "MCP 进展",
                                                                        "git_ref": "abc"}}})
        assert '"entry_type": "progress"' in parse_sse_text(r.text)["result"]["content"][0]["text"]
        r = c.post("/mcp/", headers=SHDR, json={"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                                                "params": {"name": "log_difficulty",
                                                           "arguments": {"project_id": project_id, "title": "异步坑",
                                                                        "severity": "high"}}})
        assert '"severity": "high"' in parse_sse_text(r.text)["result"]["content"][0]["text"]
        r = c.post("/mcp/", headers=SHDR, json={"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                                                "params": {"name": "end_dev_session",
                                                           "arguments": {"session_id": sid, "summary": "结束"}}})
        assert '"ended_at"' in parse_sse_text(r.text)["result"]["content"][0]["text"]
        r = c.post("/mcp/", headers=SHDR, json={"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                                                "params": {"name": "get_dev_log_stats_mcp",
                                                           "arguments": {"project_id": project_id}}})
        assert '"open_difficulties"' in parse_sse_text(r.text)["result"]["content"][0]["text"]
        r = c.post("/mcp/", headers=SHDR, json={"jsonrpc": "2.0", "id": 8, "method": "tools/call",
                                                "params": {"name": "get_project_state",
                                                           "arguments": {"project_id": project_id}}})
        assert "open_todos" in parse_sse_text(r.text)["result"]["content"][0]["text"]
        r = c.post("/mcp/", headers=SHDR, json={"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                                                "params": {"name": "get_dev_report",
                                                           "arguments": {"project_id": project_id}}})
        assert "开发汇报" in parse_sse_text(r.text)["result"]["content"][0]["text"]

        print("DEV LOGS CHECKS PASSED: service/rest/mcp")


if __name__ == "__main__":
    asyncio.run(main())
