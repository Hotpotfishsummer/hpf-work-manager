from datetime import date

from fastapi import APIRouter, HTTPException

from app.deps import CurrentUser, DbDep
from app.models import Project
from app.routers.projects import _get_owned_project
from app.schemas import BurndownPoint, DashboardOverview, GanttData, ProjectStats
from app.services.stats import (
    get_burndown,
    get_gantt_data,
    get_overview,
    get_project_stats,
)

router = APIRouter(tags=["stats"])


def _project_range(project: Project) -> tuple[date, date]:
    """项目起止日期，缺省回退到今日，保证区间非空。"""
    start = project.start_date or date.today()
    end = project.end_date or date.today()
    if start > end:
        raise HTTPException(status_code=400, detail="项目开始日期晚于截止日期")
    return start, end


@router.get("/projects/{project_id}/stats", response_model=ProjectStats)
async def project_stats(project_id: int, user: CurrentUser, db: DbDep):
    await _get_owned_project(db, user, project_id)
    return await get_project_stats(db, project_id)


@router.get("/projects/{project_id}/burndown", response_model=list[BurndownPoint])
async def project_burndown(project_id: int, user: CurrentUser, db: DbDep):
    project = await _get_owned_project(db, user, project_id)
    start, end = _project_range(project)
    return await get_burndown(db, project_id, start, end)


@router.get("/projects/{project_id}/gantt", response_model=GanttData)
async def project_gantt(project_id: int, user: CurrentUser, db: DbDep):
    project = await _get_owned_project(db, user, project_id)
    start, end = _project_range(project)
    return await get_gantt_data(db, project_id, start, end)


@router.get("/overview", response_model=DashboardOverview)
async def overview(user: CurrentUser, db: DbDep):
    return await get_overview(db, user.id)
