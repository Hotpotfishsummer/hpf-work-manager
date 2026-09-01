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
