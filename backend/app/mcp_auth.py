"""MCP Streamable HTTP 端点的认证中间件。

在 MCP 传输层拦截请求，校验 Bearer API Key，将用户名写入 contextvar，
供 MCP tool 处理器读取。未认证返回 401。
"""

from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

import app.mcp_auth as mcp_auth_module
from app.core.apikey import validate_api_key
from app.core.security import decode_token
from app.mcp_server import current_username
from app.models import ApiKey, User


class MCPAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization", "")
        token = None
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()

        username = None
        if token:
            # 1) JWT
            username = decode_token(token)
            if username is None:
                # 2) API Key
                key_hash = validate_api_key(token)
                if key_hash is not None:
                    async with mcp_auth_module.AsyncSessionLocal() as db:
                        row = (
                            await db.execute(
                                select(ApiKey).where(
                                    ApiKey.key_hash == key_hash,
                                    ApiKey.revoked_at.is_(None),
                                )
                            )
                        ).scalar_one_or_none()
                        if row is not None:
                            u = (
                                await db.execute(
                                    select(User).where(User.id == row.user_id)
                                )
                            ).scalar_one_or_none()
                            username = u.username if u else None

        if username is None:
            return JSONResponse(
                {"detail": "未认证：请提供有效的 API Key 或 JWT"},
                status_code=401,
            )

        token = current_username.set(username)
        try:
            return await call_next(request)
        finally:
            current_username.reset(token)