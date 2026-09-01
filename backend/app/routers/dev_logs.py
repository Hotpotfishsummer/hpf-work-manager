from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.events import publish
from app.deps import CurrentUser, DbDep
from app.models import DevLog, DevSession, Project
from app.routers.projects import _get_owned_project
from app.schemas import (
    DevLogCreate,
    DevLogOut,
    DevLogStats,
    DevLogUpdate,
    DevReport,
    DevReportRequest,
    DevSessionCreate,
    DevSessionEnd,
    DevSessionOut,
)
from app.services.dev_logs import (
    _attach_session,
    _validate_related_tasks,
    apply_log_update,
    get_dev_log_stats,
    get_dev_report,
    session_to_dict,
)
from app.utils.time import utcnow

router = APIRouter(tags=["dev-logs"])


async def _get_log(db: DbDep, user: CurrentUser, log_id: int) -> DevLog:
    log = (
        await db.execute(
            select(DevLog)
            .join(Project, DevLog.project_id == Project.id)
            .where(DevLog.id == log_id, Project.owner_id == user.id)
        )
    ).scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return log


async def _get_session(db: DbDep, user: CurrentUser, session_id: int) -> DevSession:
    s = (
        await db.execute(
            select(DevSession)
            .join(Project, DevSession.project_id == Project.id)
            .where(DevSession.id == session_id, Project.owner_id == user.id)
        )
    ).scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    return s


# ---- 开发记录条目 ----


@router.get("/projects/{project_id}/logs", response_model=list[DevLogOut])
async def list_logs(
    project_id: int,
    user: CurrentUser,
    db: DbDep,
    entry_type: str | None = Query(default=None),
    log_status: str | None = Query(default=None, alias="status"),
    since: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    await _get_owned_project(db, user, project_id)
    stmt = select(DevLog).where(DevLog.project_id == project_id)
    if entry_type:
        stmt = stmt.where(DevLog.entry_type == entry_type)
    if log_status:
        stmt = stmt.where(DevLog.status == log_status)
    if since:
        stmt = stmt.where(func.date(DevLog.created_at) >= since)
    rows = (
        (await db.execute(stmt.order_by(DevLog.created_at.desc()).offset(offset).limit(limit)))
        .scalars()
        .all()
    )
    return rows


@router.post(
    "/projects/{project_id}/logs",
    response_model=DevLogOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_log(
    project_id: int, payload: DevLogCreate, user: CurrentUser, db: DbDep
):
    await _get_owned_project(db, user, project_id)
    data = payload.model_dump()
    data.pop("session_id", None)
    try:
        await _validate_related_tasks(db, project_id, data.get("related_task_ids"))
        session_id = await _attach_session(db, project_id, payload.session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    log = DevLog(
        project_id=project_id,
        session_id=session_id,
        author=user.username,
        **data,
    )
    if log.status == "done":
        log.resolved_at = utcnow()
    db.add(log)
    await db.commit()
    await db.refresh(log)
    await publish(project_id, "created", "log", log.id)
    return log


@router.get("/projects/{project_id}/logs/stats", response_model=DevLogStats)
async def logs_stats(project_id: int, user: CurrentUser, db: DbDep):
    await _get_owned_project(db, user, project_id)
    return await get_dev_log_stats(db, project_id)


@router.post("/projects/{project_id}/logs/report", response_model=DevReport)
async def logs_report(
    project_id: int, payload: DevReportRequest, user: CurrentUser, db: DbDep
):
    await _get_owned_project(db, user, project_id)
    text = await get_dev_report(db, project_id, payload.start, payload.end)
    return DevReport(text=text)


@router.get("/logs/{log_id}", response_model=DevLogOut)
async def get_log(log_id: int, user: CurrentUser, db: DbDep):
    return await _get_log(db, user, log_id)


@router.put("/logs/{log_id}", response_model=DevLogOut)
async def update_log(
    log_id: int, payload: DevLogUpdate, user: CurrentUser, db: DbDep
):
    log = await _get_log(db, user, log_id)
    data = payload.model_dump(exclude_unset=True)
    if "related_task_ids" in data:
        try:
            await _validate_related_tasks(db, log.project_id, data.get("related_task_ids"))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
    apply_log_update(log, data)
    await db.commit()
    await db.refresh(log)
    await publish(log.project_id, "updated", "log", log.id)
    return log


@router.post("/logs/{log_id}/resolve", response_model=DevLogOut)
async def resolve_log(log_id: int, user: CurrentUser, db: DbDep):
    log = await _get_log(db, user, log_id)
    if log.entry_type not in ("todo", "blocker"):
        raise HTTPException(status_code=400, detail="仅 todo / blocker 条目可标记完成")
    log.status = "done"
    log.resolved_at = utcnow()
    await db.commit()
    await db.refresh(log)
    await publish(log.project_id, "updated", "log", log.id)
    return log


@router.delete("/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_log(log_id: int, user: CurrentUser, db: DbDep):
    log = await _get_log(db, user, log_id)
    pid = log.project_id
    await db.delete(log)
    await db.commit()
    await publish(pid, "deleted", "log", log_id)


# ---- 开发会话 ----


@router.post(
    "/projects/{project_id}/sessions",
    response_model=DevSessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    project_id: int, payload: DevSessionCreate, user: CurrentUser, db: DbDep
):
    await _get_owned_project(db, user, project_id)
    s = DevSession(
        project_id=project_id,
        title=payload.title,
        author=user.username,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    await publish(project_id, "created", "session", s.id)
    return session_to_dict(s)


@router.post("/sessions/{session_id}/end", response_model=DevSessionOut)
async def end_session(
    session_id: int, payload: DevSessionEnd, user: CurrentUser, db: DbDep
):
    s = await _get_session(db, user, session_id)
    s.ended_at = utcnow()
    if payload.summary is not None:
        s.summary = payload.summary
    await db.commit()
    await db.refresh(s)
    count = (
        await db.execute(
            select(func.count(DevLog.id)).where(DevLog.session_id == s.id)
        )
    ).scalar_one()
    await publish(s.project_id, "updated", "session", s.id)
    return session_to_dict(s, count)


@router.get("/projects/{project_id}/sessions", response_model=list[DevSessionOut])
async def list_sessions(project_id: int, user: CurrentUser, db: DbDep):
    await _get_owned_project(db, user, project_id)
    sessions = (
        (
            await db.execute(
                select(DevSession)
                .where(DevSession.project_id == project_id)
                .order_by(DevSession.started_at.desc())
            )
        )
        .scalars()
        .all()
    )
    counts = dict(
        (
            await db.execute(
                select(DevLog.session_id, func.count(DevLog.id))
                .where(DevLog.project_id == project_id, DevLog.session_id.is_not(None))
                .group_by(DevLog.session_id)
            )
        ).all()
    )
    return [session_to_dict(s, counts.get(s.id, 0)) for s in sessions]
