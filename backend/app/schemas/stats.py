from datetime import date

from pydantic import BaseModel


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
    weighted_progress: float  # 0-100，工时加权：Σ(权重×任务进度)/Σ(权重)，权重=预估工时（未填按 1）
    estimated_hours_total: float | None  # 已填预估工时的任务总工时；无任务填工时为 None
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


class DevLogStats(BaseModel):
    total: int
    today_count: int
    open_todos: int
    open_difficulties: int
    open_blockers: int
    decisions: int
    type_counts: dict[str, int]
    latest_activity: str | None


class DevReportRequest(BaseModel):
    start: date | None = None
    end: date | None = None


class DevReport(BaseModel):
    text: str


class DashboardProjectCard(BaseModel):
    project_id: int
    name: str
    status: str
    progress: float
    weighted_progress: float  # 工时加权进度（权重=预估工时，未填按 1）
    total_tasks: int
    done_tasks: int
    overdue_count: int


class DashboardOverdueItem(BaseModel):
    id: int
    name: str
    project_id: int
    project_name: str
    due_date: date | None
    days_late: int
    priority: str


class DashboardRecentLog(BaseModel):
    id: int
    project_id: int
    project_name: str
    entry_type: str
    title: str
    author: str
    created_at: str


class DashboardSession(BaseModel):
    id: int
    project_id: int
    project_name: str
    title: str | None
    log_count: int
    started_at: str


class DashboardOverview(BaseModel):
    total_projects: int
    active_projects: int
    projects: list[DashboardProjectCard]
    overdue_tasks: list[DashboardOverdueItem]
    recent_logs: list[DashboardRecentLog]
    active_sessions: list[DashboardSession]
    today_completed: int
