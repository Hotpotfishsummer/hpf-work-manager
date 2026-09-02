"""里程碑 CRUD 正常路径测试（B4 盲区补齐）。"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_milestone_full_crud(auth_client, test_project):
    # 创建
    resp = await auth_client.post(
        f"/api/projects/{test_project.id}/milestones",
        json={"name": "M1", "due_date": "2026-12-31"},
    )
    assert resp.status_code == 201
    mid = resp.json()["id"]
    assert resp.json()["name"] == "M1"
    assert resp.json()["status"] == "active"

    # 列表
    resp = await auth_client.get(f"/api/projects/{test_project.id}/milestones")
    assert resp.status_code == 200
    names = [m["name"] for m in resp.json()]
    assert "M1" in names

    # 更新
    resp = await auth_client.put(f"/api/milestones/{mid}", json={"name": "M1 改"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "M1 改"

    # 标记完成
    resp = await auth_client.put(f"/api/milestones/{mid}", json={"status": "done"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"

    # 删除
    resp = await auth_client.delete(f"/api/milestones/{mid}")
    assert resp.status_code == 204
    resp = await auth_client.get(f"/api/projects/{test_project.id}/milestones")
    assert mid not in [m["id"] for m in resp.json()]


async def test_delete_milestone_keeps_tasks(auth_client, test_project):
    """删除里程碑后其下任务保留（milestone_id 置空）。"""
    resp = await auth_client.post(
        f"/api/projects/{test_project.id}/milestones", json={"name": "M1"}
    )
    mid = resp.json()["id"]
    resp = await auth_client.post(
        f"/api/projects/{test_project.id}/tasks",
        json={"name": "T1", "milestone_id": mid},
    )
    tid = resp.json()["id"]

    resp = await auth_client.delete(f"/api/milestones/{mid}")
    assert resp.status_code == 204

    resp = await auth_client.get(f"/api/tasks/{tid}")
    assert resp.status_code == 200
    assert resp.json()["milestone_id"] is None
