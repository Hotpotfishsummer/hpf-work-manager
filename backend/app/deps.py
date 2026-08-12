from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.apikey import validate_api_key
from app.core.security import decode_token
from app.database import get_db
from app.models import ApiKey, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
bearer_scheme = HTTPBearer(auto_error=False)

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _user_from_username(db: AsyncSession, username: str) -> User | None:
    return (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()


async def get_optional_user(
    db: DbDep,
    jwt_creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User | None:
    """优先解析 JWT，其次解析 API Key（Bearer 头携带）。两者都无效返回 None。"""
    if jwt_creds is None:
        return None
    token = jwt_creds.credentials

    # 1) 尝试 JWT
    username = decode_token(token)
    if username is not None:
        return await _user_from_username(db, username)

    # 2) 尝试 API Key
    key_hash = validate_api_key(token)
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
    return await _user_from_username(db, row.user_id)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbDep,
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录状态无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    username = decode_token(token)
    if username is None:
        raise credentials_error
    user = (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if user is None:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
