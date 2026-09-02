"""开发记录服务：DevLog/DevSession 的序列化、统计与报表生成。

REST 与 MCP 共用，避免业务逻辑分叉。"""

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DevLog, DevSession, Project, Task
from app.schemas import DevLogStats
from app.schemas.dev_log import _SEVERITY_TYPES, _STATUS_TYPES
from app.utils.time import display_day_bounds_utc, display_today, utcnow


def to_dict(log: DevLog) -> dict:
    return {
        "id": log.id,
        "project_id": log.project_id,
        "session_id": log.session_id,
        "entry_type": log.entry_type,
        "status": log.status,
        "severity": log.severity,
        "title": log.title,
        "content": log.content,
        "related_task_ids": log.related_task_ids or [],
        "git_ref": log.git_ref,
        "author": log.author,
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "updated_at": log.updated_at.isoformat() if log.updated_at else None,
        "resolved_at": log.resolved_at.isoformat() if log.resolved_at else None,
    }


def session_to_dict(s: DevSession, log_count: int = 0) -> dict:
    return {
        "id": s.id,
        "project_id": s.project_id,
        "title": s.title,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "summary": s.summary,
        "author": s.author,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "log_count": log_count,
    }


async def _validate_related_tasks(db: AsyncSession, project_id: int, ids: list[int] | None) -> None:
    """校验 related_task_ids 均属于本项目；任一越权即拒绝。"""
    if not ids:
        return
    rows = (
        (
            await db.execute(
                select(Task.id).where(
                    Task.id.in_(ids), Task.project_id == project_id
                )
            )
        )
        .scalars()
        .all()
    )
    if set(rows) != set(ids):
        raise ValueError("related_task_ids 中存在不属于该项目的任务")


async def _attach_session(db: AsyncSession, project_id: int, session_id: int | None) -> int | None:
    """校验 session 属于本项目并返回；无 session 且存在未结束会话时自动归入。"""
    if session_id is not None:
        row = (
            await db.execute(
                select(DevSession).where(
                    DevSession.id == session_id, DevSession.project_id == project_id
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise ValueError(f"会话 {session_id} 不存在")
        return session_id
    # 自动归入最近的未结束会话
    open_session = (
        await db.execute(
            select(DevSession)
            .where(DevSession.project_id == project_id, DevSession.ended_at.is_(None))
            .order_by(DevSession.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return open_session.id if open_session else None


def apply_log_update(log: DevLog, data: dict) -> None:
    """应用更新字段，并维护 status/severity/entry_type 的组合约束。"""
    entry_type = data.get("entry_type", log.entry_type)
    if data.get("entry_type") is not None:
        log.entry_type = entry_type
    if data.get("status") is not None:
        log.status = data["status"]
        if data["status"] == "done":
            log.resolved_at = utcnow()
        elif data["status"] == "open":
            log.resolved_at = None
    if data.get("severity") is not None:
        log.severity = data["severity"]
    if data.get("title") is not None:
        log.title = data["title"]
    if data.get("content") is not None:
        log.content = data["content"]
    if data.get("related_task_ids") is not None:
        log.related_task_ids = data["related_task_ids"]
    if data.get("git_ref") is not None:
        log.git_ref = data["git_ref"]
    # 组合约束：非 todo/blocker 强制 open；非 difficulty/blocker 清空 severity
    if entry_type not in _STATUS_TYPES:
        log.status = "open"
        log.resolved_at = None
    if entry_type not in _SEVERITY_TYPES:
        log.severity = None


async def get_dev_log_stats(db: AsyncSession, project_id: int) -> DevLogStats:
    rows = (
        await db.execute(
            select(DevLog.entry_type, func.count(DevLog.id)).where(
                DevLog.project_id == project_id
            ).group_by(DevLog.entry_type)
        )
    ).all()
    type_counts: dict[str, int] = {t: 0 for t in ["progress", "difficulty", "todo", "decision", "blocker", "milestone", "note"]}
    for entry_type, cnt in rows:
        type_counts[entry_type] = cnt

    day_start, day_end = display_day_bounds_utc(display_today())
    today_count = (
        await db.execute(
            select(func.count(DevLog.id)).where(
                DevLog.project_id == project_id,
                DevLog.created_at >= day_start,
                DevLog.created_at < day_end,
            )
        )
    ).scalar_one()

    open_todos = (
        await db.execute(
            select(func.count(DevLog.id)).where(
                DevLog.project_id == project_id,
                DevLog.entry_type == "todo",
                DevLog.status == "open",
            )
        )
    ).scalar_one()

    open_difficulties = (
        await db.execute(
            select(func.count(DevLog.id)).where(
                DevLog.project_id == project_id,
                DevLog.entry_type == "difficulty",
                DevLog.status == "open",
            )
        )
    ).scalar_one()

    open_blockers = (
        await db.execute(
            select(func.count(DevLog.id)).where(
                DevLog.project_id == project_id,
                DevLog.entry_type == "blocker",
                DevLog.status == "open",
            )
        )
    ).scalar_one()

    latest = (
        await db.execute(
            select(DevLog.created_at)
            .where(DevLog.project_id == project_id)
            .order_by(DevLog.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return DevLogStats(
        total=sum(type_counts.values()),
        today_count=today_count,
        open_todos=open_todos,
        open_difficulties=open_difficulties,
        open_blockers=open_blockers,
        decisions=type_counts["decision"],
        type_counts=type_counts,
        latest_activity=latest.isoformat() if latest else None,
    )


async def get_project_state(db: AsyncSession, project_id: int) -> dict:
    """上下文恢复聚合包：让新会话的 AI 一次拉取即可接续开发。"""
    async def _logs(entry_type: str, status: str | None, limit: int) -> list[dict]:
        stmt = (
            select(DevLog)
            .where(DevLog.project_id == project_id, DevLog.entry_type == entry_type)
        )
        if status:
            stmt = stmt.where(DevLog.status == status)
        rows = (
            (await db.execute(stmt.order_by(DevLog.created_at.desc()).limit(limit)))
            .scalars()
            .all()
        )
        return [to_dict(r) for r in rows]

    open_session = (
        await db.execute(
            select(DevSession)
            .where(DevSession.project_id == project_id, DevSession.ended_at.is_(None))
            .order_by(DevSession.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "description": project.description,
        }
        if project
        else None,
        "open_todos": await _logs("todo", "open", 20),
        "active_difficulties": await _logs("difficulty", "open", 10),
        "open_blockers": await _logs("blocker", "open", 10),
        "recent_progress": await _logs("progress", None, 5),
        "recent_decisions": await _logs("decision", None, 5),
        "active_session": session_to_dict(open_session) if open_session else None,
    }


_TYPE_LABEL = {
    "progress": "进展",
    "difficulty": "难点",
    "todo": "待办",
    "decision": "决策",
    "blocker": "阻塞",
    "milestone": "里程碑",
    "note": "备注",
}


async def get_dev_report(
    db: AsyncSession, project_id: int, start: date | None, end: date | None
) -> str:
    """生成一段可读的阶段汇报（Markdown）。AI 与人共用同一份口径。"""
    stmt = select(DevLog).where(DevLog.project_id == project_id)
    if start:
        stmt = stmt.where(DevLog.created_at >= datetime.combine(start, datetime.min.time()))
    if end:
        stmt = stmt.where(DevLog.created_at <= datetime.combine(end, datetime.max.time()))
    rows = (
        (await db.execute(stmt.order_by(DevLog.created_at.asc()))).scalars().all()
    )

    lines: list[str] = []
    range_txt = (
        f"（{start.isoformat()} ~ {end.isoformat()}）"
        if start or end
        else "（全部时间）"
    )
    lines.append(f"# 开发汇报 {range_txt}")
    lines.append("")

    if not rows:
        lines.append("该时间段内暂无开发记录。")
        return "\n".join(lines)

    for entry_type in ["progress", "milestone", "difficulty", "blocker", "todo", "decision", "note"]:
        group = [r for r in rows if r.entry_type == entry_type]
        if not group:
            continue
        lines.append(f"## {_TYPE_LABEL[entry_type]}")
        for r in group:
            severity = f" `[{r.severity}]`" if r.severity else ""
            status_mark = "（已解决）" if r.status == "done" else ""
            lines.append(f"- **{r.title}**{severity}{status_mark}")
            if r.content:
                lines.append(f"  - {r.content.strip()}")
            if r.related_task_ids:
                lines.append(f"  - 关联任务：{r.related_task_ids}")
            if r.git_ref:
                lines.append(f"  - git: `{r.git_ref}`")
            if r.author:
                lines.append(f"  - 来源：{r.author}（{r.created_at.date()}）")
        lines.append("")

    return "\n".join(lines)
