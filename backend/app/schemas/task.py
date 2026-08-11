from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

TASK_STATUS = {"todo", "in_progress", "done"}
TASK_PRIORITY = {"low", "medium", "high"}


class TaskBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    milestone_id: int | None = None
    priority: str = "medium"
    status: str = "todo"
    progress: int = Field(default=0, ge=0, le=100)
    start_date: date | None = None
    due_date: date | None = None
    estimated_hours: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check(self) -> "TaskBase":
        if self.status not in TASK_STATUS:
            raise ValueError(f"status 必须为 {sorted(TASK_STATUS)} 之一")
        if self.priority not in TASK_PRIORITY:
            raise ValueError(f"priority 必须为 {sorted(TASK_PRIORITY)} 之一")
        return self


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    milestone_id: int | None = None
    priority: str | None = None
    status: str | None = None
    progress: int | None = Field(default=None, ge=0, le=100)
    start_date: date | None = None
    due_date: date | None = None
    estimated_hours: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check(self) -> "TaskUpdate":
        if self.status is not None and self.status not in TASK_STATUS:
            raise ValueError(f"status 必须为 {sorted(TASK_STATUS)} 之一")
        if self.priority is not None and self.priority not in TASK_PRIORITY:
            raise ValueError(f"priority 必须为 {sorted(TASK_PRIORITY)} 之一")
        return self


class TaskBulkUpdate(BaseModel):
    ids: list[int] = Field(min_length=1)
    data: TaskUpdate


class TaskOut(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    completed_at: datetime | None
    created_at: datetime
    # 派生字段：是否延期（后端计算，不落库）
    overdue: bool = False
