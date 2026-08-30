from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    start_date: date | None = None
    end_date: date | None = None


class ProjectCreate(ProjectBase):
    @model_validator(mode="after")
    def _check_date_order(self) -> "ProjectCreate":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("开始日期晚于截止日期")
        return self


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    status: str | None = None  # active / archived
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def _reject_explicit_null(self) -> "ProjectUpdate":
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name 不能为空")
        return self


class ProjectOut(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    created_at: datetime
