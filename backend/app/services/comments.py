"""评论服务层：任务评论 + 项目评论（工作方向指示）。

REST 与 MCP 共用，避免两边逻辑分叉。
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comment, Project, Task
from app.utils.time import utcnow

DIRECTIONS_LIMIT = 50


def comment_to_dict(c: Comment) -> dict:
    """REST 与 MCP 共用的评论序列化。"""
    return {
        "id": c.id,
        "task_id": c.task_id,
        "project_id": c.project_id,
        "author_id": c.author_id,
        "author_username": c.author_username,
        "content": c.content,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
        # 语义化：仅项目评论才有「是否已处理」的概念，任务评论恒视为待处理
        "is_direction": c.project_id is not None,
        "resolved": c.project_id is not None and c.resolved_at is not None,
    }


async def list_task_comments(db: AsyncSession, task_id: int) -> list[Comment]:
    rows = (
        await db.execute(
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.created_at.asc(), Comment.id.asc())
        )
    ).scalars().all()
    return list(rows)


async def list_project_comments(
    db: AsyncSession, project_id: int, *, include_resolved: bool = False
) -> list[Comment]:
    """项目指示，按时间升序（早写的在前，读起来是时间线）。"""
    stmt = select(Comment).where(Comment.project_id == project_id)
    if not include_resolved:
        stmt = stmt.where(Comment.resolved_at.is_(None))
    rows = (
        await db.execute(stmt.order_by(Comment.created_at.asc(), Comment.id.asc()))
    ).scalars().all()
    return list(rows)


async def get_open_directions(
    db: AsyncSession, project_id: int, limit: int = DIRECTIONS_LIMIT
) -> list[dict]:
    """未处理的项目指示 —— Agent 开工前的必读项（供 get_project_state 使用）。

    只取未处理的：已落实的旧指示不应反复出现在上下文里干扰判断。
    """
    comments = await list_project_comments(db, project_id)
    return [comment_to_dict(c) for c in comments[:limit]]


async def open_direction_counts(
    db: AsyncSession, project_ids: list[int] | None = None
) -> dict[int, int]:
    """各项目「未处理指示」数，一次聚合；project_ids 为 None 表示全部项目。"""
    stmt = (
        select(Comment.project_id, func.count(Comment.id))
        .where(Comment.project_id.is_not(None), Comment.resolved_at.is_(None))
        .group_by(Comment.project_id)
    )
    if project_ids is not None:
        if not project_ids:
            return {}
        stmt = stmt.where(Comment.project_id.in_(project_ids))
    rows = (await db.execute(stmt)).all()
    return {pid: cnt for pid, cnt in rows}


async def project_comment_summaries(db: AsyncSession, owner_id: int) -> list[dict]:
    """负责人视角的项目指示概览（主页用）：每个有指示的项目一行。

    返回 open_count / total_count / 最新一条未处理指示的预览。
    """
    stmt = (
        select(
            Comment.project_id,
            Project.name.label("project_name"),
            func.count(Comment.id).label("total"),
            func.count(Comment.resolved_at).label("resolved"),
        )
        .join(Project, Comment.project_id == Project.id)
        .where(Project.owner_id == owner_id, Comment.project_id.is_not(None))
        .group_by(Comment.project_id, Project.name)
    )
    rows = (await db.execute(stmt)).all()
    result = []
    for pid, name, total, resolved in rows:
        latest = (
            await db.execute(
                select(Comment)
                .where(Comment.project_id == pid, Comment.resolved_at.is_(None))
                .order_by(Comment.created_at.desc(), Comment.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        result.append(
            {
                "project_id": pid,
                "project_name": name,
                "open_count": total - resolved,
                "total_count": total,
                "latest": (
                    {
                        "id": latest.id,
                        "content": latest.content,
                        "author_username": latest.author_username,
                        "created_at": (
                            latest.created_at.isoformat() if latest.created_at else None
                        ),
                    }
                    if latest
                    else None
                ),
            }
        )
    result.sort(key=lambda r: (r["open_count"] == 0, r["project_name"]))
    return result


async def set_resolved(db: AsyncSession, comment: Comment, resolved: bool) -> Comment:
    """标记 / 取消标记项目指示为已处理。任务评论不支持（没有「落实」语义）。"""
    if comment.project_id is None:
        raise ValueError("只有项目评论可以标记为已处理")
    comment.resolved_at = utcnow() if resolved else None
    await db.commit()
    await db.refresh(comment)
    return comment


async def owned_comment_project_id(
    db: AsyncSession, comment_id: int, owner_id: int
) -> tuple[Comment, int] | None:
    """按 id 取评论并校验其所属项目归 owner 所有；返回 (评论, 项目 id)。

    任务评论与项目评论一视同仁：非本人项目的评论一律视为「不存在」。
    """
    comment = (
        await db.execute(
            select(Comment)
            .outerjoin(Task, Comment.task_id == Task.id)
            .outerjoin(Project, Project.id == func.coalesce(Task.project_id, Comment.project_id))
            .where(Comment.id == comment_id, Project.owner_id == owner_id)
        )
    ).scalar_one_or_none()
    if comment is None:
        return None
    if comment.project_id is not None:
        return comment, comment.project_id
    task_pid = (
        await db.execute(select(Task.project_id).where(Task.id == comment.task_id))
    ).scalar_one()
    return comment, task_pid


__all__ = [
    "comment_to_dict",
    "get_open_directions",
    "list_project_comments",
    "list_task_comments",
    "open_direction_counts",
    "owned_comment_project_id",
    "project_comment_summaries",
    "set_resolved",
]
