from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MilestoneBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    due_date: date | None = None


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    due_date: date | None = None
    status: str | None = None  # active / done

    @model_validator(mode="after")
    def _reject_explicit_null(self) -> "MilestoneUpdate":
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name 不能为空")
        return self


class MilestoneOut(MilestoneBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    status: str
    created_at: datetime
