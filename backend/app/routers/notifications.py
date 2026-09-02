"""通知已读水位端点（P4-4 通知中心服务端化）。

前端 localStorage 水位跨设备/清缓存即丢；此端点以服务端为准：
- GET  /notifications/watermark  读取
- PUT  /notifications/watermark  推进（body: {"last_read_at": "<ISO8601 UTC>"}）
"""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.deps import CurrentUser, DbDep
from app.models import NotificationWatermark

router = APIRouter(tags=["notifications"])


class WatermarkOut(BaseModel):
    last_read_at: datetime | None


class WatermarkUpdate(BaseModel):
    last_read_at: datetime = Field(description="已读水位（ISO8601，UTC）")


@router.get("/notifications/watermark", response_model=WatermarkOut)
async def get_watermark(user: CurrentUser, db: DbDep):
    row = await db.get(NotificationWatermark, user.id)
    last_read_at = row.last_read_at if row else None
    if last_read_at is not None and last_read_at.tzinfo is None:
        last_read_at = last_read_at.replace(tzinfo=UTC)  # SQLite 返回 naive，按 UTC 解释
    return WatermarkOut(last_read_at=last_read_at)


@router.put("/notifications/watermark", response_model=WatermarkOut)
async def put_watermark(payload: WatermarkUpdate, user: CurrentUser, db: DbDep):
    # 水位只允许前推，不允许回退（防多设备旧时间戳覆盖新状态）
    incoming = payload.last_read_at
    if incoming.tzinfo is None:
        incoming = incoming.replace(tzinfo=UTC)
    row = await db.get(NotificationWatermark, user.id)
    if row is None:
        row = NotificationWatermark(user_id=user.id, last_read_at=incoming)
        db.add(row)
    else:
        current = row.last_read_at
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)  # SQLite naive → UTC
        if incoming > current:
            row.last_read_at = incoming
    await db.commit()
    await db.refresh(row)
    stored = row.last_read_at
    if stored.tzinfo is None:
        stored = stored.replace(tzinfo=UTC)
    return WatermarkOut(last_read_at=stored)
