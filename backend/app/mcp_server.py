"""MCP Server：让 AI 编码工具通过 MCP 协议读写项目数据。

- 通过 Streamable HTTP 传输暴露（FastMCP.streamable_http_app()）
- 认证由外层 ASGI 中间件完成，将解析出的用户名写入 contextvar
- 工具复用 services 层与模型，避免业务逻辑分叉
"""

import contextvars
from datetime import date, datetime
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy import select

from app.config import settings
from app.core.events import publish
from app.database import AsyncSessionLocal
from app.models import DevLog, DevSession, Milestone, Project, Task, TaskDependency, User
from app.schemas import (
    DevLogCreate,
    MilestoneCreate,
    ProjectCreate,
    TaskCreate,
)
from app.services.dev_logs import (
    _attach_session,
    _validate_related_tasks,
    apply_log_update,
    get_dev_log_stats as _get_dev_log_stats_service,
    get_dev_report as _get_dev_report_service,
    get_project_state as _get_project_state_service,
    session_to_dict,
    to_dict,
)
from app.services.stats import get_burndown, get_gantt_data, get_project_stats
from app.services.tasks import apply_task_update, to_out
from app.utils.time import utcnow

# 由 ASGI 中间件在每次请求时写入当前认证用户名
current_username: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "mcp_current_username", default=None
)

def _allowed_hosts() -> list[str]:
    """MCP DNS 防重绑定允许的 Host 列表。显式配置优先，否则从 CORS 源推导。"""
    if settings.mcp_allowed_hosts.strip():
        return [h.strip() for h in settings.mcp_allowed_hosts.split(",") if h.strip()]
    hosts = set()
    for raw in settings.cors_origin_list:
        host = urlparse(raw).netloc
        if host:
            hosts.add(host)
    hosts.add("localhost")
    return list(hosts)


mcp = FastMCP(
    "HPF Work Manager",
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=bool(_allowed_hosts()),
        allowed_hosts=_allowed_hosts(),
    ),
    instructions=(
        "HPF 任务/项目管理与进度追踪 MCP 服务。"
        "提供项目、里程碑、任务、依赖与统计数据的读写能力，"
        "AI 工具可在编码过程中自动维护任务状态与进度。"
    ),
)


async def _get_user(db, username: str) -> User:
    user = (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if user is None:
        raise ValueError("当前用户不存在")
    return user


async def _require_project(db, username: str, project_id: int) -> Project:
    user = await _get_user(db, username)
    project = (
        await db.execute(
            select(Project).where(
                Project.id == project_id, Project.owner_id == user.id
            )
        )
    ).scalar_one_or_none()
    if project is None:
        raise ValueError(f"项目 {project_id} 不存在")
    return project


async def _require_task(db, username: str, task_id: int) -> Task:
    user = await _get_user(db, username)
    task = (
        await db.execute(
            select(Task)
            .join(Project, Task.project_id == Project.id)
            .where(Task.id == task_id, Project.owner_id == user.id)
        )
    ).scalar_one_or_none()
    if task is None:
        raise ValueError(f"任务 {task_id} 不存在")
    return task


def _project_dict(p: Project) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "status": p.status,
        "start_date": p.start_date.isoformat() if p.start_date else None,
        "end_date": p.end_date.isoformat() if p.end_date else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _milestone_dict(m: Milestone) -> dict:
    return {
        "id": m.id,
        "project_id": m.project_id,
        "name": m.name,
        "due_date": m.due_date.isoformat() if m.due_date else None,
        "status": m.status,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def _task_dict(t: Task) -> dict:
    return {
        "id": t.id,
        "project_id": t.project_id,
        "milestone_id": t.milestone_id,
        "name": t.name,
        "description": t.description,
        "status": t.status,
        "priority": t.priority,
        "progress": t.progress,
        "start_date": t.start_date.isoformat() if t.start_date else None,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "estimated_hours": t.estimated_hours,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


# ---------- 项目 ----------


@mcp.tool()
async def list_projects() -> list[dict]:
    """列出当前用户的所有项目。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        user = await _get_user(db, username)
        rows = (
            (
                await db.execute(
                    select(Project)
                    .where(Project.owner_id == user.id)
                    .order_by(Project.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        return [_project_dict(p) for p in rows]


@mcp.tool()
async def get_project(project_id: int) -> dict:
    """获取单个项目详情。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        p = await _require_project(db, username, project_id)
        return _project_dict(p)


@mcp.tool()
async def create_project(
    name: str, description: str | None = None,
    start_date: str | None = None, end_date: str | None = None,
) -> dict:
    """创建项目。name 必填；start_date/end_date 为 ISO 日期字符串。"""
    username = _username()
    payload = ProjectCreate(
        name=name,
        description=description,
        start_date=date.fromisoformat(start_date) if start_date else None,
        end_date=date.fromisoformat(end_date) if end_date else None,
    )
    async with AsyncSessionLocal() as db:
        user = await _get_user(db, username)
        project = Project(owner_id=user.id, **payload.model_dump())
        db.add(project)
        await db.commit()
        await db.refresh(project)
        await publish(project.id, "created", "project", project.id)
        return _project_dict(project)


@mcp.tool()
async def update_project(
    project_id: int, name: str | None = None, description: str | None = None,
    status: str | None = None, start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """更新项目字段。仅更新传入的字段。"""
    username = _username()
    updates = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if status is not None:
        if status not in ("active", "archived"):
            raise ValueError("status 必须为 active 或 archived")
        updates["status"] = status
    try:
        if start_date is not None:
            updates["start_date"] = date.fromisoformat(start_date)
        if end_date is not None:
            updates["end_date"] = date.fromisoformat(end_date)
    except ValueError as e:
        raise ValueError(f"日期格式不合法（应为 YYYY-MM-DD）：{e}") from None
    async with AsyncSessionLocal() as db:
        p = await _require_project(db, username, project_id)
        for key, value in updates.items():
            setattr(p, key, value)
        await db.commit()
        await db.refresh(p)
        await publish(p.id, "updated", "project", p.id)
        return _project_dict(p)


@mcp.tool()
async def delete_project(project_id: int) -> str:
    """删除项目及其全部任务、里程碑。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        p = await _require_project(db, username, project_id)
        await db.delete(p)
        await db.commit()
        return f"项目 {project_id} 已删除"


# ---------- 里程碑 ----------


@mcp.tool()
async def list_milestones(project_id: int) -> list[dict]:
    """列出项目的所有里程碑。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        await _require_project(db, username, project_id)
        rows = (
            (
                await db.execute(
                    select(Milestone)
                    .where(Milestone.project_id == project_id)
                    .order_by(Milestone.due_date.asc().nulls_last())
                )
            )
            .scalars()
            .all()
        )
        return [_milestone_dict(m) for m in rows]


@mcp.tool()
async def create_milestone(
    project_id: int, name: str, due_date: str | None = None,
) -> dict:
    """在项目中创建里程碑。project_id 与 name 必填。"""
    username = _username()
    payload = MilestoneCreate(
        name=name,
        due_date=date.fromisoformat(due_date) if due_date else None,
    )
    async with AsyncSessionLocal() as db:
        await _require_project(db, username, project_id)
        ms = Milestone(project_id=project_id, **payload.model_dump())
        db.add(ms)
        await db.commit()
        await db.refresh(ms)
        await publish(project_id, "created", "milestone", ms.id)
        return _milestone_dict(ms)


@mcp.tool()
async def update_milestone(
    milestone_id: int, name: str | None = None, due_date: str | None = None,
    status: str | None = None,
) -> dict:
    """更新里程碑。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        user = await _get_user(db, username)
        ms = (
            await db.execute(
                select(Milestone)
                .join(Project, Milestone.project_id == Project.id)
                .where(Milestone.id == milestone_id, Project.owner_id == user.id)
            )
        ).scalar_one_or_none()
        if ms is None:
            raise ValueError(f"里程碑 {milestone_id} 不存在")
        if name is not None:
            ms.name = name
        try:
            if due_date is not None:
                ms.due_date = date.fromisoformat(due_date)
        except ValueError as e:
            raise ValueError(f"日期格式不合法（应为 YYYY-MM-DD）：{e}") from None
        if status is not None:
            if status not in ("active", "done"):
                raise ValueError("status 必须为 active 或 done")
            ms.status = status
        await db.commit()
        await db.refresh(ms)
        await publish(ms.project_id, "updated", "milestone", ms.id)
        return _milestone_dict(ms)


@mcp.tool()
async def delete_milestone(milestone_id: int) -> str:
    """删除里程碑（其下任务保留，milestone_id 置空）。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        user = await _get_user(db, username)
        ms = (
            await db.execute(
                select(Milestone)
                .join(Project, Milestone.project_id == Project.id)
                .where(Milestone.id == milestone_id, Project.owner_id == user.id)
            )
        ).scalar_one_or_none()
        if ms is None:
            raise ValueError(f"里程碑 {milestone_id} 不存在")
        pid = ms.project_id
        await db.delete(ms)
        await db.commit()
        await publish(pid, "deleted", "milestone", milestone_id)
        return f"里程碑 {milestone_id} 已删除"


# ---------- 任务 ----------


@mcp.tool()
async def list_tasks(
    project_id: int, status: str | None = None, overdue: bool | None = None
) -> list[dict]:
    """列出项目任务。可按 status（todo/in_progress/done）与 overdue 过滤。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        await _require_project(db, username, project_id)
        stmt = select(Task).where(Task.project_id == project_id)
        if status:
            stmt = stmt.where(Task.status == status)
        rows = (
            (await db.execute(stmt.order_by(Task.created_at.desc()))).scalars().all()
        )
        outs = [to_out(t) for t in rows]
        if overdue:
            outs = [t for t in outs if t.overdue]
        return [_task_dict(t) for t in outs]


@mcp.tool()
async def get_task(task_id: int) -> dict:
    """获取单个任务详情。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        task = await _require_task(db, username, task_id)
        return _task_dict(task)


@mcp.tool()
async def create_task(
    project_id: int, name: str, description: str | None = None,
    milestone_id: int | None = None, priority: str = "medium",
    status: str = "todo", progress: int = 0, start_date: str | None = None,
    due_date: str | None = None, estimated_hours: int | None = None,
) -> dict:
    """在项目中创建任务。project_id 与 name 必填。status=done 时自动 progress=100。"""
    username = _username()
    payload = TaskCreate(
        name=name,
        description=description,
        milestone_id=milestone_id,
        priority=priority,
        status=status,
        progress=progress,
        start_date=date.fromisoformat(start_date) if start_date else None,
        due_date=date.fromisoformat(due_date) if due_date else None,
        estimated_hours=estimated_hours,
    )
    async with AsyncSessionLocal() as db:
        await _require_project(db, username, project_id)
        if milestone_id is not None:
            ms = await db.get(Milestone, milestone_id)
            if ms is None or ms.project_id != project_id:
                raise ValueError("里程碑不存在或不属于该项目")
        data = payload.model_dump()
        if data["status"] == "done":
            data["progress"] = 100
            data["completed_at"] = utcnow()
        else:
            data["completed_at"] = None
        task = Task(project_id=project_id, **data)
        db.add(task)
        await db.commit()
        await db.refresh(task)
        await publish(project_id, "created", "task", task.id)
        return _task_dict(task)


@mcp.tool()
async def update_task(
    task_id: int, name: str | None = None, description: str | None = None,
    milestone_id: int | None = None, priority: str | None = None,
    status: str | None = None, progress: int | None = None,
    start_date: str | None = None, due_date: str | None = None,
    estimated_hours: int | None = None,
) -> dict:
    """更新任务。仅更新传入字段；status=done 自动 progress=100。"""
    username = _username()
    updates = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if milestone_id is not None:
        updates["milestone_id"] = milestone_id
    if priority is not None:
        if priority not in ("low", "medium", "high"):
            raise ValueError("priority 必须为 low、medium 或 high")
        updates["priority"] = priority
    if status is not None:
        if status not in ("todo", "in_progress", "done"):
            raise ValueError("status 必须为 todo、in_progress 或 done")
        updates["status"] = status
    if progress is not None:
        updates["progress"] = progress
    try:
        if start_date is not None:
            updates["start_date"] = date.fromisoformat(start_date)
        if due_date is not None:
            updates["due_date"] = date.fromisoformat(due_date)
    except ValueError as e:
        raise ValueError(f"日期格式不合法（应为 YYYY-MM-DD）：{e}") from None
    if estimated_hours is not None:
        updates["estimated_hours"] = estimated_hours
    async with AsyncSessionLocal() as db:
        task = await _require_task(db, username, task_id)
        if "milestone_id" in updates:
            ms = await db.get(Milestone, updates["milestone_id"])
            if ms is None or ms.project_id != task.project_id:
                raise ValueError("里程碑不存在或不属于该项目")
        apply_task_update(task, updates)
        await db.commit()
        await db.refresh(task)
        await publish(task.project_id, "updated", "task", task.id)
        return _task_dict(task)


@mcp.tool()
async def delete_task(task_id: int) -> str:
    """删除任务。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        task = await _require_task(db, username, task_id)
        pid = task.project_id
        await db.delete(task)
        await db.commit()
        await publish(pid, "deleted", "task", task_id)
        return f"任务 {task_id} 已删除"


@mcp.tool()
async def add_task_dependency(task_id: int, depends_on_task_id: int) -> str:
    """为任务添加依赖（前者依赖后者）。"""
    username = _username()
    if task_id == depends_on_task_id:
        raise ValueError("任务不能依赖自身")
    async with AsyncSessionLocal() as db:
        task = await _require_task(db, username, task_id)
        await _require_task(db, username, depends_on_task_id)
        exists = (
            await db.execute(
                select(TaskDependency).where(
                    TaskDependency.task_id == task_id,
                    TaskDependency.depends_on_task_id == depends_on_task_id,
                )
            )
        ).scalar_one_or_none()
        if exists is not None:
            raise ValueError("依赖关系已存在")
        db.add(TaskDependency(task_id=task_id, depends_on_task_id=depends_on_task_id))
        await db.commit()
        await publish(task.project_id, "updated", "task", task_id)
        return f"任务 {task_id} 已依赖任务 {depends_on_task_id}"


@mcp.tool()
async def remove_task_dependency(task_id: int, depends_on_task_id: int) -> str:
    """移除任务依赖。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        task = await _require_task(db, username, task_id)
        row = (
            await db.execute(
                select(TaskDependency).where(
                    TaskDependency.task_id == task_id,
                    TaskDependency.depends_on_task_id == depends_on_task_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise ValueError("依赖关系不存在")
        await db.delete(row)
        await db.commit()
        await publish(task.project_id, "updated", "task", task_id)
        return f"任务 {task_id} 的依赖已移除"


@mcp.tool()
async def list_task_dependencies(task_id: int) -> list[dict]:
    """列出任务的前置依赖（含依赖任务的名称与状态，便于判断是否可开工）。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        task = await _require_task(db, username, task_id)
        rows = (
            (
                await db.execute(
                    select(Task.id, Task.name, Task.status, Task.progress)
                    .join(
                        TaskDependency,
                        TaskDependency.depends_on_task_id == Task.id,
                    )
                    .where(TaskDependency.task_id == task_id)
                    .order_by(Task.id)
                )
            )
            .all()
        )
        return [
            {
                "task_id": task.id,
                "depends_on_task_id": rid,
                "name": name,
                "status": status,
                "progress": progress,
            }
            for rid, name, status, progress in rows
        ]


# ---------- 统计 ----------


@mcp.tool()
async def get_project_stats_mcp(project_id: int) -> dict:
    """获取项目进度统计（总数/完成/进行中/待办/进度%/延期列表）。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        await _require_project(db, username, project_id)
        stats = await get_project_stats(db, project_id)
        return {
            "total_tasks": stats.total_tasks,
            "done_tasks": stats.done_tasks,
            "in_progress_tasks": stats.in_progress_tasks,
            "todo_tasks": stats.todo_tasks,
            "progress": stats.progress,
            "overdue_tasks": [
                {
                    "id": o.id,
                    "name": o.name,
                    "due_date": o.due_date.isoformat() if o.due_date else None,
                    "days_late": o.days_late,
                    "priority": o.priority,
                }
                for o in stats.overdue_tasks
            ],
        }


@mcp.tool()
async def get_burndown_mcp(project_id: int) -> list[dict]:
    """获取项目燃尽图数据（期望线 + 实际线）。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        p = await _require_project(db, username, project_id)
        start = p.start_date or date.today()
        end = p.end_date or date.today()
        points = await get_burndown(db, project_id, start, end)
        return [
            {"date": pt.date, "ideal_remaining": pt.ideal_remaining, "actual_remaining": pt.actual_remaining}
            for pt in points
        ]


@mcp.tool()
async def get_gantt_mcp(project_id: int) -> dict:
    """获取项目甘特图数据（任务 + 依赖）。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        p = await _require_project(db, username, project_id)
        start = p.start_date or date.today()
        end = p.end_date or date.today()
        gantt = await get_gantt_data(db, project_id, start, end)
        return {
            "project_start": gantt.project_start,
            "project_end": gantt.project_end,
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "start": t.start,
                    "end": t.end,
                    "progress": t.progress,
                    "dependencies": t.dependencies,
                    "overdue": t.overdue,
                    "status": t.status,
                }
                for t in gantt.tasks
            ],
        }


# ---------- 开发记录（DevLog / DevSession） ----------


async def _require_log(db, username: str, log_id: int) -> DevLog:
    user = await _get_user(db, username)
    log = (
        await db.execute(
            select(DevLog)
            .join(Project, DevLog.project_id == Project.id)
            .where(DevLog.id == log_id, Project.owner_id == user.id)
        )
    ).scalar_one_or_none()
    if log is None:
        raise ValueError(f"记录 {log_id} 不存在")
    return log


async def _require_session(db, username: str, session_id: int) -> DevSession:
    user = await _get_user(db, username)
    s = (
        await db.execute(
            select(DevSession)
            .join(Project, DevSession.project_id == Project.id)
            .where(DevSession.id == session_id, Project.owner_id == user.id)
        )
    ).scalar_one_or_none()
    if s is None:
        raise ValueError(f"会话 {session_id} 不存在")
    return s


async def _create_log_entry(
    db, username: str, project_id: int, entry_type: str, title: str,
    content: str | None = None, severity: str | None = None,
    related_task_ids: list[int] | None = None, git_ref: str | None = None,
    session_id: int | None = None,
) -> dict:
    await _require_project(db, username, project_id)
    payload = DevLogCreate(
        entry_type=entry_type,
        title=title,
        content=content,
        severity=severity,
        related_task_ids=related_task_ids,
        git_ref=git_ref,
    )
    try:
        await _validate_related_tasks(db, project_id, related_task_ids)
        sid = await _attach_session(db, project_id, session_id)
    except ValueError as e:
        raise ValueError(str(e))
    log = DevLog(
        project_id=project_id,
        session_id=sid,
        author=username,
        **payload.model_dump(exclude={"session_id"}),
    )
    if log.status == "done":
        log.resolved_at = utcnow()
    db.add(log)
    await db.commit()
    await db.refresh(log)
    await publish(project_id, "created", "log", log.id)
    return to_dict(log)


@mcp.tool()
async def log_progress(
    project_id: int, title: str, content: str | None = None,
    related_task_ids: list[int] | None = None, git_ref: str | None = None,
) -> dict:
    """记录一次开发进展。project_id 与 title 必填；建议附 git_ref（commit 或分支名）溯源。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        return await _create_log_entry(
            db, username, project_id, "progress", title, content,
            related_task_ids=related_task_ids, git_ref=git_ref,
        )


@mcp.tool()
async def log_difficulty(
    project_id: int, title: str, content: str | None = None,
    severity: str = "medium", related_task_ids: list[int] | None = None,
) -> dict:
    """记录遇到的难点。severity: low/medium/high。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        return await _create_log_entry(
            db, username, project_id, "difficulty", title, content,
            severity=severity, related_task_ids=related_task_ids,
        )


@mcp.tool()
async def log_todo(
    project_id: int, title: str, content: str | None = None,
    related_task_ids: list[int] | None = None, git_ref: str | None = None,
) -> dict:
    """记录下一步待办（开发过程中的 TODO，比任务更轻量）。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        return await _create_log_entry(
            db, username, project_id, "todo", title, content,
            related_task_ids=related_task_ids, git_ref=git_ref,
        )


@mcp.tool()
async def log_decision(
    project_id: int, title: str, content: str | None = None,
    related_task_ids: list[int] | None = None,
) -> dict:
    """记录一个技术决策及理由。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        return await _create_log_entry(
            db, username, project_id, "decision", title, content,
            related_task_ids=related_task_ids,
        )


@mcp.tool()
async def log_blocker(
    project_id: int, title: str, content: str | None = None,
    severity: str = "high",
) -> dict:
    """记录阻塞项。severity: low/medium/high（默认 high）。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        return await _create_log_entry(
            db, username, project_id, "blocker", title, content, severity=severity,
        )


@mcp.tool()
async def log_note(project_id: int, title: str, content: str | None = None) -> dict:
    """记录一条通用备注。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        return await _create_log_entry(db, username, project_id, "note", title, content)


@mcp.tool()
async def start_dev_session(project_id: int, title: str | None = None) -> dict:
    """开始一次开发会话。后续 log_* 会自动归入本次会话，直到 end_dev_session。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        await _require_project(db, username, project_id)
        s = DevSession(project_id=project_id, title=title, author=username)
        db.add(s)
        await db.commit()
        await db.refresh(s)
        await publish(project_id, "created", "session", s.id)
        return session_to_dict(s)


@mcp.tool()
async def end_dev_session(session_id: int, summary: str | None = None) -> dict:
    """结束一次开发会话，可选附会话总结。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        s = await _require_session(db, username, session_id)
        s.ended_at = utcnow()
        if summary is not None:
            s.summary = summary
        await db.commit()
        await db.refresh(s)
        await publish(s.project_id, "updated", "session", s.id)
        return session_to_dict(s)


@mcp.tool()
async def list_dev_logs(
    project_id: int, entry_type: str | None = None,
    status: str | None = None, since: str | None = None, limit: int = 50,
) -> list[dict]:
    """列出项目的开发记录。可按 entry_type（progress/difficulty/todo/decision/blocker/milestone/note）与 status（open/done）过滤。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        await _require_project(db, username, project_id)
        stmt = select(DevLog).where(DevLog.project_id == project_id)
        if entry_type:
            stmt = stmt.where(DevLog.entry_type == entry_type)
        if status:
            stmt = stmt.where(DevLog.status == status)
        if since:
            stmt = stmt.where(DevLog.created_at >= datetime.fromisoformat(since))
        rows = (
            (await db.execute(stmt.order_by(DevLog.created_at.desc()).limit(limit)))
            .scalars()
            .all()
        )
        return [to_dict(r) for r in rows]


@mcp.tool()
async def get_dev_log_stats_mcp(project_id: int) -> dict:
    """获取开发记录统计（今日记录/进行中难点/未完成待办/决策数等）。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        await _require_project(db, username, project_id)
        stats = await _get_dev_log_stats_service(db, project_id)
        return {
            "total": stats.total,
            "today_count": stats.today_count,
            "open_todos": stats.open_todos,
            "open_difficulties": stats.open_difficulties,
            "open_blockers": stats.open_blockers,
            "decisions": stats.decisions,
            "type_counts": stats.type_counts,
            "latest_activity": stats.latest_activity,
        }


@mcp.tool()
async def get_project_state(project_id: int) -> dict:
    """获取项目开发状态聚合包（待办/难点/阻塞/最近进展/最近决策/进行中会话），用于新会话快速恢复上下文。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        await _require_project(db, username, project_id)
        return await _get_project_state_service(db, project_id)


@mcp.tool()
async def get_dev_report(
    project_id: int, start: str | None = None, end: str | None = None,
) -> str:
    """生成项目开发汇报文本（Markdown）。start/end 为 ISO 日期，可省略表示全部时间。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        await _require_project(db, username, project_id)
        start_d = date.fromisoformat(start) if start else None
        end_d = date.fromisoformat(end) if end else None
        return await _get_dev_report_service(db, project_id, start_d, end_d)


@mcp.tool()
async def update_dev_log(
    log_id: int, title: str | None = None, content: str | None = None,
    severity: str | None = None, status: str | None = None,
    related_task_ids: list[int] | None = None,
) -> dict:
    """更新一条开发记录。仅更新传入字段。"""
    username = _username()
    updates = {}
    if title is not None:
        updates["title"] = title
    if content is not None:
        updates["content"] = content
    if severity is not None:
        updates["severity"] = severity
    if status is not None:
        updates["status"] = status
    if related_task_ids is not None:
        updates["related_task_ids"] = related_task_ids
    async with AsyncSessionLocal() as db:
        log = await _require_log(db, username, log_id)
        if "related_task_ids" in updates:
            try:
                await _validate_related_tasks(db, log.project_id, updates["related_task_ids"])
            except ValueError as e:
                raise ValueError(str(e))
        apply_log_update(log, updates)
        await db.commit()
        await db.refresh(log)
        await publish(log.project_id, "updated", "log", log.id)
        return to_dict(log)


@mcp.tool()
async def delete_dev_log(log_id: int) -> str:
    """删除一条开发记录。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        log = await _require_log(db, username, log_id)
        pid = log.project_id
        await db.delete(log)
        await db.commit()
        await publish(pid, "deleted", "log", log_id)
        return f"记录 {log_id} 已删除"


@mcp.tool()
async def resolve_dev_log(log_id: int) -> dict:
    """将一条开发记录标记为完成（仅 todo / blocker 条目可用）。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        log = await _require_log(db, username, log_id)
        if log.entry_type not in ("todo", "blocker"):
            raise ValueError("仅 todo / blocker 条目可标记完成")
        log.status = "done"
        log.resolved_at = utcnow()
        await db.commit()
        await db.refresh(log)
        await publish(log.project_id, "updated", "log", log.id)
        return to_dict(log)


def get_mcp_app():
    """返回可挂载到 FastAPI 的 ASGI 应用（Starlette）。"""
    return mcp.streamable_http_app()


def get_session_manager():
    """返回 MCP 的 StreamableHTTP 会话管理器，供宿主 App lifespan 启动。"""
    if mcp._session_manager is None:
        mcp.streamable_http_app()  # 触发惰性创建
    return mcp._session_manager


def _username() -> str:
    username = current_username.get()
    if not username:
        raise ValueError("未认证：请提供有效的 API Key")
    return username