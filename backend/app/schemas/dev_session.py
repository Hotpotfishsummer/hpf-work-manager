from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DevSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class DevSessionEnd(BaseModel):
    summary: str | None = None


class DevSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str | None
    started_at: datetime
    ended_at: datetime | None
    summary: str | None
    author: str
    created_at: datetime
    # 派生：该会话下的记录条数（由接口填充，非 ORM 字段）
    log_count: int = 0
