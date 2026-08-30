from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.deps import CurrentUser, DbDep
from app.models import Milestone, Project, Task
from app.routers.projects import _get_owned_project
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search(
    user: CurrentUser,
    db: DbDep,
    q: str = Query(..., min_length=2, description="搜索关键词，至少 2 字符"),
    project_id: int | None = Query(default=None, description="可选：限定项目范围"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """全局搜索：项目、任务、里程碑。要求 q 长度 >= 2。"""
    # Validate project ownership if project_id provided
    if project_id is not None:
        await _get_owned_project(db, user, project_id)

    # Build base conditions
    project_cond = Project.owner_id == user.id
    if project_id is not None:
        project_cond = Project.id == project_id

    # Search projects
    project_stmt = (
        select(Project)
        .where(project_cond, Project.name.ilike(f"%{q}%"))
        .order_by(Project.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    projects = (await db.execute(project_stmt)).scalars().all()

    # Search tasks
    task_cond = Task.project_id.in_(
        select(Project.id).where(project_cond)
    ) if project_id is None else Task.project_id == project_id
    task_stmt = (
        select(Task)
        .where(task_cond, Task.name.ilike(f"%{q}%"))
        .order_by(Task.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    tasks = (await db.execute(task_stmt)).scalars().all()

    # Search milestones
    ms_cond = Milestone.project_id.in_(
        select(Project.id).where(project_cond)
    ) if project_id is None else Milestone.project_id == project_id
    ms_stmt = (
        select(Milestone)
        .where(ms_cond, Milestone.name.ilike(f"%{q}%"))
        .order_by(Milestone.due_date.asc().nulls_last())
        .limit(limit)
        .offset(offset)
    )
    milestones = (await db.execute(ms_stmt)).scalars().all()

    # Build results
    items: list[SearchResultItem] = []

    for p in projects:
        items.append(
            SearchResultItem(
                type="project",
                id=p.id,
                name=p.name,
                description=p.description,
                project_id=p.id,
                project_name=p.name,
                status=p.status,
            )
        )

    for t in tasks:
        items.append(
            SearchResultItem(
                type="task",
                id=t.id,
                name=t.name,
                description=t.description,
                project_id=t.project_id,
                project_name=None,  # Could join if needed
                status=t.status,
                due_date=t.due_date.isoformat() if t.due_date else None,
            )
        )

    for m in milestones:
        items.append(
            SearchResultItem(
                type="milestone",
                id=m.id,
                name=m.name,
                description=None,
                project_id=m.project_id,
                project_name=None,
                status=m.status,
                due_date=m.due_date.isoformat() if m.due_date else None,
            )
        )

    # Total count (approximate: sum of individual counts)
    total = len(items)

    return SearchResponse(items=items, total=total)