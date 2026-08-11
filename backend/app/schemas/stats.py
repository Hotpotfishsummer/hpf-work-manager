from datetime import date

from pydantic import BaseModel

from app.schemas.task import TaskOut


class OverdueTask(BaseModel):
    id: int
    name: str
    due_date: date | None
    days_late: int
    priority: str


class ProjectStats(BaseModel):
    total_tasks: int
    done_tasks: int
    in_progress_tasks: int
    todo_tasks: int
    progress: float  # 0-100，完成任务数/总任务数
    overdue_tasks: list[OverdueTask]


class BurndownPoint(BaseModel):
    date: str
    ideal_remaining: int
    actual_remaining: int


class GanttDependency(BaseModel):
    task_id: int
    depends_on_task_id: int


class GanttTask(BaseModel):
    id: str
    name: str
    start: str
    end: str
    progress: int
    dependencies: str
    overdue: bool
    status: str


class GanttData(BaseModel):
    tasks: list[GanttTask]
    project_start: str
    project_end: str
