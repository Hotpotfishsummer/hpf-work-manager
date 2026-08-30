from fastapi import Query, APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.events import publish
from app.deps import CurrentUser, DbDep
from app.models import Milestone, Project
from app.routers.projects import _get_owned_project
from app.schemas import MilestoneCreate, MilestoneOut, MilestoneUpdate

router = APIRouter(tags=["milestones"])


async def _get_milestone(db: DbDep, user: CurrentUser, milestone_id: int) -> Milestone:
    milestone = (
        await db.execute(
            select(Milestone)
            .join(Project, Milestone.project_id == Project.id)
            .where(Milestone.id == milestone_id, Project.owner_id == user.id)
        )
    ).scalar_one_or_none()
    if milestone is None:
        raise HTTPException(status_code=404, detail="里程碑不存在")
    return milestone


@router.get("/projects/{project_id}/milestones", response_model=list[MilestoneOut])
async def list_milestones(
    project_id: int,
    user: CurrentUser,
    db: DbDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    await _get_owned_project(db, user, project_id)
    milestones = (
        await db.execute(
            select(Milestone)
            .where(Milestone.project_id == project_id)
            .order_by(Milestone.due_date.asc().nulls_last())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()
    return milestones


@router.post(
    "/projects/{project_id}/milestones",
    response_model=MilestoneOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_milestone(
    project_id: int, payload: MilestoneCreate, user: CurrentUser, db: DbDep
):
    await _get_owned_project(db, user, project_id)
    milestone = Milestone(project_id=project_id, **payload.model_dump())
    db.add(milestone)
    await db.commit()
    await db.refresh(milestone)
    await publish(project_id, "created", "milestone", milestone.id)
    return milestone


@router.put("/milestones/{milestone_id}", response_model=MilestoneOut)
async def update_milestone(
    milestone_id: int, payload: MilestoneUpdate, user: CurrentUser, db: DbDep
):
    milestone = await _get_milestone(db, user, milestone_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(milestone, key, value)
    await db.commit()
    await db.refresh(milestone)
    await publish(milestone.project_id, "updated", "milestone", milestone.id)
    return milestone


@router.delete("/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_milestone(milestone_id: int, user: CurrentUser, db: DbDep):
    milestone = await _get_milestone(db, user, milestone_id)
    pid, mid = milestone.project_id, milestone.id
    await db.delete(milestone)
    await db.commit()
    await publish(pid, "deleted", "milestone", mid)
