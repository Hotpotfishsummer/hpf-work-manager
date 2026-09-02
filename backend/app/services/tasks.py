"""任务相关共享业务逻辑：状态机与序列化。

REST router 与 MCP server 复用，避免逻辑分叉。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, TaskDependency
from app.schemas import TaskOut
from app.services.stats import is_overdue
from app.utils.time import utcnow


def apply_status_transition(task: Task, status: str) -> None:
    """状态流转规则：done → progress=100 + completed_at；否则清空 completed_at。"""
    if status == "done":
        task.status = "done"
        task.progress = 100
        task.completed_at = task.completed_at or utcnow()
    else:
        task.status = status
        task.completed_at = None


def apply_task_update(task: Task, data: dict) -> None:
    """将更新字段应用到 task，含状态机与 progress 钳制。`data` 应为已剔除未设字段的 dict。"""
    if "status" in data:
        apply_status_transition(task, data["status"])
    if "progress" in data and task.status != "done":
        task.progress = max(0, min(100, data["progress"]))
    for key in (
        "name",
        "description",
        "milestone_id",
        "priority",
        "start_date",
        "due_date",
        "estimated_hours",
    ):
        if key in data:
            setattr(task, key, data[key])


def to_out(task: Task, depends_on: list[int] | None = None) -> TaskOut:
    """序列化任务；传入 depends_on（列表端点应批量取好后传入，避免 N+1）。"""
    out = TaskOut.model_validate(task)
    out.overdue = is_overdue(task)
    if depends_on is not None:
        out.depends_on = sorted(depends_on)
    return out


async def get_task_depends(db: AsyncSession, task_id: int) -> list[int]:
    """单任务的前置依赖 id 列表。"""
    rows = (
        await db.execute(
            select(TaskDependency.depends_on_task_id).where(TaskDependency.task_id == task_id)
        )
    ).scalars().all()
    return sorted(rows)


async def get_project_depends_map(db: AsyncSession, project_id: int) -> dict[int, list[int]]:
    """项目内全部依赖边按 task_id 分组（列表序列化一次取全，避免 N+1）。"""
    rows = (
        await db.execute(
            select(TaskDependency.task_id, TaskDependency.depends_on_task_id)
            .join(Task, TaskDependency.task_id == Task.id)
            .where(Task.project_id == project_id)
        )
    ).all()
    mapping: dict[int, list[int]] = {}
    for tid, dep in rows:
        mapping.setdefault(tid, []).append(dep)
    return mapping


async def ensure_no_cycle(db: AsyncSession, task_id: int, depends_on_task_id: int) -> None:
    """环检测：沿 depends_on 链从新前置任务向上游遍历，若能回到 task_id 则成环。

    REST 与 MCP 共用；成环抛 ValueError（调用方转 400/工具错误）。
    """
    if task_id == depends_on_task_id:
        raise ValueError("任务不能依赖自身")
    frontier = [depends_on_task_id]
    seen = set(frontier)
    while frontier:
        rows = (
            await db.execute(
                select(TaskDependency.depends_on_task_id).where(
                    TaskDependency.task_id.in_(frontier)
                )
            )
        ).scalars().all()
        nxt = [d for d in rows if d not in seen]
        if task_id in nxt:
            raise ValueError(f"添加依赖会形成循环：任务 {task_id} 已在任务 {depends_on_task_id} 的上游链路中")
        seen.update(nxt)
        frontier = nxt