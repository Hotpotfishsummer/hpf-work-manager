from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.apikey import validate_api_key
from app.core.security import decode_token
from app.database import get_db
from app.models import ApiKey, User

# auto_error=False：关闭鉴权模式下允许无凭证；开启时由 get_current_user 统一抛 401
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _user_from_username(db: AsyncSession, username: str) -> User | None:
    return (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()


async def _user_from_api_key(db: AsyncSession, raw_key: str) -> User | None:
    """按 API Key 查用户；格式非法、已撤销或用户不存在均返回 None。"""
    key_hash = validate_api_key(raw_key)
    if key_hash is None:
        return None
    row = (
        await db.execute(
            select(ApiKey).where(
                ApiKey.key_hash == key_hash,
                ApiKey.revoked_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return await db.get(User, row.user_id)


async def get_optional_user(
    db: DbDep,
    jwt_creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User | None:
    """优先解析 JWT，其次解析 API Key；两者都无效返回 None（不抛错）。"""
    if jwt_creds is None:
        return None
    token = jwt_creds.credentials

    username = decode_token(token)
    if username is not None:
        return await _user_from_username(db, username)

    return await _user_from_api_key(db, token)


async def get_current_user(
    db: DbDep,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User:
    """解析当前用户。

    两种模式，由 `AUTH_REQUIRED` 环境变量控制：

    - `AUTH_REQUIRED=false`（默认，Tailscale / Localhost 内网部署）：
      未携带或携带无效凭证时回退到 admin 用户，前端无需登录。
      携带有效 JWT / API Key 时仍按该凭证识别用户，便于多用户与审计。
    - `AUTH_REQUIRED=true`（对外暴露 / 公网反代）：
      必须携带有效 JWT 或 API Key，否则 401。
    """
    if token:
        username = decode_token(token)
        if username is not None:
            user = await _user_from_username(db, username)
            if user is not None:
                return user
        else:
            # 不是 JWT，再试 API Key
            user = await _user_from_api_key(db, token)
            if user is not None:
                return user

    if settings.auth_required:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 内网免鉴权模式：回退到 admin（不存在则按需创建）
    user = (await db.execute(select(User).order_by(User.id))).scalars().first()
    if user is None:
        user = User(username="admin", email="admin@example.com", hashed_password="nopassword")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
