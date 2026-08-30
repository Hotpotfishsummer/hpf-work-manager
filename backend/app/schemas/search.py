from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    type: str  # "project" | "task" | "milestone"
    id: int
    name: str
    description: str | None = None
    project_id: int | None = None
    project_name: str | None = None
    status: str | None = None
    due_date: str | None = None


class SearchResponse(BaseModel):
    items: list[SearchResultItem]
    total: int


class SearchRequest(BaseModel):
    q: str = Field(..., min_length=2, description="搜索关键词，至少 2 字符")
    project_id: int | None = Field(default=None, description="可选：限定项目范围")
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)