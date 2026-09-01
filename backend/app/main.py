from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import RequestLoggingMiddleware, setup_logging
from app.core.ratelimit import limiter
from app.database import get_db
from app.routers import (
    auth,
    dev_logs,
    events,
    keys,
    milestones,
    projects,
    search,
    stats,
    tasks,
)

setup_logging()

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
    version="0.2.0",
    lifespan=lifespan,
)

# 请求日志：JSON 结构化输出，含 request_id / latency_ms（先于 CORS 注册以覆盖全部请求）
app.add_middleware(RequestLoggingMiddleware)

# slowapi 装饰器从 app.state.limiter 取实例
app.state.limiter = limiter

# CORS：生产走 nginx 同源反代；dev 走 vite proxy；白名单兜底
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- 全局异常归一：DB 约束/数据错误转 4xx，不泄露堆栈 ----
def _err(status: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail, "code": code})


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return _err(409, "CONFLICT", "数据冲突：唯一约束或关联校验失败")


@app.exception_handler(DataError)
async def data_error_handler(request: Request, exc: DataError):
    return _err(422, "VALIDATION_ERROR", "数据格式或长度不符合要求")


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return _err(422, "VALIDATION_ERROR", str(exc) or "参数不合法")


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "请求过于频繁，请稍后再试", "code": "RATE_LIMIT_EXCEEDED"},
        headers={"Retry-After": str(getattr(exc, "retry_after", 60) or 60)},
    )


API_PREFIX = "/api"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(keys.router, prefix=API_PREFIX)
app.include_router(search.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(milestones.router, prefix=API_PREFIX)
app.include_router(tasks.router, prefix=API_PREFIX)
app.include_router(stats.router, prefix=API_PREFIX)
app.include_router(dev_logs.router, prefix=API_PREFIX)
app.include_router(events.router, prefix=API_PREFIX)


@app.get("/api/health", tags=["health"])
async def health(db: AsyncSession = Depends(get_db)):
    # DB 感知探活：SELECT 1 失败返回 503，供 compose healthcheck 使用
    from sqlalchemy.exc import SQLAlchemyError

    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "db": "unavailable", "code": "SERVICE_UNAVAILABLE"},
        )


# ---- MCP 端点挂载 ----
if settings.mcp_enabled:
    from app.mcp_auth import MCPAuthMiddleware
    from app.mcp_server import get_mcp_app

    # 认证中间件仅作用于 MCP 应用，不污染全局 REST
    app.mount(settings.mcp_path, MCPAuthMiddleware(get_mcp_app()))
