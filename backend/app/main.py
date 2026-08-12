from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, events, keys, milestones, projects, stats, tasks

# ---- MCP Server（AI 工具接入）----
# 在宿主 App lifespan 中启动 MCP 会话管理器（挂载子应用不会自动触发其 lifespan）
_mcp_session_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mcp_session_manager
    mcp_cm = None
    if settings.mcp_enabled:
        from app.mcp_server import get_session_manager

        _mcp_session_manager = get_session_manager()
        mcp_cm = _mcp_session_manager.run()
        await mcp_cm.__aenter__()
    try:
        yield
    finally:
        if mcp_cm is not None:
            await mcp_cm.__aexit__(None, None, None)


app = FastAPI(
    title="HPF Work Manager API",
    description="任务/项目管理与进度追踪 API（FastAPI + PostgreSQL）",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS：生产走 nginx 同源反代；dev 走 vite proxy；白名单兜底
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(keys.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(milestones.router, prefix=API_PREFIX)
app.include_router(tasks.router, prefix=API_PREFIX)
app.include_router(stats.router, prefix=API_PREFIX)
app.include_router(events.router, prefix=API_PREFIX)


@app.get("/api/health", tags=["health"])
async def health():
    return {"status": "ok"}


# ---- MCP 端点挂载 ----
if settings.mcp_enabled:
    from app.mcp_auth import MCPAuthMiddleware
    from app.mcp_server import get_mcp_app

    # 认证中间件仅作用于 MCP 应用，不污染全局 REST
    app.mount(settings.mcp_path, MCPAuthMiddleware(get_mcp_app()))