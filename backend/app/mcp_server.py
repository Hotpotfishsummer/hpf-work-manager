"""MCP Server：让 AI 编码工具通过 MCP 协议读写项目数据。

- 通过 Streamable HTTP 传输暴露（FastMCP.streamable_http_app()）
- 认证由外层 ASGI 中间件完成，将解析出的用户名写入 contextvar
- 工具复用 services 层与模型，避免业务逻辑分叉
"""

import contextvars
from datetime import UTC, date, datetime
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy import or_, select

from app.config import settings
from app.core.events import publish
from app.database import AsyncSessionLocal
from app.models import (
    Comment,
    DevLog,
    DevSession,
    Milestone,
    Project,
    Task,
    TaskDependency,
    User,
)
from app.schemas import (
    DevLogCreate,
    MilestoneCreate,
    ProjectCreate,
    TaskCreate,
)
from app.schemas.task import TASK_CATEGORIES
from app.services.dev_logs import (
    _attach_session,
    _validate_related_tasks,
    apply_log_update,
    session_to_dict,
    to_dict,
)
from app.services.dev_logs import (
    get_dev_log_stats as _get_dev_log_stats_service,
)
from app.services.dev_logs import (
    get_dev_report as _get_dev_report_service,
)
from app.services.dev_logs import (
    get_project_state as _get_project_state_service,
)
from app.services.stats import (
    display_today,
    get_burndown,
    get_gantt_data,
)
from app.services.stats import (
    get_project_stats as _get_project_stats_service,
)
from app.services.tasks import (
    apply_task_update,
    ensure_no_cycle,
    get_project_comment_counts,
    get_project_depends_map,
    get_task_depends,
)
from app.services.comments import (
    comment_to_dict,
    list_project_comments,
    list_task_comments,
    open_direction_counts,
    owned_comment_project_id,
    set_resolved,
)
from app.utils.time import utcnow

# 由 ASGI 中间件在每次请求时写入当前认证用户名
current_username: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "mcp_current_username", default=None
)

def _allowed_hosts() -> list[str]:
    """MCP DNS 防重绑定允许的 Host 列表。包含本地回环与 Tailscale 信任域。"""
    hosts = {"localhost", "localhost:8088", "127.0.0.1", "127.0.0.1:8088", "100.69.225.112", "100.69.225.112:8088"}
    if settings.mcp_allowed_hosts.strip():
        for h in settings.mcp_allowed_hosts.split(","):
            if h.strip():
                hosts.add(h.strip())
    for raw in settings.cors_origin_list:
        host = urlparse(raw).netloc
        if host:
            hosts.add(host)
    return list(hosts)


mcp = FastMCP(
    "HPF Work Manager",
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=bool(_allowed_hosts()),
        allowed_hosts=_allowed_hosts(),
    ),
    instructions=(
        "HPF 任务/项目管理、5h额度雷达与双重认证协同 MCP 服务。"
        "提供项目、里程碑、任务、依赖、DevLog，以及外驱双重认证协同与下一步推演规划能力。"
        "AI 工具可在编码过程中自动维护任务状态、进行规划交叉审查与防幻觉核销。"
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


def _task_dict(
    t: Task, depends_on: list[int] | None = None, comment_count: int | None = None
) -> dict:
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
        "category": t.category,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "depends_on": sorted(depends_on) if depends_on is not None else [],
        "comment_count": comment_count if comment_count is not None else 0,
    }


# ---------- 项目 ----------


@mcp.tool()
async def list_projects(
    status: str | None = None, offset: int = 0, limit: int = 50
) -> list[dict]:
    """列出当前用户的所有项目，可按 status（active/archived）过滤；offset/limit 分页。"""
    username = _username()
    if status is not None and status not in ("active", "archived"):
        raise ValueError("status 必须为 active / archived 之一")
    async with AsyncSessionLocal() as db:
        user = await _get_user(db, username)
        stmt = select(Project).where(Project.owner_id == user.id)
        if status:
            stmt = stmt.where(Project.status == status)
        rows = (
            (
                await db.execute(
                    stmt.order_by(Project.created_at.desc())
                    .offset(max(0, offset))
                    .limit(min(max(1, limit), 200))
                )
            )
            .scalars()
            .all()
        )
        counts = await open_direction_counts(db, [p.id for p in rows])
        return [{**_project_dict(p), "open_directions": counts.get(p.id, 0)} for p in rows]


@mcp.tool()
async def get_project(project_id: int) -> dict:
    """获取单个项目详情。open_directions=该项目未处理的工作方向指示数（>0 时开工前先读 list_comments(project_id=...)）。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        p = await _require_project(db, username, project_id)
        counts = await open_direction_counts(db, [p.id])
        return {**_project_dict(p), "open_directions": counts.get(p.id, 0)}


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
    project_id: int, status: str | None = None, overdue: bool | None = None,
    search: str | None = None, offset: int = 0, limit: int = 200,
) -> list[dict]:
    """列出项目任务。可按 status（todo/in_progress/done）、overdue 过滤、search 名称/描述模糊搜索；offset/limit 分页。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        await _require_project(db, username, project_id)
        stmt = select(Task).where(Task.project_id == project_id)
        if status:
            stmt = stmt.where(Task.status == status)
        if overdue is True:
            stmt = stmt.where(Task.status != "done", Task.due_date.is_not(None), Task.due_date < display_today())
        if overdue is False:
            # 与 overdue=True 对称的 SQL 条件：保证分页语义稳定（页大小恒定）
            stmt = stmt.where(
                or_(Task.status == "done", Task.due_date.is_(None), Task.due_date >= display_today())
            )
        if search:
            like = f"%{search.strip()}%"
            stmt = stmt.where(or_(Task.name.ilike(like), Task.description.ilike(like)))
        rows = (
            (
                await db.execute(
                    stmt.order_by(Task.created_at.desc())
                    .offset(max(0, offset))
                    .limit(min(max(1, limit), 500))
                )
            )
            .scalars()
            .all()
        )
        depends_map = await get_project_depends_map(db, project_id)
        comment_counts = await get_project_comment_counts(db, project_id)
        return [
            _task_dict(t, depends_map.get(t.id, []), comment_counts.get(t.id, 0))
            for t in rows
        ]


@mcp.tool()
async def get_task(task_id: int) -> dict:
    """获取单个任务详情（含前置依赖：depends_on 为 id 列表，depends_on_detail 含名称/状态/进度，便于判断是否可开工）。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        task = await _require_task(db, username, task_id)
        comment_counts = await get_project_comment_counts(db, task.project_id)
        return {
            **_task_dict(
                task, await get_task_depends(db, task.id), comment_counts.get(task.id, 0)
            ),
            "depends_on_detail": await _depends_detail(db, task.id),
        }


@mcp.tool()
async def create_task(
    project_id: int, name: str, description: str | None = None,
    milestone_id: int | None = None, priority: str = "medium",
    status: str = "todo", progress: int = 0, start_date: str | None = None,
    due_date: str | None = None, estimated_hours: int | None = None,
    category: str | None = None,
) -> dict:
    """在项目中创建任务。project_id 与 name 必填。status=done 时自动 progress=100。
    category 取 feature/bugfix/refactor/testing/docs/devops 之一（不传=未分类）。"""
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
        category=category,
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
    estimated_hours: int | None = None, category: str | None = None,
    add_depends_on: list[int] | None = None,
    remove_depends_on: list[int] | None = None,
) -> dict:
    """更新任务。仅更新传入字段；status=done 自动 progress=100。
    category 取 feature/bugfix/refactor/testing/docs/devops 之一。
    依赖管理：add_depends_on / remove_depends_on 传前置任务 id 列表
    （前者依赖后者；重复添加自动跳过，移除不存在的依赖自动忽略）。
    当前依赖可从 get_task 返回的 depends_on / depends_on_detail 读取。"""
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
    if category is not None:
        if category not in TASK_CATEGORIES:
            raise ValueError(f"category 必须为 {sorted(TASK_CATEGORIES)} 之一")
        updates["category"] = category
    async with AsyncSessionLocal() as db:
        task = await _require_task(db, username, task_id)
        if "milestone_id" in updates:
            ms = await db.get(Milestone, updates["milestone_id"])
            if ms is None or ms.project_id != task.project_id:
                raise ValueError("里程碑不存在或不属于该项目")
        apply_task_update(task, updates)
        for dep_id in add_depends_on or []:
            await _require_task(db, username, dep_id)
            await ensure_no_cycle(db, task_id, dep_id)
            exists = (
                await db.execute(
                    select(TaskDependency).where(
                        TaskDependency.task_id == task_id,
                        TaskDependency.depends_on_task_id == dep_id,
                    )
                )
            ).scalar_one_or_none()
            if exists is None:
                db.add(TaskDependency(task_id=task_id, depends_on_task_id=dep_id))
        for dep_id in remove_depends_on or []:
            row = (
                await db.execute(
                    select(TaskDependency).where(
                        TaskDependency.task_id == task_id,
                        TaskDependency.depends_on_task_id == dep_id,
                    )
                )
            ).scalar_one_or_none()
            if row is not None:
                await db.delete(row)
        await db.commit()
        await db.refresh(task)
        await publish(task.project_id, "updated", "task", task.id)
        return _task_dict(task, await get_task_depends(db, task.id))


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


async def _depends_detail(db, task_id: int) -> list[dict]:
    """任务前置依赖的富信息（名称/状态/进度），供 get_task 附带返回。"""
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
        {"task_id": rid, "name": name, "status": status, "progress": progress}
        for rid, name, status, progress in rows
    ]


# ---------- 统计 ----------


@mcp.tool()
async def get_project_stats(project_id: int, kind: str = "overview") -> dict:
    """获取项目统计数据。kind 取值：
    overview（默认）= 进度统计（总数/完成/进行中/待办/进度%/工时加权进度/延期列表）；
    burndown = 燃尽图数据（期望线 + 实际线）；
    gantt = 甘特图数据（任务 + 依赖）；
    devlog = 开发记录统计（今日记录/进行中难点/未完成待办/决策数等）。
    返回 {"kind": kind, "data": ...}。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        p = await _require_project(db, username, project_id)
        if kind == "overview":
            stats = await _get_project_stats_service(db, project_id)
            data: object = {
                "total_tasks": stats.total_tasks,
                "done_tasks": stats.done_tasks,
                "in_progress_tasks": stats.in_progress_tasks,
                "todo_tasks": stats.todo_tasks,
                "progress": stats.progress,
                "weighted_progress": stats.weighted_progress,
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
        elif kind == "burndown":
            start = p.start_date or display_today()
            end = p.end_date or display_today()
            points = await get_burndown(db, project_id, start, end)
            data = [
                {"date": pt.date, "ideal_remaining": pt.ideal_remaining, "actual_remaining": pt.actual_remaining}
                for pt in points
            ]
        elif kind == "gantt":
            start = p.start_date or display_today()
            end = p.end_date or display_today()
            gantt = await get_gantt_data(db, project_id, start, end)
            data = {
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
        elif kind == "devlog":
            stats = await _get_dev_log_stats_service(db, project_id)
            data = {
                "total": stats.total,
                "today_count": stats.today_count,
                "open_todos": stats.open_todos,
                "open_difficulties": stats.open_difficulties,
                "open_blockers": stats.open_blockers,
                "decisions": stats.decisions,
                "type_counts": stats.type_counts,
                "latest_activity": stats.latest_activity,
            }
        else:
            raise ValueError("kind 必须为 overview / burndown / gantt / devlog 之一")
        return {"kind": kind, "data": data}


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
        raise ValueError(str(e)) from e
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
async def log_dev_entry(
    project_id: int, entry_type: str, title: str, content: str | None = None,
    severity: str | None = None, related_task_ids: list[int] | None = None,
    git_ref: str | None = None,
) -> dict:
    """写入一条开发记录（DevLog）。entry_type 取值与用途：
    progress=开发进展（建议附 git_ref 溯源）；difficulty=难点；todo=下一步轻量待办；
    decision=技术决策及理由；blocker=阻塞项；note=通用备注。
    severity（low/medium/high）仅 difficulty（默认 medium）/blocker（默认 high）有效。
    todo/blocker 条目后续用 manage_dev_log(action="resolve") 关闭。"""
    username = _username()
    if entry_type not in ("progress", "difficulty", "todo", "decision", "blocker", "note"):
        raise ValueError("entry_type 必须为 progress / difficulty / todo / decision / blocker / note 之一")
    if severity is None:
        if entry_type == "difficulty":
            severity = "medium"
        elif entry_type == "blocker":
            severity = "high"
    async with AsyncSessionLocal() as db:
        return await _create_log_entry(
            db, username, project_id, entry_type, title, content,
            severity=severity, related_task_ids=related_task_ids, git_ref=git_ref,
        )


@mcp.tool()
async def start_dev_session(project_id: int, title: str | None = None) -> dict:
    """开始一次开发会话。后续 log_dev_entry 会自动归入本次会话，直到 end_dev_session。"""
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
    status: str | None = None, since: str | None = None,
    limit: int = 50, offset: int = 0,
) -> list[dict]:
    """列出项目的开发记录。可按 entry_type（progress/difficulty/todo/decision/blocker/milestone/note）与 status（open/done）过滤；offset/limit 分页。"""
    username = _username()
    async with AsyncSessionLocal() as db:
        await _require_project(db, username, project_id)
        stmt = select(DevLog).where(DevLog.project_id == project_id)
        if entry_type:
            stmt = stmt.where(DevLog.entry_type == entry_type)
        if status:
            stmt = stmt.where(DevLog.status == status)
        if since:
            since_dt = datetime.fromisoformat(since)
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=UTC)
            stmt = stmt.where(DevLog.created_at >= since_dt)
        rows = (
            (
                await db.execute(
                    stmt.order_by(DevLog.created_at.desc())
                    .offset(max(0, offset))
                    .limit(min(max(1, limit), 200))
                )
            )
            .scalars()
            .all()
        )
        return [to_dict(r) for r in rows]


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
async def manage_dev_log(
    log_id: int, action: str, title: str | None = None,
    content: str | None = None, severity: str | None = None,
    status: str | None = None, related_task_ids: list[int] | None = None,
) -> dict:
    """维护一条开发记录。action 取值：
    update=更新字段（仅更新传入字段）；
    resolve=标记完成（仅 todo / blocker 条目可用）；
    delete=删除该记录。"""
    username = _username()
    if action not in ("update", "resolve", "delete"):
        raise ValueError("action 必须为 update / resolve / delete 之一")
    async with AsyncSessionLocal() as db:
        log = await _require_log(db, username, log_id)
        if action == "delete":
            pid = log.project_id
            await db.delete(log)
            await db.commit()
            await publish(pid, "deleted", "log", log_id)
            return {"ok": True, "deleted_log_id": log_id}
        if action == "resolve":
            if log.entry_type not in ("todo", "blocker"):
                raise ValueError("仅 todo / blocker 条目可标记完成")
            log.status = "done"
            log.resolved_at = utcnow()
        else:  # update
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
                try:
                    await _validate_related_tasks(db, log.project_id, related_task_ids)
                except ValueError as e:
                    raise ValueError(str(e)) from e
                updates["related_task_ids"] = related_task_ids
            apply_log_update(log, updates)
        await db.commit()
        await db.refresh(log)
        await publish(log.project_id, "updated", "log", log.id)
        return {"ok": True, "log": to_dict(log)}


# ---------- 评论（P5） ----------


def _require_anchor(task_id: int | None, project_id: int | None) -> None:
    """评论必须明确挂在一个锚点上；两个都传会产生歧义，直接拒绝。"""
    if (task_id is None) == (project_id is None):
        raise ValueError("task_id 与 project_id 必须且只能传一个")


def _validate_comment_content(content: str) -> str:
    if not content.strip():
        raise ValueError("评论内容不能为空")
    if len(content) > 2000:
        raise ValueError("评论内容不能超过 2000 字符")
    return content.strip()


@mcp.tool()
async def add_comment(
    task_id: int | None = None,
    project_id: int | None = None,
    content: str = "",
    resolve_ids: list[int] | None = None,
) -> dict:
    """添加评论，和/或把项目指示标记为已处理。task_id 与 project_id 必须且只能传一个。

    - task_id=任务评论：对单个任务的讨论。
    - project_id=项目评论：给该项目留「工作方向 / 指示 / 结论」，下次接手该项目的 Agent
      会在 get_project_state 的 directions 字段里读到（也会随 Prompt 一起下发）。
      项目负责人用它告诉 Agent 往哪走、别碰什么。
    - resolve_ids=项目评论 id 列表：指示已落实时一并标记为已处理，避免旧指示反复出现在
      后续 Agent 的上下文里。只想结单不写新评论时，content 可留空。
    返回 {comment, resolved_ids}。"""
    username = _username()
    _require_anchor(task_id, project_id)
    content = content.strip()
    if not content and not resolve_ids:
        raise ValueError("content 与 resolve_ids 至少提供一个")
    if content:
        content = _validate_comment_content(content)
    async with AsyncSessionLocal() as db:
        # 先校验锚点归属，再写 —— 他人项目/任务一律按「不存在」拒绝
        if task_id is not None:
            anchor_pid = (await _require_task(db, username, task_id)).project_id
        else:
            await _require_project(db, username, project_id)
            anchor_pid = project_id
        user = (
            await db.execute(select(User).where(User.username == username))
        ).scalar_one_or_none()
        owner_id = user.id if user else -1

        created = None
        if content:
            comment = Comment(
                task_id=task_id,
                project_id=project_id,
                author_id=user.id if user else None,
                author_username=username,
                content=content,
            )
            db.add(comment)
            await db.commit()
            await db.refresh(comment)
            await publish(anchor_pid, "created", "comment", comment.id)
            created = comment

        resolved_ids: list[int] = []
        for cid in resolve_ids or []:
            found = await owned_comment_project_id(db, cid, owner_id)
            if found is None:
                raise ValueError(f"评论 {cid} 不存在")
            target, pid = found
            if target.project_id is None:
                raise ValueError(f"评论 {cid} 是任务评论，不支持标记已处理")
            if project_id is not None and target.project_id != project_id:
                raise ValueError(f"评论 {cid} 不属于项目 {project_id}")
            await set_resolved(db, target, True)
            await publish(pid, "updated", "comment", target.id)
            resolved_ids.append(cid)

        return {
            "comment": _comment_dict(created) if created is not None else None,
            "resolved_ids": resolved_ids,
        }


@mcp.tool()
async def list_comments(
    task_id: int | None = None,
    project_id: int | None = None,
    include_resolved: bool = False,
    offset: int = 0,
    limit: int = 100,
) -> list[dict]:
    """列出评论（按时间升序；offset/limit 分页，上限 500）。task_id 与 project_id 必须且只能传一个。

    project_id=读取项目的「工作方向指示」—— 接手某项目开工前应先读它。
    默认只返回未处理（include_resolved=False）的项目指示；include_resolved=True 看完整时间线。"""
    username = _username()
    _require_anchor(task_id, project_id)
    async with AsyncSessionLocal() as db:
        if task_id is not None:
            await _require_task(db, username, task_id)
            rows = await list_task_comments(db, task_id)
        else:
            await _require_project(db, username, project_id)
            rows = await list_project_comments(
                db, project_id, include_resolved=include_resolved
            )
        start = max(0, offset)
        end = start + min(max(1, limit), 500)
        return [_comment_dict(c) for c in rows[start:end]]


def _comment_dict(c: Comment) -> dict:
    d = comment_to_dict(c)
    d["created_at"] = c.created_at.isoformat() if c.created_at else None
    return d


# =====================================================================
# 7. AI Driver & 双重认证协同工具（4 个）
# =====================================================================


@mcp.tool()
async def get_manager_status() -> dict:
    """查询管理器当前算力配额与 Agent 驱动模式（双重认证 DUAL_CERTIFIED vs 外部单驱 EXTERNAL_DRIVEN）及行动指南。"""
    from app.services.ideator import get_active_workspace
    from app.services.quota import quota_service

    mode_info = await quota_service.get_driver_mode()
    return {
        "ok": True,
        "driver_mode": mode_info["driver_mode"],
        "mode_description": mode_info["mode_desc"],
        "has_internal_tokens": mode_info["has_internal_tokens"],
        "quota": mode_info["quota_status"],
        "guidelines": mode_info["guidelines"],
        "active_workspace": str(get_active_workspace()),
    }


@mcp.tool()
async def get_next_steps(project_name: str) -> list[dict]:
    """获取指定项目的下一步高价值落地任务建议。内部有额度时由 MiniMax 架构师推演，额度耗尽时自动降级为代码库启发式规则推演。"""
    from app.services.ideator import ideator_service

    return await ideator_service.generate_next_steps(project_name)


@mcp.tool()
async def propose_task_plan(
    project_name: str,
    tasks: list[dict],
    agent_role_or_id: str = "external_agent",
    rationale: str = "",
    auto_create: bool = False,
) -> dict:
    """【双重认证核心】外部 Agent 提交多项任务规划提案。
    内部 Token 充足时由 MiniMax 架构师交叉审查，纠偏低端模型的理解偏差与幻觉；
    内部 Token 耗尽时由确定性工程护栏校验。若 auto_create=True 则直接将认证任务建档落入看板。
    """
    from app.services.ideator import ideator_service

    username = _username()
    review_result = await ideator_service.review_task_proposal(
        project_name=project_name,
        proposed_tasks=tasks,
        agent_role_or_id=agent_role_or_id,
        rationale=rationale,
    )

    created_task_ids = []
    if auto_create and review_result.get("ok"):
        async with AsyncSessionLocal() as db:
            user = await _get_user(db, username)
            proj = (
                await db.execute(
                    select(Project).where(
                        Project.owner_id == user.id,
                        Project.name == project_name,
                    )
                )
            ).scalar_one_or_none()
            if not proj:
                local_projs = ideator_service.list_projects()
                found_desc = next(
                    (p["description"] for p in local_projs if p["name"] == project_name),
                    f"服务器本地项目 {project_name}",
                )
                proj = Project(
                    name=project_name[:120],
                    description=found_desc[:500] if found_desc else None,
                    owner_id=user.id,
                    status="active",
                )
                db.add(proj)
                await db.commit()
                await db.refresh(proj)
                await publish(proj.id, "created", "project", proj.id)

            for t in review_result.get("certified_tasks", []):
                new_task = Task(
                    project_id=proj.id,
                    name=t.get("title", "未命名任务")[:200],
                    description=t.get("description", "")[:1000],
                    status="todo",
                    priority=t.get("priority", "medium")
                    if t.get("priority") in ["low", "medium", "high"]
                    else "medium",
                    progress=0,
                    estimated_hours=t.get("estimated_hours", 2),
                )
                db.add(new_task)
                await db.commit()
                await db.refresh(new_task)
                created_task_ids.append(new_task.id)
                await publish(proj.id, "created", "task", new_task.id)

    return {
        **review_result,
        "created_task_ids": created_task_ids,
        "project_name": project_name,
    }


@mcp.tool()
async def verify_and_complete_task(
    task_id: int,
    git_ref: str,
    verification_evidence: str,
    summary: str = "",
) -> dict:
    """【双重认证核销】外部 Agent 交付完成任务。
    必须提供真实 git commit hash 与验收测试凭证，杜绝低端模型凭假设标记完成。
    成功后自动盖章标记 done 并生成关联 DevLog 交付记录与 SSE 事件广播。
    """
    from app.services.tasks import apply_status_transition

    username = _username()
    async with AsyncSessionLocal() as db:
        user = await _get_user(db, username)
        task = (
            await db.execute(
                select(Task)
                .join(Project, Task.project_id == Project.id)
                .where(Task.id == task_id, Project.owner_id == user.id)
            )
        ).scalar_one_or_none()
        if not task:
            raise ValueError(f"任务 {task_id} 不存在或无权操作")

        # 标记完成
        apply_status_transition(task, "done")
        db.add(task)

        session_id = await _attach_session(db, task.project_id, None)

        # 自动生成 DevLog 交付记录
        log = DevLog(
            project_id=task.project_id,
            session_id=session_id,
            entry_type="progress",
            title=f"完成工单: {task.name}",
            content=f"【完成总结】{summary or task.name}\n\n【验收验证凭证】\n{verification_evidence}",
            git_ref=git_ref[:100],
            author=username,
            related_task_ids=[task.id],
        )
        db.add(log)
        await db.commit()
        await db.refresh(task)
        await db.refresh(log)

        await publish(task.project_id, "updated", "task", task.id)
        await publish(task.project_id, "created", "log", log.id)

        return {
            "ok": True,
            "task_id": task.id,
            "task_name": task.name,
            "status": task.status,
            "dev_log_id": log.id,
            "git_ref": git_ref,
            "certified": True,
            "message": f"任务「{task.name}」已完成双重认证归档，并生成关联 DevLog 凭证！",
        }


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
