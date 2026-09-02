from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import case, func, or_, select

from app.core.events import publish
from app.deps import CurrentUser, DbDep
from app.models import Milestone, Project, Task, TaskDependency
from app.routers.projects import _get_owned_project
from app.schemas import (
    TaskBulkUpdate,
    TaskCreate,
    TaskDependencyCreate,
    TaskOut,
    TaskUpdate,
)
from app.services.tasks import (
    apply_task_update,
    ensure_no_cycle,
    get_project_depends_map,
    get_task_depends,
    to_out,
)
from app.utils.time import display_today, utcnow

router = APIRouter(tags=["tasks"])


async def _ensure_milestone_in_project(db: DbDep, project_id: int, milestone_id: int | None):
    """校验里程碑归属：不存在或跨项目一律 400。"""
    if milestone_id is None:
        return
    ms = await db.get(Milestone, milestone_id)
    if ms is None or ms.project_id != project_id:
        raise HTTPException(status_code=400, detail="里程碑不存在或不属于该项目")


async def _get_task(db: DbDep, user: CurrentUser, task_id: int) -> Task:
    task = (
        await db.execute(
            select(Task)
            .join(Project, Task.project_id == Project.id)
            .where(Task.id == task_id, Project.owner_id == user.id)
        )
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
async def list_tasks(
    project_id: int,
    user: CurrentUser,
    db: DbDep,
    status_filter: str | None = Query(default=None, alias="status"),
    overdue: bool | None = Query(default=None),
    priority: str | None = Query(default=None, description="low/medium/high"),
    milestone_id: int | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100, description="按名称/描述模糊搜索"),
    sort: str | None = Query(default=None, description="created_desc / due_asc / due_desc / priority_desc"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    await _get_owned_project(db, user, project_id)
    stmt = select(Task).where(Task.project_id == project_id)
    if status_filter:
        stmt = stmt.where(Task.status == status_filter)
    if priority:
        stmt = stmt.where(Task.priority == priority)
    if milestone_id is not None:
        stmt = stmt.where(Task.milestone_id == milestone_id)
    if search:
        pat = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(func.lower(Task.name).like(pat), func.lower(Task.description).like(pat))
        )
    # 逾期为实时派生字段，SQL 级过滤保证分页语义正确
    if overdue is True:
        stmt = stmt.where(
            Task.status != "done", Task.due_date.is_not(None), Task.due_date < display_today()
        )
    # 排序
    if sort == "due_asc":
        stmt = stmt.order_by(Task.due_date.asc().nulls_last())
    elif sort == "due_desc":
        stmt = stmt.order_by(Task.due_date.desc().nulls_last())
    elif sort == "priority_desc":
        # high > medium > low：用 CASE WHEN 排序
        stmt = stmt.order_by(
            case(
                (Task.priority == "high", 0),
                (Task.priority == "medium", 1),
                (Task.priority == "low", 2),
                else_=3,
            ),
            Task.created_at.desc(),
        )
    else:
        stmt = stmt.order_by(Task.created_at.desc())
    tasks = (await db.execute(stmt.offset(offset).limit(limit))).scalars().all()
    depends_map = await get_project_depends_map(db, project_id)
    return [to_out(t, depends_map.get(t.id, [])) for t in tasks]


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    project_id: int, payload: TaskCreate, user: CurrentUser, db: DbDep
):
    await _get_owned_project(db, user, project_id)
    await _ensure_milestone_in_project(db, project_id, payload.milestone_id)

    data = payload.model_dump()
    status_ = data.get("status", "todo")
    # 状态流转规则：done → progress=100 + completed_at；否则 completed_at=None
    if status_ == "done":
        data["progress"] = 100
        data["completed_at"] = utcnow()
    else:
        data["completed_at"] = None

    task = Task(project_id=project_id, **data)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    await publish(project_id, "created", "task", task.id)
    return to_out(task)


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, user: CurrentUser, db: DbDep):
    task = await _get_task(db, user, task_id)
    return to_out(task, await get_task_depends(db, task.id))


@router.put("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int, payload: TaskUpdate, user: CurrentUser, db: DbDep
):
    task = await _get_task(db, user, task_id)
    data = payload.model_dump(exclude_unset=True)
    if "milestone_id" in data:
        await _ensure_milestone_in_project(db, task.project_id, data["milestone_id"])
    apply_task_update(task, data)
    await db.commit()
    await db.refresh(task)
    await publish(task.project_id, "updated", "task", task.id)
    return to_out(task, await get_task_depends(db, task.id))


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, user: CurrentUser, db: DbDep):
    task = await _get_task(db, user, task_id)
    pid, tid = task.project_id, task.id
    await db.delete(task)
    await db.commit()
    await publish(pid, "deleted", "task", tid)


@router.post("/tasks/bulk", status_code=status.HTTP_204_NO_CONTENT)
async def bulk_update(payload: TaskBulkUpdate, user: CurrentUser, db: DbDep):
    tasks = (
        (
            await db.execute(
                select(Task)
                .join(Project, Task.project_id == Project.id)
                .where(Task.id.in_(payload.ids), Project.owner_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    data = payload.data.model_dump(exclude_unset=True)
    if "milestone_id" in data:
        for task in tasks:
            await _ensure_milestone_in_project(db, task.project_id, data["milestone_id"])
    for task in tasks:
        apply_task_update(task, data)
    await db.commit()
    for task in tasks:
        await publish(task.project_id, "updated", "task", task.id)


# ---- 依赖关系管理 ----

@router.get("/tasks/{task_id}/dependencies", response_model=list[int])
async def list_dependencies(task_id: int, user: CurrentUser, db: DbDep):
    await _get_task(db, user, task_id)
    rows = (
        await db.execute(
            select(TaskDependency.depends_on_task_id).where(
                TaskDependency.task_id == task_id
            )
        )
    ).scalars().all()
    return list(rows)


@router.post("/tasks/{task_id}/dependencies", status_code=status.HTTP_204_NO_CONTENT)
async def add_dependency(
    task_id: int, payload: TaskDependencyCreate, user: CurrentUser, db: DbDep
):
    dep_id = payload.depends_on_task_id
    task = await _get_task(db, user, task_id)
    await _get_task(db, user, dep_id)
    try:
        await ensure_no_cycle(db, task_id, dep_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    exists = (
        await db.execute(
            select(TaskDependency).where(
                TaskDependency.task_id == task_id,
                TaskDependency.depends_on_task_id == dep_id,
            )
        )
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="依赖关系已存在")

    db.add(TaskDependency(task_id=task_id, depends_on_task_id=dep_id))
    await db.commit()
    await publish(task.project_id, "updated", "task", task_id)


@router.delete("/tasks/{task_id}/dependencies", status_code=status.HTTP_204_NO_CONTENT)
async def remove_dependency(
    task_id: int, payload: TaskDependencyCreate, user: CurrentUser, db: DbDep
):
    dep_id = payload.depends_on_task_id
    task = await _get_task(db, user, task_id)
    row = (
        await db.execute(
            select(TaskDependency).where(
                TaskDependency.task_id == task_id,
                TaskDependency.depends_on_task_id == dep_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="依赖关系不存在")
    await db.delete(row)
    await db.commit()
    await publish(task.project_id, "updated", "task", task_id)
