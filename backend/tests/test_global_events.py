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


@pytest.mark.asyncio
async def test_ticket_rate_limited_after_60_per_minute(auth_client):
    """/events/ticket 挂了 slowapi 60/minute：连续请求应触发 429（nginx 之外的应用层兜底）。"""
    from app.core.ratelimit import limiter

    limiter.reset()
    try:
        codes = []
        for _ in range(61):
            resp = await auth_client.post("/api/events/ticket")
            codes.append(resp.status_code)
            if resp.status_code == 429:
                break
        assert 429 in codes, f"61 次请求内应出现 429，实际末尾: {codes[-5:]}"
    finally:
        limiter.reset()


@pytest.mark.asyncio
async def test_full_stream_flow_subscribe_and_receive(auth_client, test_project):
    """完整流集成：换 ticket → 订阅项目流 → 写操作发布事件 → 流中收到 project-update。"""
    import asyncio
    import json as _json

    # 1. 换取短期 ticket
    resp = await auth_client.post("/api/events/ticket")
    assert resp.status_code == 200
    ticket = resp.json()["ticket"]

    url = f"/api/events/stream?project_id={test_project.id}&ticket={ticket}"
    lines: list[str] = []

    async def read_first_event():
        async with auth_client.stream("GET", url) as resp:
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                lines.append(line)
                if line.startswith("event: project-update"):
                    return True
        return False

    reader = asyncio.create_task(read_first_event())
    await asyncio.sleep(1)  # 等 SSE 端完成订阅

    # 2. 写操作 → 服务端 publish → SSE 流转发
    done = False
    for _ in range(5):  # 容忍订阅竞态：多次触发直到流中出现事件
        resp = await auth_client.post(
            f"/api/projects/{test_project.id}/tasks", json={"name": "sse 集成"}
        )
        assert resp.status_code == 201
        try:
            done = await asyncio.wait_for(asyncio.shield(reader), timeout=1)
            if done:
                break
        except (asyncio.TimeoutError, TimeoutError):
            continue

    assert done
    # 解析事件负载
    idx = lines.index("event: project-update")
    payload = _json.loads(lines[idx + 1].removeprefix("data: "))
    assert payload["entity"] == "task"
    assert payload["type"] == "created"
    assert payload["project_id"] == test_project.id

    reader.cancel()
