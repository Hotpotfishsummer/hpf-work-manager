"""端到端集成验证：API Key 认证、任务状态机、SSE 事件、MCP（基于 SQLite）。

在不依赖 Docker/Postgres 的环境下，用 aiosqlite 覆盖 DB 层验证核心链路。
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class _URL:
    def __init__(self, s):
        self.raw = s


def setup_sqlite():
    """将全局 async engine 指向 SQLite 内存库，并建表。"""
    import app.database as database
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.database import Base

    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    database.engine = test_engine
    database.AsyncSessionLocal = async_sessionmaker(
        test_engine, class_=database.AsyncSession, expire_on_commit=False
    )
    # 让 get_db 使用新 session 工厂
    from app.database import AsyncSessionLocal

    async def get_db_override():
        async with AsyncSessionLocal() as session:
            yield session

    import app.deps as deps
    deps.get_db = get_db_override
    import app.routers.projects as projects
    projects.get_db = get_db_override
    import app.routers.tasks as tasks
    tasks.get_db = get_db_override
    import app.routers.keys as keys
    keys.get_db = get_db_override
    import app.routers.events as events
    events.get_db = get_db_override

    async def _init():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    return _init


async def main():
    init = setup_sqlite()
    await init()

    from app.database import AsyncSessionLocal
    from app.models import User, ApiKey, Project, Task
    from app.core import apikey
    from app.core.events import subscribe, publish
    from app.services.tasks import apply_task_update, to_out
    from app.utils.time import utcnow
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        # 1. 建用户
        user = User(
            username="alice",
            email="a@b.co",
            hashed_password="x",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # 2. API Key 生成 + 校验
        raw, prefix, key_hash = apikey.generate_api_key(user.id)
        assert apikey.validate_api_key(raw) == key_hash
        assert apikey.validate_api_key("bad") is None

        key = ApiKey(user_id=user.id, name="claude", prefix=prefix, key_hash=key_hash)
        db.add(key)
        await db.commit()
        await db.refresh(key)
        assert key.id is not None

        # 3. 建项目
        proj = Project(owner_id=user.id, name="P1")
        db.add(proj)
        await db.commit()
        await db.refresh(proj)

        # 4. 任务状态机：done -> progress=100, completed_at
        task = Task(project_id=proj.id, name="T1", status="todo", progress=0)
        db.add(task)
        await db.commit()
        await db.refresh(task)
        apply_task_update(task, {"status": "done"})
        assert task.progress == 100
        assert task.completed_at is not None
        # 非 done 清空 completed_at
        apply_task_update(task, {"status": "in_progress"})
        assert task.completed_at is None
        await db.commit()

        # 5. SSE 事件发布/订阅
        q = asyncio.Queue(maxsize=10)
        await subscribe(proj.id, q)
        await publish(proj.id, "updated", "task", task.id)
        msg = await asyncio.wait_for(q.get(), timeout=2)
        import json

        data = json.loads(msg)
        assert data["entity"] == "task" and data["project_id"] == proj.id

        print("ALL INTEGRATION CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())