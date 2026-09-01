from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DevLog, DevSession, ProgressSnapshot, Project, Task
from app.models.task_dependency import TaskDependency
from app.schemas.stats import (
    BurndownPoint,
    DashboardOverdueItem,
    DashboardOverview,
    DashboardProjectCard,
    DashboardRecentLog,
    DashboardSession,
    GanttData,
    GanttDependency,
    GanttTask,
    OverdueTask,
    ProjectStats,
)
from app.utils.time import today_utc


def is_overdue(task: Task, today: date | None = None) -> bool:
    """延期判定：未完成且截止日期早于今天（不落库，实时派生）。"""
    today = today or today_utc()
    return task.status != "done" and task.due_date is not None and task.due_date < today


def compute_overdue(task: Task) -> OverdueTask | None:
    if not is_overdue(task):
        return None
    days_late = (today_utc() - task.due_date).days
    return OverdueTask(
        id=task.id,
        name=task.name,
        due_date=task.due_date,
        days_late=days_late,
        priority=task.priority,
    )


async def get_project_stats(db: AsyncSession, project_id: int) -> ProjectStats:
    """项目进度汇总：总数/完成/进行中/待办 + 进度%（数量与工时加权）+ 延期列表。"""
    row = (
        await db.execute(
            select(
                func.count(Task.id),
                func.count().filter(Task.status == "done"),
                func.count().filter(Task.status == "in_progress"),
                func.count().filter(Task.status == "todo"),
                # 工时加权：权重=预估工时（未填按 1），任务进度即权重占比
                func.coalesce(func.sum(func.coalesce(Task.estimated_hours, 1) * Task.progress), 0),
                func.coalesce(func.sum(func.coalesce(Task.estimated_hours, 1)), 0),
                func.sum(Task.estimated_hours),  # 已填工时的总量（None=无任务填工时）
            ).where(Task.project_id == project_id)
        )
    ).one()
    total, done, in_progress, todo, weighted_num, weighted_den, hours_total = row

    progress = round(done / total * 100, 1) if total else 0.0
    weighted_progress = round(float(weighted_num) / float(weighted_den), 1) if weighted_den else 0.0
    estimated_hours_total = float(hours_total) if hours_total is not None else None

    tasks = (
        (
            await db.execute(
                select(Task).where(
                    Task.project_id == project_id,
                    Task.status != "done",
                    Task.due_date.is_not(None),
                )
            )
        )
        .scalars()
        .all()
    )
    overdue = [o for o in (compute_overdue(t) for t in tasks) if o is not None]
    overdue.sort(key=lambda o: o.days_late, reverse=True)

    # P4-3 每日快照：读取统计时按天 upsert（自愈式），保证趋势数据随使用自然沉淀
    await upsert_progress_snapshot(db, project_id, total, done, progress, weighted_progress)

    return ProjectStats(
        total_tasks=total,
        done_tasks=done,
        in_progress_tasks=in_progress,
        todo_tasks=todo,
        progress=progress,
        weighted_progress=weighted_progress,
        estimated_hours_total=estimated_hours_total,
        overdue_tasks=overdue,
    )


async def upsert_progress_snapshot(
    db: AsyncSession, project_id: int, total: int, done: int, progress: float, weighted: float
) -> None:
    """写入/更新今日快照；同日重复读取仅更新数值。

    查询后更新而非方言级 upsert：SQLite（测试）与 PostgreSQL（生产）双兼容；
    单用户工具并发冲突可忽略，唯一约束兜底。
    """
    today = today_utc()
    snap = (
        await db.execute(
            select(ProgressSnapshot).where(
                ProgressSnapshot.project_id == project_id,
                ProgressSnapshot.date == today,
            )
        )
    ).scalar_one_or_none()
    if snap is None:
        snap = ProgressSnapshot(
            project_id=project_id,
            date=today,
            total_tasks=total,
            done_tasks=done,
            progress=progress,
            weighted_progress=weighted,
        )
        db.add(snap)
    else:
        snap.total_tasks = total
        snap.done_tasks = done
        snap.progress = progress
        snap.weighted_progress = weighted
    await db.commit()


async def get_progress_history(db: AsyncSession, project_id: int, limit: int = 90) -> list[ProgressSnapshot]:
    """按日期升序返回最近 N 天快照（供趋势图/回溯）。"""
    rows = (
        (
            await db.execute(
                select(ProgressSnapshot)
                .where(ProgressSnapshot.project_id == project_id)
                .order_by(ProgressSnapshot.date.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return list(reversed(rows))


def _date_range(start: date, end: date) -> list[date]:
    days = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur += timedelta(days=1)
    return days


async def get_burndown(db: AsyncSession, project_id: int, start: date, end: date) -> list[BurndownPoint]:
    """燃尽图（轻量无快照表）：
    - 期望线：项目起止日之间，从总任务数线性降到 0
    - 实际线：基于 Task.completed_at 按日聚合，每天 = 总任务数 - 当日累计完成数
    """
    total = (
        await db.execute(select(func.count(Task.id)).where(Task.project_id == project_id))
    ).scalar_one()

    rows = (
        await db.execute(
            select(Task.completed_at).where(
                Task.project_id == project_id,
                Task.status == "done",
                Task.completed_at.is_not(None),
            )
        )
    ).all()

    # 按日期统计完成数（completed_at 为 UTC datetime，取日期）
    completed_by_day: dict[date, int] = {}
    for (completed_at,) in rows:
        d = completed_at.date()
        completed_by_day[d] = completed_by_day.get(d, 0) + 1

    days = _date_range(start, end)
    n = len(days)
    points: list[BurndownPoint] = []
    cumulative = 0
    for i, d in enumerate(days):
        cumulative += completed_by_day.get(d, 0)
        # 理想剩余：起点总任务数，终点 0
        ideal = round(total * (1 - i / max(n - 1, 1)))
        points.append(
            BurndownPoint(
                date=d.isoformat(),
                ideal_remaining=ideal,
                actual_remaining=max(total - cumulative, 0),
            )
        )
    return points


async def get_gantt_data(db: AsyncSession, project_id: int, start: date, end: date) -> GanttData:
    """甘特图数据：任务 + 依赖（frappe-gantt 可直接消费）。"""
    tasks = (
        (await db.execute(select(Task).where(Task.project_id == project_id)))
        .scalars()
        .all()
    )

    dep_rows = (
        await db.execute(
            select(TaskDependency.task_id, TaskDependency.depends_on_task_id).where(
                TaskDependency.task_id.in_([t.id for t in tasks]) if tasks else False
            )
        )
    ).all()
    deps = [GanttDependency(task_id=tid, depends_on_task_id=did) for tid, did in dep_rows]

    # 聚合依赖字符串 "task_id:dep_id,task_id:dep_id"
    dep_map: dict[int, list[int]] = {}
    for dep in deps:
        dep_map.setdefault(dep.task_id, []).append(dep.depends_on_task_id)

    gantt_tasks = [
        GanttTask(
            id=str(t.id),
            name=t.name,
            start=(t.start_date or start).isoformat(),
            end=(t.due_date or end).isoformat(),
            progress=t.progress,
            dependencies=",".join(
                f"{t.id}:{did}" for did in dep_map.get(t.id, [])
            ),
            overdue=is_overdue(t),
            status=t.status,
        )
        for t in tasks
    ]

    return GanttData(
        tasks=gantt_tasks,
        project_start=start.isoformat(),
        project_end=end.isoformat(),
    )


async def get_overview(db: AsyncSession, user_id: int) -> DashboardOverview:
    """仪表盘聚合：当前用户全量项目的进度卡片、跨项目逾期、近期 DevLog、活跃会话、今日完成数。

    单次查询返回，避免前端 N+1 并发请求。
    """
    today = today_utc()

    # 用户全部项目
    projects = (
        (
            await db.execute(
                select(Project).where(Project.owner_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    project_ids = [p.id for p in projects]
    pid_to_name = {p.id: p.name for p in projects}

    # 项目进度统计（一次聚合，含工时加权）
    project_stats_rows = (
        await db.execute(
            select(
                Task.project_id,
                func.count(Task.id),
                func.count().filter(Task.status == "done"),
                func.count().filter(
                    (Task.status != "done") & (Task.due_date.is_not(None)) & (Task.due_date < today)
                ),
                func.coalesce(func.sum(func.coalesce(Task.estimated_hours, 1) * Task.progress), 0),
                func.coalesce(func.sum(func.coalesce(Task.estimated_hours, 1)), 0),
            ).where(Task.project_id.in_(project_ids) if project_ids else False)
            .group_by(Task.project_id)
        )
    ).all() if project_ids else []
    stats_by_pid: dict[int, tuple[int, int, int, float, float]] = {
        pid: (total, done, overdue, weighted_num, weighted_den)
        for pid, total, done, overdue, weighted_num, weighted_den in project_stats_rows
    }

    cards = []
    for p in projects:
        total, done, overdue, weighted_num, weighted_den = stats_by_pid.get(p.id, (0, 0, 0, 0, 0))
        cards.append(
            DashboardProjectCard(
                project_id=p.id,
                name=p.name,
                status=p.status,
                progress=round(done / total * 100, 1) if total else 0.0,
                weighted_progress=round(float(weighted_num) / float(weighted_den), 1) if weighted_den else 0.0,
                total_tasks=total,
                done_tasks=done,
                overdue_count=overdue,
            )
        )

    # 跨项目逾期任务
    overdue_query = (
        await db.execute(
            select(Task).where(
                Task.project_id.in_(project_ids) if project_ids else False,
                Task.status != "done",
                Task.due_date.is_not(None),
                Task.due_date < today,
            )
        )
    ).scalars().all() if project_ids else []
    overdue_items = [
        DashboardOverdueItem(
            id=t.id,
            name=t.name,
            project_id=t.project_id,
            project_name=pid_to_name.get(t.project_id, ""),
            due_date=t.due_date,
            days_late=(today - t.due_date).days,
            priority=t.priority,
        )
        for t in overdue_query
    ]
    overdue_items.sort(key=lambda x: x.days_late, reverse=True)

    # 近期 DevLog（按创建时间倒序取 12 条）
    recent_logs = []
    if project_ids:
        log_rows = (
            await db.execute(
                select(DevLog)
                .where(DevLog.project_id.in_(project_ids))
                .order_by(DevLog.created_at.desc())
                .limit(12)
            )
        ).scalars().all()
        recent_logs = [
            DashboardRecentLog(
                id=lg.id,
                project_id=lg.project_id,
                project_name=pid_to_name.get(lg.project_id, ""),
                entry_type=lg.entry_type,
                title=lg.title,
                author=lg.author,
                created_at=lg.created_at.isoformat(),
            )
            for lg in log_rows
        ]

    # 活跃会话（未结束）
    active_sessions = []
    if project_ids:
        session_rows = (
            await db.execute(
                select(DevSession, func.count(DevLog.id))
                .outerjoin(DevLog, DevLog.session_id == DevSession.id)
                .where(DevSession.project_id.in_(project_ids), DevSession.ended_at.is_(None))
                .group_by(DevSession.id)
            )
        ).all()
        active_sessions = [
            DashboardSession(
                id=s.id,
                project_id=s.project_id,
                project_name=pid_to_name.get(s.project_id, ""),
                title=s.title,
                log_count=count,
                started_at=s.started_at.isoformat(),
            )
            for s, count in session_rows
        ]

    # 今日完成数（按本地完成日期判定）
    today_completed = 0
    if project_ids:
        today_completed = (
            await db.execute(
                select(func.count(Task.id)).where(
                    Task.project_id.in_(project_ids),
                    Task.status == "done",
                    Task.completed_at.is_not(None),
                    func.date(Task.completed_at) == today.isoformat(),
                )
            )
        ).scalar_one()

    return DashboardOverview(
        total_projects=len(projects),
        active_projects=sum(1 for p in projects if p.status == "active"),
        projects=cards,
        overdue_tasks=overdue_items,
        recent_logs=recent_logs,
        active_sessions=active_sessions,
        today_completed=today_completed or 0,
    )
