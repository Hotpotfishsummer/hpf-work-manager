"""评论端点：任务评论 + 项目评论（工作方向指示）。

所有权：一律按「所属项目归当前用户」校验；访问他人评论按不存在处理（404），
不泄露其存在。
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from app.core.events import publish
from app.deps import CurrentUser, DbDep
from app.models import Comment
from app.routers.projects import _get_owned_project
from app.routers.tasks import _get_task
from app.services.comments import (
    comment_to_dict,
    list_project_comments,
    list_task_comments,
    owned_comment_project_id,
    project_comment_summaries,
    set_resolved,
)

router = APIRouter(tags=["comments"])


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        # 纯空白不算内容（min_length 只数字符，拦不住）
        if not v.strip():
            raise ValueError("评论内容不能为空")
        return v


class CommentResolve(BaseModel):
    # 缺省即「标记已处理」；显式传 false 用于撤销
    resolved: bool = True


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int | None
    project_id: int | None
    author_id: int | None
    author_username: str
    content: str
    created_at: datetime
    resolved_at: datetime | None
    is_direction: bool = False
    resolved: bool = False


class ProjectCommentSummaryLatest(BaseModel):
    id: int
    content: str
    author_username: str
    created_at: datetime | None


class ProjectCommentSummary(BaseModel):
    project_id: int
    project_name: str
    open_count: int
    total_count: int
    latest: ProjectCommentSummaryLatest | None


def _out(c: Comment) -> CommentOut:
    return CommentOut.model_validate(comment_to_dict(c))


# ---------- 项目评论（工作方向指示） ----------


@router.get("/comments/project-summary", response_model=list[ProjectCommentSummary])
async def get_project_comment_summary(user: CurrentUser, db: DbDep):
    """负责人名下所有「有项目指示」的项目概览，主页的指示入口用。"""
    return await project_comment_summaries(db, user.id)


@router.get(
    "/projects/{project_id}/comments", response_model=list[CommentOut]
)
async def list_project_comments_endpoint(
    project_id: int,
    user: CurrentUser,
    db: DbDep,
    include_resolved: bool = False,
):
    await _get_owned_project(db, user, project_id)
    rows = await list_project_comments(
        db, project_id, include_resolved=include_resolved
    )
    return [_out(c) for c in rows]


@router.post(
    "/projects/{project_id}/comments", response_model=CommentOut, status_code=201
)
async def create_project_comment(
    project_id: int, payload: CommentCreate, user: CurrentUser, db: DbDep
):
    await _get_owned_project(db, user, project_id)
    comment = Comment(
        project_id=project_id,
        author_id=user.id,
        author_username=user.username,
        content=payload.content.strip(),
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    await publish(project_id, "created", "comment", comment.id)
    return _out(comment)


@router.post("/comments/{comment_id}/resolve", response_model=CommentOut)
async def resolve_comment(
    comment_id: int, user: CurrentUser, db: DbDep, payload: CommentResolve | None = None
):
    found = await owned_comment_project_id(db, comment_id, user.id)
    if found is None:
        raise HTTPException(status_code=404, detail="评论不存在")
    comment, pid = found
    if comment.project_id is None:
        raise HTTPException(
            status_code=400, detail="任务评论不支持标记已处理（仅项目指示可以）"
        )
    resolved = True if payload is None else payload.resolved
    comment = await set_resolved(db, comment, resolved)
    await publish(pid, "updated", "comment", comment.id)
    return _out(comment)


# ---------- 任务评论 ----------


@router.get("/tasks/{task_id}/comments", response_model=list[CommentOut])
async def list_comments(task_id: int, user: CurrentUser, db: DbDep):
    await _get_task(db, user, task_id)
    rows = await list_task_comments(db, task_id)
    return [_out(c) for c in rows]


@router.post("/tasks/{task_id}/comments", response_model=CommentOut, status_code=201)
async def create_comment(
    task_id: int, payload: CommentCreate, user: CurrentUser, db: DbDep
):
    task = await _get_task(db, user, task_id)
    comment = Comment(
        task_id=task_id,
        author_id=user.id,
        author_username=user.username,
        content=payload.content.strip(),
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    await publish(task.project_id, "created", "comment", comment.id)
    return _out(comment)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: int, user: CurrentUser, db: DbDep):
    found = await owned_comment_project_id(db, comment_id, user.id)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
    comment, pid = found
    await db.delete(comment)
    await db.commit()
    await publish(pid, "deleted", "comment", comment_id)
