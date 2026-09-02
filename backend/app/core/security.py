from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 登录时序侧信道缓解用：用户不存在时对服务端执行一次等价 bcrypt 校验，
# 使"用户不存在"与"密码错误"的响应耗时一致（内容为随机密钥的密文，不可反推）。
_DUMMY_HASH = pwd_context.hash("timing-side-channel-mitigation-dummy")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, user_id: int) -> str:
    """签发 JWT。sub=user_id（稳定标识，不受改名影响），username 供兼容层还原。"""
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(user_id), "username": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> str | None:
    """校验 JWT 并返回用户名；失败返回 None。

    兼容两代 token：新版读 username 字段（sub 为 user_id），旧版直接用 sub（用户名）。
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("username") or payload.get("sub")
    except jwt.PyJWTError:
        return None


def create_sse_ticket(subject: str, user_id: int) -> str:
    """签发 SSE 连接用的短期 ticket（EventSource 无法携带 Authorization 头）。

    typ=sse 用于与登录 JWT 区分；有效期短（默认 30s），仅用于 /events/stream 认证。
    """
    expire = datetime.now(UTC) + timedelta(seconds=settings.sse_ticket_expire_seconds)
    payload = {"sub": str(user_id), "username": subject, "typ": "sse", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_sse_ticket(token: str) -> str | None:
    """校验 SSE ticket 并返回用户名，失败返回 None（兼容旧版 sub=用户名）。"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("typ") != "sse":
            return None
        return payload.get("username") or payload.get("sub")
    except jwt.PyJWTError:
        return None
