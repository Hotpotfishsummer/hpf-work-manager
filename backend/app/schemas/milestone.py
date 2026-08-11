from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MilestoneBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    due_date: date | None = None


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    due_date: date | None = None
    status: str | None = None  # active / done


class MilestoneOut(MilestoneBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    status: str
    created_at: datetime
