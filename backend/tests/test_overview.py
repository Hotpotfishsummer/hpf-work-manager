"""Dashboard /overview 聚合端点回归测试。

覆盖 P3 修复的两个真 bug：
- 卡片统计三元组解包错误导致 done/overdue NameError（此前 total>0 即崩，测试全靠空库短路）
- REST list_tasks search/sort 分支缺导入（func/case NameError → 500）
"""

import pytest


@pytest.mark.asyncio
async def test_overview_project_cards_stats(auth_client, db_session, test_user, test_project):
    """项目卡片 progress/done_tasks/overdue_count 必须来自真实聚合而非默认值。"""
    from datetime import date, timedelta

    from app.models import Task

    today = date.today()
    db_session.add_all(
        [
            Task(project_id=test_project.id, name="已完成", status="done", progress=100),
            Task(project_id=test_project.id, name="进行中", status="in_progress", progress=40),
            Task(
                project_id=test_project.id,
                name="已逾期",
                status="in_progress",
                progress=10,
                due_date=today - timedelta(days=3),
            ),
        ]
    )
    await db_session.commit()

    resp = await auth_client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_projects"] >= 1
    card = next(c for c in data["projects"] if c["project_id"] == test_project.id)
    assert card["total_tasks"] == 3
    assert card["done_tasks"] == 1
    assert card["overdue_count"] == 1
    assert card["progress"] == 33.3

    # 跨项目逾期列表应包含刚建的逾期任务
    assert any(t["name"] == "已逾期" for t in data["overdue_tasks"])


@pytest.mark.asyncio
async def test_overview_empty_user(auth_client):
    """无项目用户返回零值结构而非报错。"""
    resp = await auth_client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_projects"] == 0
    assert data["projects"] == []
    assert data["today_completed"] == 0


@pytest.mark.asyncio
async def test_list_tasks_search_and_sort(auth_client, db_session, test_project):
    """search/sort 参数必须可用（回归：func/case 未导入导致 500）。"""
    from datetime import date

    from app.models import Task

    db_session.add_all(
        [
            Task(project_id=test_project.id, name="编写登录接口", status="todo", progress=0),
            Task(project_id=test_project.id, name="设计首页", status="in_progress", progress=50, priority="high"),
            Task(
                project_id=test_project.id,
                name="修复登录bug",
                status="in_progress",
                progress=20,
                priority="medium",
                due_date=date(2026, 1, 1),
            ),
        ]
    )
    await db_session.commit()
    base = f"/api/projects/{test_project.id}/tasks"

    # search 命中名称（大小写不敏感）
    resp = await auth_client.get(base, params={"search": "登录"})
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert names == ["编写登录接口", "修复登录bug"]

    # search 命中描述
    resp = await auth_client.get(base, params={"search": "全不匹配的词"})
    assert resp.status_code == 200
    assert resp.json() == []

    # priority_desc 排序：high 在前
    resp = await auth_client.get(base, params={"sort": "priority_desc"})
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert names[0] == "设计首页"

    # due_asc：有截止日的排前且升序
    resp = await auth_client.get(base, params={"sort": "due_asc"})
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert "修复登录bug" in names[0]

    # overdue=true：SQL 级过滤，只返回未完成且有截止日且已逾期
    resp = await auth_client.get(base, params={"overdue": "true"})
    assert resp.status_code == 200
    names = [t["name"] for t in resp.json()]
    assert names == ["修复登录bug"]


@pytest.mark.asyncio
async def test_weighted_progress(auth_client, db_session, test_project):
    """P4-1: 工时加权进度——权重=预估工时（未填按 1），与数量进度并存。"""
    from app.models import Task

    # 3 个任务：9h 完成(100)、1h 未开始(0)、未填工时 进行中(50)
    # 数量进度 = 1/3 = 33.3
    # 加权 = (9*100 + 1*0 + 1*50) / (9+1+1) = 950/11 = 86.4
    # 总工时（已填）= 10
    db_session.add_all(
        [
            Task(project_id=test_project.id, name="大任务", status="done", progress=100, estimated_hours=9),
            Task(project_id=test_project.id, name="小任务", status="todo", progress=0, estimated_hours=1),
            Task(project_id=test_project.id, name="未填工时", status="in_progress", progress=50),
        ]
    )
    await db_session.commit()

    resp = await auth_client.get(f"/api/projects/{test_project.id}/stats")
    assert resp.status_code == 200
    s = resp.json()
    assert s["progress"] == 33.3
    assert s["weighted_progress"] == 86.4
    assert s["estimated_hours_total"] == 10.0

    # overview 卡片同样带加权进度
    resp = await auth_client.get("/api/overview")
    assert resp.status_code == 200
    card = next(c for c in resp.json()["projects"] if c["project_id"] == test_project.id)
    assert card["weighted_progress"] == 86.4


@pytest.mark.asyncio
async def test_weighted_progress_no_hours(auth_client, db_session, test_project):
    """P4-1: 无人填工时时 estimated_hours_total=None，加权退化为数量进度。"""
    from app.models import Task

    db_session.add_all(
        [
            Task(project_id=test_project.id, name="A", status="done", progress=100),
            Task(project_id=test_project.id, name="B", status="todo", progress=0),
        ]
    )
    await db_session.commit()

    resp = await auth_client.get(f"/api/projects/{test_project.id}/stats")
    assert resp.status_code == 200
    s = resp.json()
    assert s["estimated_hours_total"] is None
    assert s["progress"] == 50.0
    assert s["weighted_progress"] == 50.0  # 全部按 1 权重 → 等同数量进度


@pytest.mark.asyncio
async def test_progress_snapshot_upsert_and_history(auth_client, db_session, test_project):
    """P4-3: 读取 stats 时按天沉淀快照；重复读取同日只更新不新增；历史端点升序返回。"""
    from app.models import Task
    from app.utils.time import display_today

    db_session.add(Task(project_id=test_project.id, name="T1", status="done", progress=100))
    db_session.add(Task(project_id=test_project.id, name="T2", status="todo", progress=0))
    await db_session.commit()

    # 第一次读取 stats → 沉淀今日快照
    resp = await auth_client.get(f"/api/projects/{test_project.id}/stats")
    assert resp.status_code == 200

    # 任务变化后再次读取 → 同一天快照被更新而非新增
    db_session.add(Task(project_id=test_project.id, name="T3", status="done", progress=100))
    await db_session.commit()
    resp = await auth_client.get(f"/api/projects/{test_project.id}/stats")
    assert resp.status_code == 200

    resp = await auth_client.get(f"/api/projects/{test_project.id}/progress-history")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 1  # 同日 upsert，仅一条
    snap = history[0]
    assert snap["date"] == display_today().isoformat()
    assert snap["total_tasks"] == 3
    assert snap["done_tasks"] == 2
    assert snap["progress"] == 66.7
