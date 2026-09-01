"""进程内事件总线：按项目维度广播变更事件，供 SSE 推送。

单实例部署足够；若未来多副本，需替换为 Redis Pub/Sub。
"""

import asyncio
import json
from collections import defaultdict
from datetime import UTC, datetime

_queues: dict[str, set[asyncio.Queue]] = defaultdict(set)
_lock = asyncio.Lock()


def _topic(project_id: int) -> str:
    return f"project:{project_id}"


async def subscribe(project_id: int, queue: asyncio.Queue) -> None:
    async with _lock:
        _queues[_topic(project_id)].add(queue)


async def unsubscribe(project_id: int, queue: asyncio.Queue) -> None:
    async with _lock:
        _queues[_topic(project_id)].discard(queue)


async def publish(project_id: int, event_type: str, entity: str, entity_id: int) -> None:
    """发布一条变更事件到指定项目主题。"""
    message = json.dumps(
        {
            "type": event_type,
            "entity": entity,
            "entity_id": entity_id,
            "project_id": project_id,
            "ts": datetime.now(UTC).isoformat(),
        }
    )
    async with _lock:
        queues = list(_queues[_topic(project_id)])
    for q in queues:
        # 队列满则丢弃最旧事件，避免阻塞业务写路径
        if q.full():
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            pass