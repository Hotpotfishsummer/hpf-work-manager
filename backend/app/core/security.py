from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str) -> str:
    """签发 JWT，subject 为用户名。"""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> str | None:
    """校验 JWT 并返回 subject（用户名），失败返回 None。"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def create_sse_ticket(subject: str) -> str:
    """签发 SSE 连接用的短期 ticket（EventSource 无法携带 Authorization 头）。

    typ=sse 用于与登录 JWT 区分；有效期短（默认 30s），仅用于 /events/stream 认证。
    """
    expire = datetime.now(timezone.utc) + timedelta(seconds=settings.sse_ticket_expire_seconds)
    payload = {"sub": subject, "typ": "sse", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_sse_ticket(token: str) -> str | None:
    """校验 SSE ticket 并返回 subject（用户名），失败返回 None。"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("typ") != "sse":
            return None
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
