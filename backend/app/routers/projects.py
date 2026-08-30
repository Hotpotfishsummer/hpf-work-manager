from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.events import publish
from app.deps import CurrentUser, DbDep
from app.models import Project
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


async def _get_owned_project(db: DbDep, user: CurrentUser, project_id: int) -> Project:
    project = (
        await db.execute(
            select(Project).where(
                Project.id == project_id, Project.owner_id == user.id
            )
        )
    ).scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    user: CurrentUser,
    db: DbDep,
    status: str | None = Query(default=None, description="按状态过滤：active / archived"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(Project).where(Project.owner_id == user.id)
    if status:
        stmt = stmt.where(Project.status == status)
    projects = (
        await db.execute(
            stmt.order_by(Project.created_at.desc()).offset(offset).limit(limit)
        )
    ).scalars().all()
    return projects


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, user: CurrentUser, db: DbDep):
    project = Project(owner_id=user.id, **payload.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    await publish(project.id, "created", "project", project.id)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: int, user: CurrentUser, db: DbDep):
    return await _get_owned_project(db, user, project_id)


@router.put("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: int, payload: ProjectUpdate, user: CurrentUser, db: DbDep
):
    project = await _get_owned_project(db, user, project_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    await publish(project.id, "updated", "project", project.id)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, user: CurrentUser, db: DbDep):
    project = await _get_owned_project(db, user, project_id)
    pid = project.id
    await db.delete(project)
    await db.commit()
    await publish(pid, "deleted", "project", pid)