"""任务依赖：环检测 + depends_on 序列化 + 请求体校验（B5/F3）。"""

import pytest

pytestmark = pytest.mark.asyncio


async def _create_task(auth_client, test_project, name: str) -> int:
    resp = await auth_client.post(
        f"/api/projects/{test_project.id}/tasks", json={"name": name}
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_task_out_includes_depends_on(auth_client, test_project):
    """任务列表/详情应返回 depends_on（此前字段缺失，前端依赖标签永不显示）。"""
    a = await _create_task(auth_client, test_project, "A")
    b = await _create_task(auth_client, test_project, "B")
    resp = await auth_client.post(
        f"/api/tasks/{b}/dependencies", json={"depends_on_task_id": a}
    )
    assert resp.status_code == 204

    resp = await auth_client.get(f"/api/tasks/{b}")
    assert resp.status_code == 200
    assert resp.json()["depends_on"] == [a]

    resp = await auth_client.get(f"/api/projects/{test_project.id}/tasks")
    by_id = {t["id"]: t for t in resp.json()}
    assert by_id[b]["depends_on"] == [a]
    assert by_id[a]["depends_on"] == []


async def test_dependency_body_type_validated(auth_client, test_project):
    """裸 dict 换成 Pydantic 模型：非正整数 → 明确 422。"""
    a = await _create_task(auth_client, test_project, "A")
    resp = await auth_client.post(
        f"/api/tasks/{a}/dependencies", json={"depends_on_task_id": "abc"}
    )
    assert resp.status_code == 422
    resp = await auth_client.post(
        f"/api/tasks/{a}/dependencies", json={"depends_on_task_id": 0}
    )
    assert resp.status_code == 422


async def test_direct_cycle_rejected(auth_client, test_project):
    """A→B 后再 B→A 必须 400（此前可写入环，甘特/拓扑死循环）。"""
    a = await _create_task(auth_client, test_project, "A")
    b = await _create_task(auth_client, test_project, "B")
    resp = await auth_client.post(
        f"/api/tasks/{a}/dependencies", json={"depends_on_task_id": b}
    )
    assert resp.status_code == 204

    resp = await auth_client.post(
        f"/api/tasks/{b}/dependencies", json={"depends_on_task_id": a}
    )
    assert resp.status_code == 400
    assert "循环" in resp.json()["detail"]


async def test_long_cycle_rejected(auth_client, test_project):
    """三节点长环：A→B→C 后 C→A 应拒绝。"""
    a = await _create_task(auth_client, test_project, "A")
    b = await _create_task(auth_client, test_project, "B")
    c = await _create_task(auth_client, test_project, "C")
    for tid, dep in ((a, b), (b, c)):
        resp = await auth_client.post(
            f"/api/tasks/{tid}/dependencies", json={"depends_on_task_id": dep}
        )
        assert resp.status_code == 204

    resp = await auth_client.post(
        f"/api/tasks/{c}/dependencies", json={"depends_on_task_id": a}
    )
    assert resp.status_code == 400


async def test_diamond_no_false_positive(auth_client, test_project):
    """菱形结构（A←B,C，B/C←D）不误报成环。"""
    a = await _create_task(auth_client, test_project, "A")
    b = await _create_task(auth_client, test_project, "B")
    c = await _create_task(auth_client, test_project, "C")
    d = await _create_task(auth_client, test_project, "D")
    for tid, dep in ((b, a), (c, a), (d, b), (d, c)):
        resp = await auth_client.post(
            f"/api/tasks/{tid}/dependencies", json={"depends_on_task_id": dep}
        )
        assert resp.status_code == 204, f"{tid}→{dep} 不应被误判成环"


async def test_self_dependency_rejected(auth_client, test_project):
    a = await _create_task(auth_client, test_project, "A")
    resp = await auth_client.post(
        f"/api/tasks/{a}/dependencies", json={"depends_on_task_id": a}
    )
    assert resp.status_code == 400
