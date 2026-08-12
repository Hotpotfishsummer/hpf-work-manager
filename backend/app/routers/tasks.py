from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.deps import CurrentUser, DbDep
from app.models import Project, Task, TaskDependency
from app.routers.projects import _get_owned_project
from app.schemas import TaskBulkUpdate, TaskCreate, TaskOut, TaskUpdate
from app.services.tasks import apply_task_update, to_out
from app.utils.time import utcnow

router = APIRouter(tags=["tasks"])


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
):
    await _get_owned_project(db, user, project_id)
    stmt = select(Task).where(Task.project_id == project_id)
    if status_filter:
        stmt = stmt.where(Task.status == status_filter)
    tasks = (await db.execute(stmt.order_by(Task.created_at.desc()))).scalars().all()
    outs = [to_out(t) for t in tasks]
    if overdue:
        outs = [t for t in outs if t.overdue]
    return outs


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    project_id: int, payload: TaskCreate, user: CurrentUser, db: DbDep
):
    await _get_owned_project(db, user, project_id)

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
    return to_out(task)


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: int, user: CurrentUser, db: DbDep):
    return to_out(await _get_task(db, user, task_id))


@router.put("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: int, payload: TaskUpdate, user: CurrentUser, db: DbDep
):
    task = await _get_task(db, user, task_id)
    data = payload.model_dump(exclude_unset=True)
    apply_task_update(task, data)
    await db.commit()
    await db.refresh(task)
    return to_out(task)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, user: CurrentUser, db: DbDep):
    task = await _get_task(db, user, task_id)
    await db.delete(task)
    await db.commit()


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
    for task in tasks:
        apply_task_update(task, data)
    await db.commit()


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
async def add_dependency(task_id: int, depends_on: dict, user: CurrentUser, db: DbDep):
    dep_id = depends_on.get("depends_on_task_id")
    if not dep_id:
        raise HTTPException(status_code=422, detail="缺少 depends_on_task_id")
    task = await _get_task(db, user, task_id)
    await _get_task(db, user, dep_id)
    if task_id == dep_id:
        raise HTTPException(status_code=400, detail="任务不能依赖自身")

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


@router.delete("/tasks/{task_id}/dependencies", status_code=status.HTTP_204_NO_CONTENT)
async def remove_dependency(task_id: int, depends_on: dict, user: CurrentUser, db: DbDep):
    dep_id = depends_on.get("depends_on_task_id")
    if not dep_id:
        raise HTTPException(status_code=422, detail="缺少 depends_on_task_id")
    await _get_task(db, user, task_id)
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
