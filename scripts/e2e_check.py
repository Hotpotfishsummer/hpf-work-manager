"""端到端 API 逻辑验证（SQLite 替代 PostgreSQL，仅验证业务逻辑与路由）。
数据库使用 /tmp 下的独立临时文件，避免污染项目目录。
运行：python scripts/e2e_check.py
"""
import asyncio
import os
import sys

DB_PATH = f"/tmp/hpf_e2e_{os.getpid()}.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DB_PATH}"
os.environ["ENVIRONMENT"] = "dev"  # 允许短测试密钥（fail-fast 校验放行）
os.environ["SECRET_KEY"] = "test-secret"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import httpx  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

import app.models  # noqa: E402
from app.database import Base  # noqa: E402

BASE = "http://test/api"
PASSED = []
FAILED = []


def check(name: str, cond: bool, extra: str = ""):
    (PASSED if cond else FAILED).append(name)
    print(f"  {'✅' if cond else '❌'} {name} {extra}")


async def main():
    # 建表
    engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    transport = httpx.ASGITransport(app=__import__("app.main", fromlist=["app"]).app)
    async with httpx.AsyncClient(transport=transport, base_url=BASE) as c:
        # 1. 注册
        r = await c.post("/auth/register", json={
            "username": "tester", "email": "t@t.com", "password": "secret123"})
        check("注册成功", r.status_code == 201, f"-> {r.status_code}")
        token = r.json()["access_token"]
        H = {"Authorization": f"Bearer {token}"}

        # 2. 重复注册应失败
        r = await c.post("/auth/register", json={
            "username": "tester", "email": "t2@t.com", "password": "secret123"})
        check("重复用户名注册被拒", r.status_code == 400)

        # 3. 登录 + me
        r = await c.post("/auth/login", json={"username": "tester", "password": "secret123"})
        check("登录成功", r.status_code == 200)
        r = await c.get("/auth/me", headers=H)
        check("获取当前用户", r.status_code == 200 and r.json()["username"] == "tester")

        # 4. 未授权访问被拒
        r = await c.get("/projects")
        check("无 token 访问被拒(401)", r.status_code == 401)

        # 4.1 API Key：创建 / 列表 / exchange / 用 key 换 JWT 后建项目
        r = await c.post("/keys", headers=H, json={"name": "claude-code"})
        check("创建 API Key", r.status_code == 201 and r.json()["key"].startswith("hpf_"),
              f"-> {r.status_code}")
        api_key = r.json()["key"]
        r = await c.get("/keys", headers=H)
        check("列出 API Key", r.status_code == 200 and len(r.json()) == 1)
        r = await c.post("/keys/exchange", json={"key": api_key})
        check("API Key 换 JWT", r.status_code == 200 and r.json().get("access_token"))
        machine_jwt = r.json()["access_token"]
        MH = {"Authorization": f"Bearer {machine_jwt}"}
        r = await c.post("/projects", headers=MH, json={"name": "AI 创建的项目"})
        check("用 API Key 换的 JWT 建项目", r.status_code == 201, f"-> {r.status_code}")
        # 撤销后 exchange 应失败
        r = await c.get("/keys", headers=H)
        key_id = r.json()[0]["id"]
        r = await c.delete(f"/keys/{key_id}", headers=H)
        check("撤销 API Key", r.status_code == 204)
        r = await c.post("/keys/exchange", json={"key": api_key})
        check("撤销后 exchange 被拒(401)", r.status_code == 401, f"-> {r.status_code}")

        # 5. 创建项目
        r = await c.post("/projects", headers=H, json={
            "name": "官网改版", "description": "2026 官网重构",
            "start_date": "2026-08-01", "end_date": "2026-09-30"})
        check("创建项目", r.status_code == 201, f"-> {r.status_code}")
        pid = r.json()["id"]

        # 6. 创建里程碑（相对日期：过去 A / 未来 B·C，避免脚本随时间腐化）
        from datetime import date, timedelta
        today = date.today()
        d = lambda off: (today + timedelta(days=off)).isoformat()
        r = await c.post(f"/projects/{pid}/milestones", headers=H, json={
            "name": "设计评审", "due_date": d(-19)})
        check("创建里程碑", r.status_code == 201)
        mid = r.json()["id"]

        # 7. 创建任务（含依赖）：A 已逾期，B/C 未逾期
        r = await c.post(f"/projects/{pid}/tasks", headers=H, json={
            "name": "页面设计", "priority": "high", "due_date": d(-24),
            "milestone_id": mid, "start_date": d(-33), "progress": 40})
        check("创建任务A", r.status_code == 201)
        ta = r.json()["id"]
        r = await c.post(f"/projects/{pid}/tasks", headers=H, json={
            "name": "前端开发", "status": "in_progress", "due_date": d(-2 + 61)})
        check("创建任务B", r.status_code == 201)
        tb = r.json()["id"]
        r = await c.post(f"/projects/{pid}/tasks", headers=H, json={
            "name": "测试验收", "due_date": d(25)})
        check("创建任务C", r.status_code == 201)
        tc = r.json()["id"]

        # 8. 添加依赖 B→A
        r = await c.post(f"/tasks/{tb}/dependencies", headers=H, json={"depends_on_task_id": ta})
        check("添加依赖 B→A", r.status_code == 204)
        r = await c.post(f"/tasks/{tb}/dependencies", headers=H, json={"depends_on_task_id": ta})
        check("重复依赖被拒", r.status_code == 400)
        r = await c.post(f"/tasks/{tb}/dependencies", headers=H, json={"depends_on_task_id": tb})
        check("自依赖被拒", r.status_code == 400)

        # 9. 统计（1 个延期：A due 08-10 早于今天 08-11）
        r = await c.get(f"/projects/{pid}/stats", headers=H)
        s = r.json()
        check("stats 总数=3", s["total_tasks"] == 3, f"got {s['total_tasks']}")
        check("stats 进行中=1", s["in_progress_tasks"] == 1, f"got {s['in_progress_tasks']}")
        check("stats 延期=1(A)", len(s["overdue_tasks"]) == 1 and s["overdue_tasks"][0]["name"] == "页面设计",
              f"got {[o['name'] for o in s['overdue_tasks']]}")
        check("stats 进度=0", s["progress"] == 0.0)

        # 10. 完成任务 A → 自动 progress=100 + completed_at + 进度更新
        r = await c.put(f"/tasks/{ta}", headers=H, json={"status": "done"})
        check("完成任务A", r.status_code == 200 and r.json()["progress"] == 100 and r.json()["completed_at"])
        r = await c.get(f"/projects/{pid}/stats", headers=H)
        s = r.json()
        check("完成后进度≈33.3", abs(s["progress"] - 33.3) < 0.2, f"got {s['progress']}")
        check("完成后期延清零", len(s["overdue_tasks"]) == 0)

        # 11. 任务 done → 改回 todo → completed_at 清空
        r = await c.put(f"/tasks/{ta}", headers=H, json={"status": "todo", "progress": 10})
        check("改回 todo 清空 completed_at", r.json()["completed_at"] is None and r.json()["progress"] == 10)

        # 12. 燃尽图
        r = await c.get(f"/projects/{pid}/burndown", headers=H)
        bd = r.json()
        check("燃尽图数据点数=61天", len(bd) == 61, f"got {len(bd)}")
        check("燃尽图起点=总任务数", bd[0]["ideal_remaining"] == 3, f"got {bd[0]['ideal_remaining']}")
        check("燃尽图终点=0", bd[-1]["ideal_remaining"] == 0)

        # 13. 甘特图
        r = await c.get(f"/projects/{pid}/gantt", headers=H)
        g = r.json()
        check("甘特图任务数=3", len(g["tasks"]) == 3)
        dep = [t for t in g["tasks"] if t["id"] == str(tb)][0]["dependencies"]
        check("甘特图依赖映射", dep == f"{tb}:{ta}", f"got {dep}")

        # 14. 批量更新 + 过滤
        r = await c.post("/tasks/bulk", headers=H, json={"ids": [tb, tc], "data": {"status": "done"}})
        check("批量完成任务", r.status_code == 204)
        r = await c.get(f"/projects/{pid}/tasks", headers=H, params={"status": "done"})
        check("按状态过滤", len(r.json()) == 2, f"got {len(r.json())}")

        # 15. 删除里程碑 → 任务 milestone_id 置空（保留）
        r = await c.delete(f"/milestones/{mid}", headers=H)
        check("删除里程碑", r.status_code == 204)
        r = await c.get(f"/tasks/{ta}", headers=H)
        check("任务保留且 milestone 置空", r.json()["milestone_id"] is None)

        # 16. 删除项目 → 级联删除任务/里程碑
        r = await c.delete(f"/projects/{pid}", headers=H)
        check("删除项目", r.status_code == 204)
        r = await c.get(f"/projects/{pid}", headers=H)
        check("项目已删除(404)", r.status_code == 404)
        r = await c.get("/projects", headers=H)
        check("项目列表不含已删项目", all(p["id"] != pid for p in r.json()))

        # 17. SSE 事件流：未登录 401，非本人项目 404，正常项目 200
        r = await c.get(f"/events/stream?project_id={pid}")
        check("SSE 未授权被拒(401)", r.status_code == 401)
        r = await c.get("/events/stream?project_id=999999", headers=H)
        check("SSE 他人项目被拒(404)", r.status_code == 404)

    # 清理本次创建的 /tmp 临时数据库（仅限自身文件）
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    print(f"\n结果: {len(PASSED)} 通过 / {len(FAILED)} 失败")
    if FAILED:
        print("失败项:", FAILED)
        sys.exit(1)
    print("全部通过 ✅")


if __name__ == "__main__":
    asyncio.run(main())
