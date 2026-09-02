"""统计端点家族测试（B4 盲区补齐）：/burndown、/gantt、/progress-history、/search。"""

import pytest

pytestmark = pytest.mark.asyncio


async def _create_tasks(auth_client, test_project, n, done=0):
    ids = []
    for i in range(n):
        resp = await auth_client.post(
            f"/api/projects/{test_project.id}/tasks", json={"name": f"T{i}"}
        )
        ids.append(resp.json()["id"])
    for tid in ids[:done]:
        resp = await auth_client.put(f"/api/tasks/{tid}", json={"status": "done"})
        assert resp.status_code == 200
    return ids


async def test_burndown_shape(auth_client, test_project):
    await _create_tasks(auth_client, test_project, 5, done=2)
    # 显式设置项目起止日覆盖完成日（缺省回退用本地 date.today()，与 UTC 完成分桶
    # 存在时区错位——见 IMPROVEMENTS B9，此处规避该边界）
    from datetime import timedelta

    from app.utils.time import display_today

    today = display_today()
    resp = await auth_client.put(
        f"/api/projects/{test_project.id}",
        json={
            "start_date": (today - timedelta(days=3)).isoformat(),
            "end_date": (today + timedelta(days=3)).isoformat(),
        },
    )
    assert resp.status_code == 200

    resp = await auth_client.get(f"/api/projects/{test_project.id}/burndown")
    assert resp.status_code == 200
    points = resp.json()
    assert isinstance(points, list) and len(points) >= 1
    first = points[0]
    assert {"date", "ideal_remaining", "actual_remaining"} <= set(first.keys())
    # 最后一(actual)应等于未完成数 3
    assert points[-1]["actual_remaining"] == 3


async def test_gantt_shape(auth_client, test_project):
    await _create_tasks(auth_client, test_project, 3)
    resp = await auth_client.get(f"/api/projects/{test_project.id}/gantt")
    assert resp.status_code == 200
    data = resp.json()
    assert "tasks" in data
    assert len(data["tasks"]) == 3
    assert {"id", "name", "start", "end"} <= set(data["tasks"][0].keys())


async def test_progress_history_after_stats_reads(auth_client, test_project):
    await _create_tasks(auth_client, test_project, 4, done=1)
    # 读 stats 沉淀快照；再读一次同日只更新不新增
    await auth_client.get(f"/api/projects/{test_project.id}/stats")
    await auth_client.get(f"/api/projects/{test_project.id}/stats")

    resp = await auth_client.get(f"/api/projects/{test_project.id}/progress-history")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 1  # 同日只一条
    snap = history[0]
    assert snap["total_tasks"] == 4
    assert snap["done_tasks"] == 1
    # 升序
    dates = [s["date"] for s in history]
    assert dates == sorted(dates)


async def test_search_finds_project_task_milestone(auth_client, test_project):
    await auth_client.post(f"/api/projects/{test_project.id}/tasks", json={"name": "蓝鲸模块"})
    await auth_client.post(
        f"/api/projects/{test_project.id}/milestones", json={"name": "蓝鲸里程碑"}
    )
    resp = await auth_client.get("/api/search", params={"q": "蓝鲸"})
    assert resp.status_code == 200
    body = resp.json()
    kinds = {item["type"] for item in body["items"]}
    assert {"task", "milestone"} <= kinds
    # 任务/里程碑结果带所属项目名（此前恒为 null）
    for item in body["items"]:
        assert item["project_name"] == test_project.name
    assert body["total"] >= 2

    # total 为精确总数（按实体分别 count，不受分页影响）
    resp = await auth_client.get("/api/search", params={"q": "蓝鲸", "limit": 1})
    assert resp.status_code == 200
    assert resp.json()["total"] == body["total"]
    # limit 按实体独立生效：3 类实体 × limit=1 → 至多 3 条
    assert len(resp.json()["items"]) <= 3


async def test_search_min_length_validation(auth_client):
    resp = await auth_client.get("/api/search", params={"q": "蓝"})
    assert resp.status_code == 422
