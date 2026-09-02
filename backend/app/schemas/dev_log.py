from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

DEV_LOG_TYPES = {"progress", "difficulty", "todo", "decision", "blocker", "milestone", "note"}
DEV_LOG_STATUS = {"open", "done"}
SEVERITY = {"low", "medium", "high"}

# status 仅用于 todo/blocker；severity 仅用于 difficulty/blocker
_STATUS_TYPES = {"todo", "blocker"}
_SEVERITY_TYPES = {"difficulty", "blocker"}


class DevLogBase(BaseModel):
    entry_type: str = "note"
    status: str = "open"
    severity: str | None = None
    title: str = Field(min_length=1, max_length=200)
    content: str | None = None
    related_task_ids: list[int] | None = None
    git_ref: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _check(self) -> "DevLogBase":
        if self.entry_type not in DEV_LOG_TYPES:
            raise ValueError(f"entry_type 必须为 {sorted(DEV_LOG_TYPES)} 之一")
        if self.status not in DEV_LOG_STATUS:
            raise ValueError(f"status 必须为 {sorted(DEV_LOG_STATUS)} 之一")
        if self.severity is not None and self.severity not in SEVERITY:
            raise ValueError(f"severity 必须为 {sorted(SEVERITY)} 之一")
        if self.severity is not None and self.entry_type not in _SEVERITY_TYPES:
            raise ValueError("severity 仅可用于 difficulty / blocker 条目")
        if self.status == "done" and self.entry_type not in _STATUS_TYPES:
            raise ValueError("status 仅可用于 todo / blocker 条目")
        return self


class DevLogCreate(DevLogBase):
    session_id: int | None = None


class DevLogUpdate(BaseModel):
    entry_type: str | None = None
    status: str | None = None
    severity: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = None
    related_task_ids: list[int] | None = None
    git_ref: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _check(self) -> "DevLogUpdate":
        if self.entry_type is not None and self.entry_type not in DEV_LOG_TYPES:
            raise ValueError(f"entry_type 必须为 {sorted(DEV_LOG_TYPES)} 之一")
        if self.status is not None and self.status not in DEV_LOG_STATUS:
            raise ValueError(f"status 必须为 {sorted(DEV_LOG_STATUS)} 之一")
        if self.severity is not None and self.severity not in SEVERITY:
            raise ValueError(f"severity 必须为 {sorted(SEVERITY)} 之一")
        return self


class DevLogOut(DevLogBase):
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _coerce(self) -> "DevLogOut":
        if self.related_task_ids is None:
            self.related_task_ids = []
        return self

    id: int
    project_id: int
    session_id: int | None
    author: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class DevLogPage(BaseModel):
    """带总数的分页信封（?with_total=1 时返回；默认仍是纯列表，向后兼容）。"""

    items: list[DevLogOut]
    total: int
