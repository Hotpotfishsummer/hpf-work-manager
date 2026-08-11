from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, milestones, projects, stats, tasks

app = FastAPI(
    title="HPF Work Manager API",
    description="任务/项目管理与进度追踪 API（FastAPI + PostgreSQL）",
    version="0.1.0",
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
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(milestones.router, prefix=API_PREFIX)
app.include_router(tasks.router, prefix=API_PREFIX)
app.include_router(stats.router, prefix=API_PREFIX)


@app.get("/api/health", tags=["health"])
async def health():
    return {"status": "ok"}
