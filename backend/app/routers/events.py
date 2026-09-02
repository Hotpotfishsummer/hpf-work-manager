import asyncio
import json

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from app.core.events import subscribe, subscribe_global, unsubscribe, unsubscribe_global
from app.core.ratelimit import limiter
from app.core.security import create_sse_ticket, decode_sse_ticket, decode_token
from app.deps import CurrentUser, DbDep, _user_from_username
from app.models import Project, User
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
    return {"ticket": create_sse_ticket(user.username, user.id)}


@router.get("/events/stream")
async def event_stream(
    request: Request,
    project_id: int | None = Query(default=None, description="订阅的项目 ID；省略则订阅全部有权限项目的全局流"),
    ticket: str | None = Query(default=None, description="POST /events/ticket 换取的短期 ticket"),
    authorization: str | None = Header(default=None),
    db: DbDep = None,
):
    """SSE 事件流：订阅指定项目（或全局）的变更事件，前端实时刷新。

    认证优先级：Authorization 头（JWT）> ?ticket= 短期 ticket。
    全局流仅转发该用户拥有的项目事件，不泄露他人 project_id。

    注意：认证在端点内手动校验而非 Depends(OptionalUser)——slowapi 包装下
    该依赖与 sse_starlette 的签名解析冲突，无凭证请求会被误判 422 而非 401；
    SSE 为长连接天然低频，限流由 nginx limit_req 兜底。
    """
    # 手动认证：优先 JWT header，次之 ticket
    user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        username = decode_token(token)
        if username:
            user = await _user_from_username(db, username)
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

    if project_id is not None:
        await _get_owned_project(db, user, project_id)
        owned_ids: set[int] | None = None
    else:
        owned_ids = await _owned_project_ids(db, user)

    queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    async def subscribe_and_stream():
        if project_id is not None:
            await subscribe(project_id, queue)
        else:
            await subscribe_global(queue)
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL)
                    if not event_allowed(message, owned_ids):
                        continue  # 他人项目事件：静默丢弃，不泄露存在性
                    yield {"event": "project-update", "data": message}
                except TimeoutError:
                    # 心跳，保持连接
                    yield {"event": "ping", "data": "keepalive"}
        finally:
            if project_id is not None:
                await unsubscribe(project_id, queue)
            else:
                await unsubscribe_global(queue)

    return EventSourceResponse(subscribe_and_stream())


async def _owned_project_ids(db, user: User) -> set[int]:
    rows = (await db.execute(select(Project.id).where(Project.owner_id == user.id))).all()
    return {pid for (pid,) in rows}


def event_allowed(message: str, owned_ids: set[int] | None) -> bool:
    """全局流事件过滤：owned_ids=None 表示已按项目订阅（无需过滤）。"""
    if owned_ids is None:
        return True
    try:
        payload = json.loads(message)
    except (ValueError, TypeError):
        return False
    return payload.get("project_id") in owned_ids
