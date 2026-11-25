"""MCP Streamable HTTP 端点的认证中间件。

两种模式，由 `AUTH_REQUIRED` 环境变量控制（与 REST 层保持一致）：

- `AUTH_REQUIRED=false`（默认，Tailscale / Localhost 内网部署）：
  未传或无法识别凭证时回退到 admin 用户，AI 工具零配置即可接入。
  携带有效 JWT / API Key 时仍按该凭证识别用户。
- `AUTH_REQUIRED=true`（对外暴露 / 公网反代）：
  必须携带有效凭证，否则以 401 拒绝握手，避免 MCP 成为无鉴权后门。
"""

from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

import app.mcp_auth as mcp_auth_module
from app.config import settings
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

        if not username:
            if settings.auth_required:
                # 强制鉴权模式：拒绝匿名 MCP 握手
                return JSONResponse(
                    {"error": "unauthorized", "detail": "需要有效的 API Key 或 JWT"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # 内网免鉴权模式：回退到 admin
            username = "admin"

        ctx_token = current_username.set(username)
        try:
            return await call_next(request)
        finally:
            current_username.reset(ctx_token)
