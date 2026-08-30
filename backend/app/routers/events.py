import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sse_starlette.sse import EventSourceResponse

from app.core.events import subscribe, unsubscribe
from app.core.ratelimit import limiter
from app.core.security import create_sse_ticket, decode_sse_ticket
from app.database import get_db
from app.deps import CurrentUser, DbDep, OptionalUser, _user_from_username
from app.models import User
from app.routers.projects import _get_owned_project

router = APIRouter(tags=["events"])

HEARTBEAT_INTERVAL = 25  # 秒，低于常见代理超时下限


@router.post("/events/ticket")
@limiter.limit("60/minute")
async def create_ticket(request: Request, user: CurrentUser) -> dict:
    """换取 SSE 连接用的短期 ticket。

    EventSource 无法携带 Authorization 头，故先以 JWT 换取 30s 一次性 ticket，
    再以 ?ticket= 形式传入 /events/stream；避免长期令牌进入 URL。
    """
    return {"ticket": create_sse_ticket(user.username)}


@router.get("/events/stream")
@limiter.limit("60/minute")
async def event_stream(
    request: Request,
    project_id: int = Query(..., description="订阅的项目 ID"),
    ticket: str | None = Query(default=None, description="POST /events/ticket 换取的短期 ticket"),
    user: Annotated[User | None, Depends(OptionalUser)] = None,
    db: Annotated[object, Depends(get_db)] = None,  # noqa: B008
):
    """SSE 事件流：订阅指定项目的变更事件，前端实时刷新。

    认证优先级：Authorization 头（JWT）> ?ticket= 短期 ticket。
    """
    # ticket 认证（EventSource 无法携带 header 时使用）
    if user is None and ticket:
        username = decode_sse_ticket(ticket)
        if username:
            user = await _user_from_username(db, username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证",
            headers={"WWW-Authenticate": "Bearer"},
        )

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
