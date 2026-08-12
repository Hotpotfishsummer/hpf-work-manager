from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ApiKeyOut(BaseModel):
    id: int
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyCreated(BaseModel):
    """创建成功响应：明钥仅此一次返回。"""

    id: int
    name: str
    key: str
    prefix: str


class ApiKeyIssueToken(BaseModel):
    """用 API Key 换短期 JWT（供工具以 JWT 调用既有接口）。"""

    access_token: str