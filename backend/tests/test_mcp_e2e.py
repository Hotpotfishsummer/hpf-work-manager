"""MCP Server 端到端验证（SSE 流式响应 + Streamable HTTP）。

基于 SQLite 内存库，验证：认证 → initialize → tools/list → 工具调用（create 项目/任务、update 状态）。
运行：export MCP_ALLOWED_HOSTS=testserver,localhost && python tests/test_mcp_e2e.py
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

    # SQLite 覆盖 DB 层
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
    import app.routers.keys as keys
    keys.get_db = get_db_override

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.models import ApiKey, User
    from app.core.apikey import generate_api_key
    from app.core.security import hash_password

    async with AsyncSessionLocal() as db:
        u = User(username="alice", email="a@b.c", hashed_password=hash_password("pw123456"))
        db.add(u)
        await db.commit()
        await db.refresh(u)
        raw, prefix, h = generate_api_key(u.id)
        db.add(ApiKey(user_id=u.id, name="claude", prefix=prefix, key_hash=h))
        await db.commit()

    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        HDR = {"Authorization": f"Bearer {raw}", "Accept": "application/json, text/event-stream"}
        r = c.post(
            "/mcp/",
            headers=HDR,
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                             "clientInfo": {"name": "t", "version": "1"}}},
        )
        assert r.status_code == 200, r.text
        sid = r.headers.get("mcp-session-id")
        assert sid, "缺少 mcp-session-id"
        SHDR = {**HDR, "mcp-session-id": sid}

        r = c.post("/mcp/", headers=SHDR, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        data = parse_sse_text(r.text)
        names = [t["name"] for t in data["result"]["tools"]]
        assert "update_task" in names and "list_projects" in names, names

        r = c.post("/mcp/", headers=SHDR, json={"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                                "params": {"name": "create_project", "arguments": {"name": "P1"}}})
        assert '"name": "P1"' in parse_sse_text(r.text)["result"]["content"][0]["text"]

        r = c.post("/mcp/", headers=SHDR, json={"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                                                "params": {"name": "create_task",
                                                           "arguments": {"project_id": 1, "name": "T1", "status": "todo"}}})
        import re
        tid = int(re.search(r'"id": (\d+)', parse_sse_text(r.text)["result"]["content"][0]["text"]).group(1))
        r = c.post("/mcp/", headers=SHDR, json={"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                                                "params": {"name": "update_task",
                                                           "arguments": {"task_id": tid, "status": "done"}}})
        content = parse_sse_text(r.text)["result"]["content"][0]["text"]
        assert '"progress": 100' in content and '"status": "done"' in content, content

        # 未认证访问被拒
        r = c.post("/mcp/", headers={"Accept": "application/json, text/event-stream"},
                   json={"jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": {}})
        assert r.status_code == 401, r.status_code

        print("MCP E2E OK: auth/init/tools/create_task/update_state/401")


if __name__ == "__main__":
    asyncio.run(main())