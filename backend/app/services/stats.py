from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, TaskDependency
from app.schemas.stats import (
    BurndownPoint,
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
    """项目进度汇总：总数/完成/进行中/待办 + 进度%（完成任务数/总任务数）+ 延期列表。"""
    row = (
        await db.execute(
            select(
                func.count(Task.id),
                func.count().filter(Task.status == "done"),
                func.count().filter(Task.status == "in_progress"),
                func.count().filter(Task.status == "todo"),
            ).where(Task.project_id == project_id)
        )
    ).one()
    total, done, in_progress, todo = row

    progress = round(done / total * 100, 1) if total else 0.0

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

    return ProjectStats(
        total_tasks=total,
        done_tasks=done,
        in_progress_tasks=in_progress,
        todo_tasks=todo,
        progress=progress,
        overdue_tasks=overdue,
    )


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
