"""任务相关共享业务逻辑：状态机与序列化。

REST router 与 MCP server 复用，避免逻辑分叉。
"""

from app.models import Task
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


def to_out(task: Task) -> TaskOut:
    out = TaskOut.model_validate(task)
    out.overdue = is_overdue(task)
    return out