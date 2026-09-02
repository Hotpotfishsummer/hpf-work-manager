"""跨用户数据隔离测试（B4）。

owner_id 隔离是本系统核心安全属性：用户 B 访问用户 A 的资源必须得到 404
（语义为"不存在"，避免泄露他人资源存在性），且列表/搜索不得返回他人数据。
"""

import pytest

pytestmark = pytest.mark.asyncio


@pytest.fixture()
async def owned_project_with_children(auth_client, test_project):
    """当前用户的项目 + 任务 + 里程碑 + DevLog。"""
    resp = await auth_client.post(
        f"/api/projects/{test_project.id}/tasks", json={"name": "A 的任务"}
    )
    assert resp.status_code == 201
    task_id = resp.json()["id"]

    resp = await auth_client.post(
        f"/api/projects/{test_project.id}/milestones", json={"name": "A 的里程碑"}
    )
    assert resp.status_code == 201
    milestone_id = resp.json()["id"]

    resp = await auth_client.post(
        f"/api/projects/{test_project.id}/logs",
        json={"entry_type": "note", "title": "A 的记录", "content": "A 的开发记录"},
    )
    assert resp.status_code == 201
    log_id = resp.json()["id"]

    return {"project": test_project, "task": task_id, "milestone": milestone_id, "log": log_id}


async def test_other_user_project_read_404(other_auth_client, owned_project_with_children):
    ids = owned_project_with_children
    resp = await other_auth_client.get(f"/api/projects/{ids['project'].id}")
    assert resp.status_code == 404


async def test_other_user_project_update_404(other_auth_client, owned_project_with_children):
    ids = owned_project_with_children
    resp = await other_auth_client.put(
        f"/api/projects/{ids['project'].id}", json={"name": "篡改"}
    )
    assert resp.status_code == 404


async def test_other_user_project_delete_404(other_auth_client, owned_project_with_children):
    ids = owned_project_with_children
    resp = await other_auth_client.delete(f"/api/projects/{ids['project'].id}")
    assert resp.status_code == 404


async def test_other_user_task_crud_404(other_auth_client, owned_project_with_children):
    tid = owned_project_with_children["task"]
    assert (await other_auth_client.get(f"/api/tasks/{tid}")).status_code == 404
    assert (
        await other_auth_client.put(f"/api/tasks/{tid}", json={"progress": 50})
    ).status_code == 404
    assert (await other_auth_client.delete(f"/api/tasks/{tid}")).status_code == 404


async def test_other_user_task_bulk_excludes_foreign(other_auth_client, owned_project_with_children):
    """bulk 更新他人任务：不报错但也不生效（按 owner 过滤后集合为空）。"""
    tid = owned_project_with_children["task"]
    resp = await other_auth_client.post(
        "/api/tasks/bulk", json={"ids": [tid], "data": {"priority": "high"}}
    )
    assert resp.status_code == 204


async def test_other_user_milestone_access_404(other_auth_client, owned_project_with_children):
    ids = owned_project_with_children
    # 列表挂在他人项目下 → 404
    resp = await other_auth_client.get(f"/api/projects/{ids['project'].id}/milestones")
    assert resp.status_code == 404
    # 直接访问他人里程碑 → 404
    assert (
        await other_auth_client.put(
            f"/api/milestones/{ids['milestone']}", json={"name": "篡改"}
        )
    ).status_code == 404
    assert (
        await other_auth_client.delete(f"/api/milestones/{ids['milestone']}")
    ).status_code == 404


async def test_other_user_devlog_access_404(other_auth_client, owned_project_with_children):
    ids = owned_project_with_children
    assert (await other_auth_client.get(f"/api/logs/{ids['log']}")).status_code == 404
    assert (
        await other_auth_client.delete(f"/api/logs/{ids['log']}")
    ).status_code == 404
    # 往他人项目写记录 → 404
    resp = await other_auth_client.post(
        f"/api/projects/{ids['project'].id}/logs",
        json={"entry_type": "note", "title": "x", "content": "x"},
    )
    assert resp.status_code == 404


async def test_other_user_stats_family_404(other_auth_client, owned_project_with_children):
    pid = owned_project_with_children["project"].id
    for path in ("/stats", "/burndown", "/gantt", "/progress-history"):
        resp = await other_auth_client.get(f"/api/projects/{pid}{path}")
        assert resp.status_code == 404, f"{path} 应 404，实际 {resp.status_code}"


async def test_other_user_lists_do_not_leak(other_auth_client, owned_project_with_children):
    """列表与搜索不得返回他人数据。"""
    resp = await other_auth_client.get("/api/projects")
    assert [p["id"] for p in resp.json()] == []

    resp = await other_auth_client.get("/api/overview")
    assert resp.status_code == 200
    assert resp.json()["total_projects"] == 0

    resp = await other_auth_client.get("/api/search", params={"q": "A 的"})
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    assert resp.json()["total"] == 0


async def test_owner_still_sees_own_data(auth_client, owned_project_with_children):
    """隔离测试的反向校验：owner 自己访问一切正常。"""
    ids = owned_project_with_children
    resp = await auth_client.get(f"/api/projects/{ids['project'].id}")
    assert resp.status_code == 200
    resp = await auth_client.get(f"/api/tasks/{ids['task']}")
    assert resp.status_code == 200
    resp = await auth_client.get(f"/api/logs/{ids['log']}")
    assert resp.status_code == 200
