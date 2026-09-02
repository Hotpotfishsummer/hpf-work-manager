"""P4-4 全局事件流测试：总线接线 + 所有权过滤 + 认证边界。"""

import asyncio
import json

import pytest

from app.core.events import publish, subscribe_global, unsubscribe_global
from app.routers.events import event_allowed


@pytest.mark.asyncio
async def test_global_bus_receives_all_projects():
    """全局主题能收到任意项目的事件。"""
    queue: asyncio.Queue = asyncio.Queue(maxsize=10)
    await subscribe_global(queue)
    try:
        await publish(1, "updated", "task", 11)
        await publish(2, "created", "log", 22)
        m1 = json.loads(await asyncio.wait_for(queue.get(), timeout=2))
        m2 = json.loads(await asyncio.wait_for(queue.get(), timeout=2))
        assert {m1["project_id"], m2["project_id"]} == {1, 2}
    finally:
        await unsubscribe_global(queue)


@pytest.mark.asyncio
async def test_publish_fans_out_to_global_and_project():
    """同一次 publish 同时触达项目订阅者与全局订阅者。"""
    project_q: asyncio.Queue = asyncio.Queue(maxsize=10)
    global_q: asyncio.Queue = asyncio.Queue(maxsize=10)
    from app.core.events import subscribe, unsubscribe

    await subscribe(7, project_q)
    await subscribe_global(global_q)
    try:
        await publish(7, "updated", "task", 1)
        assert json.loads(await asyncio.wait_for(project_q.get(), timeout=2))["project_id"] == 7
        assert json.loads(await asyncio.wait_for(global_q.get(), timeout=2))["project_id"] == 7
    finally:
        await unsubscribe(7, project_q)
        await unsubscribe_global(global_q)


def test_event_allowed_filters_foreign_projects():
    """全局流只放行自己拥有的项目事件，脏数据一律拒绝。"""
    mine = {1, 3}
    own = json.dumps({"project_id": 1, "type": "updated"})
    other = json.dumps({"project_id": 2, "type": "updated"})
    assert event_allowed(own, mine) is True
    assert event_allowed(other, mine) is False
    # 项目级订阅不做过滤
    assert event_allowed(other, None) is True
    # 脏数据不通过（不泄露、不崩溃）
    assert event_allowed("not-json", mine) is False


@pytest.mark.asyncio
async def test_global_stream_requires_auth(client):
    """无凭证访问全局流 → 401。"""
    resp = await client.get("/api/events/stream")
    assert resp.status_code == 401
