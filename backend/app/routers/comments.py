"""任务评论端点（P5 · API/MCP 先行，前端 UI 后续接入）。

所有权：task 归属校验复用 _get_task（JOIN Project owner_id）；
删除权限 = 项目 owner（当前系统作者即 owner）。
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.events import publish
from app.deps import CurrentUser, DbDep
from app.models import Comment, Project, Task
from app.routers.tasks import _get_task

router = APIRouter(tags=["comments"])


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: int
    task_id: int
    author_id: int | None
    author_username: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


def _out(c: Comment) -> CommentOut:
    return CommentOut.model_validate(c)


@router.get("/tasks/{task_id}/comments", response_model=list[CommentOut])
async def list_comments(task_id: int, user: CurrentUser, db: DbDep):
    await _get_task(db, user, task_id)
    rows = (
        await db.execute(
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.created_at.asc(), Comment.id.asc())
        )
    ).scalars().all()
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
        content=payload.content,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    await publish(task.project_id, "created", "comment", comment.id)
    return _out(comment)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: int, user: CurrentUser, db: DbDep):
    comment = (
        await db.execute(
            select(Comment)
            .join(Task, Comment.task_id == Task.id)
            .join(Project, Task.project_id == Project.id)
            .where(Comment.id == comment_id, Project.owner_id == user.id)
        )
    ).scalar_one_or_none()
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
    pid = (
        await db.execute(select(Task.project_id).where(Task.id == comment.task_id))
    ).scalar_one()
    await db.delete(comment)
    await db.commit()
    await publish(pid, "deleted", "comment", comment_id)
