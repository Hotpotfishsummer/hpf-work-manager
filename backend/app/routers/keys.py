from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.apikey import generate_api_key, validate_api_key
from app.core.ratelimit import limiter
from app.core.security import create_access_token
from app.database import AsyncSessionLocal
from app.deps import CurrentUser, DbDep
from app.models import ApiKey, User
from app.schemas import ApiKeyCreate, ApiKeyCreated, ApiKeyIssueToken, ApiKeyOut

router = APIRouter(prefix="/keys", tags=["api-keys"])


class ExchangeRequest(BaseModel):
    key: str


@router.get("", response_model=list[ApiKeyOut])
async def list_keys(user: CurrentUser, db: DbDep):
    rows = (
        (
            await db.execute(
                select(ApiKey)
                .where(ApiKey.user_id == user.id)
                .order_by(ApiKey.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [ApiKeyOut.model_validate(k) for k in rows]


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_key(payload: ApiKeyCreate, user: CurrentUser, db: DbDep):
    raw, prefix, key_hash = generate_api_key(user.id)
    key = ApiKey(
        user_id=user.id,
        name=payload.name,
        prefix=prefix,
        key_hash=key_hash,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return ApiKeyCreated(id=key.id, name=key.name, key=raw, prefix=key.prefix)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(key_id: int, user: CurrentUser, db: DbDep):
    key = (
        await db.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
        )
    ).scalar_one_or_none()
    if key is None:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    key.revoked_at = datetime.now(UTC)
    await db.commit()


@router.post("/exchange", response_model=ApiKeyIssueToken)
@limiter.limit("5/minute")
async def exchange_for_token(request: Request, payload: ExchangeRequest):
    """用 API Key 换取短期 JWT，供工具以 Bearer JWT 调用既有 /api 接口。

    校验通过后用独立会话查找用户并签发 JWT。
    """
    key_hash = validate_api_key(payload.key)
    if key_hash is None:
        raise HTTPException(status_code=401, detail="无效的 API Key")

    async with AsyncSessionLocal() as db:
        row = (
            await db.execute(
                select(ApiKey).where(
                    ApiKey.key_hash == key_hash,
                    ApiKey.revoked_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=401, detail="无效的 API Key")
        row.last_used_at = datetime.now(UTC)
        await db.commit()
        user = (
            await db.execute(select(User).where(User.id == row.user_id))
        ).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=401, detail="无效的 API Key")
        return ApiKeyIssueToken(access_token=create_access_token(user.username, user.id))