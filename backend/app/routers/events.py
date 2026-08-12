import asyncio

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from sse_starlette.sse import EventSourceResponse

from app.core.events import subscribe, unsubscribe
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.routers.projects import _get_owned_project

router = APIRouter(tags=["events"])

HEARTBEAT_INTERVAL = 25  # 秒，低于常见代理超时下限


@router.get("/events/stream")
async def event_stream(
    project_id: int = Query(..., description="订阅的项目 ID"),
    user: Annotated[User, Depends(get_current_user)] = None,  # noqa: B008
    db: Annotated[object, Depends(get_db)] = None,  # noqa: B008
):
    """SSE 事件流：订阅指定项目的变更事件，前端实时刷新。"""
    await _get_owned_project(db, user, project_id)

    queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    async def subscribe_and_stream():
        await subscribe(project_id, queue)
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL)
                    yield {"event": "project-update", "data": message}
                except asyncio.TimeoutError:
                    # 心跳，保持连接
                    yield {"event": "ping", "data": "keepalive"}
        finally:
            await unsubscribe(project_id, queue)

    return EventSourceResponse(subscribe_and_stream())