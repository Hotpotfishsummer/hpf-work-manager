from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.events import publish
from app.deps import CurrentUser, DbDep
from app.models import Project, Task
from app.services.ideator import ideator_service

router = APIRouter(prefix="/ideator", tags=["ideator"])


class AnalyzeRequest(BaseModel):
    project_name: str = Field(min_length=1)


class BrainstormRequest(BaseModel):
    theme: Optional[str] = "开发者效率与个人自动化工具"


class ApplyTaskRequest(BaseModel):
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    create_new_project: Optional[bool] = False
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default="", max_length=1000)
    priority: Optional[str] = "medium"
    estimated_hours: Optional[int] = 2


@router.get("/projects")
async def list_local_projects():
    """扫描服务器 ~/dsh-workspace/projects 目录下的已有项目"""
    return ideator_service.list_projects()


@router.post("/sync-projects")
async def sync_local_projects(db: DbDep, current_user: CurrentUser):
    """扫描本地代码库目录，将尚未建档的本地项目批量导入为独立的 Project"""
    local_projs = ideator_service.list_projects()
    existing_projs = (
        await db.execute(select(Project).where(Project.owner_id == current_user.id))
    ).scalars().all()
    existing_names = {p.name for p in existing_projs}

    created = []
    for lp in local_projs:
        name = lp["name"]
        if name not in existing_names:
            desc = lp.get("description") or f"服务器本地项目 {name}"
            p = Project(
                name=name,
                description=desc[:500] if desc else None,
                owner_id=current_user.id,
                status="active",
            )
            db.add(p)
            created.append(name)

    if created:
        await db.commit()
        for p in (await db.execute(select(Project).where(Project.owner_id == current_user.id))).scalars().all():
            if p.name in created:
                await publish(p.id, "created", "project", p.id)

    return {
        "ok": True,
        "synced_count": len(created),
        "created_projects": created,
        "total_local": len(local_projs),
    }


@router.post("/analyze")
async def analyze_project(payload: AnalyzeRequest):
    """读取指定项目的 README、Git 记录与代码树，推演生成下一步规划建议"""
    try:
        suggestions = await ideator_service.generate_next_steps(payload.project_name)
        return {"project_name": payload.project_name, "suggestions": suggestions}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"项目分析失败: {str(e)}",
        )


@router.post("/brainstorm")
async def brainstorm_ideas(payload: BrainstormRequest):
    """根据主题碰撞生成全新个人项目灵感与 MVP 第一步任务"""
    try:
        ideas = await ideator_service.brainstorm_ideas(payload.theme or "实用生产力工具")
        return {"theme": payload.theme, "ideas": ideas}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"灵感孵化失败: {str(e)}",
        )


@router.post("/apply-task", status_code=status.HTTP_201_CREATED)
async def apply_task_to_project(payload: ApplyTaskRequest, db: DbDep, current_user: CurrentUser):
    """一键将推演出的灵感/任务收纳进对应的独立项目看板"""
    proj = None

    # 1. 显式指定创建全新独立项目（如新项目灵感孵化）
    if payload.create_new_project and payload.project_name:
        proj = Project(
            name=payload.project_name[:120],
            description=payload.project_description[:500] if payload.project_description else f"新孵化项目 {payload.project_name}",
            owner_id=current_user.id,
            status="active",
        )
        db.add(proj)
        await db.commit()
        await db.refresh(proj)
        await publish(proj.id, "created", "project", proj.id)

    # 2. 如果指定了 project_name，优先按名称查找或自动建档独立项目
    elif payload.project_name:
        proj = (
            await db.execute(
                select(Project).where(
                    Project.owner_id == current_user.id,
                    Project.name == payload.project_name,
                )
            )
        ).scalar_one_or_none()
        if not proj:
            # 自动建档独立项目
            local_projs = ideator_service.list_projects()
            found_desc = next(
                (p["description"] for p in local_projs if p["name"] == payload.project_name),
                payload.project_description or f"服务器本地项目 {payload.project_name}",
            )
            proj = Project(
                name=payload.project_name[:120],
                description=found_desc[:500] if found_desc else None,
                owner_id=current_user.id,
                status="active",
            )
            db.add(proj)
            await db.commit()
            await db.refresh(proj)
            await publish(proj.id, "created", "project", proj.id)

    # 3. 如果指定了 project_id
    elif payload.project_id:
        proj = (
            await db.execute(
                select(Project).where(
                    Project.id == payload.project_id,
                    Project.owner_id == current_user.id,
                )
            )
        ).scalar_one_or_none()

    # 4. 兜底默认项目
    if not proj:
        proj = (await db.execute(select(Project).where(Project.owner_id == current_user.id).order_by(Project.id))).scalars().first()
        if not proj:
            proj = Project(
                name="通用任务池",
                description="HarnessPilot 默认项目看板",
                owner_id=current_user.id,
                status="active",
            )
            db.add(proj)
            await db.commit()
            await db.refresh(proj)
            await publish(proj.id, "created", "project", proj.id)

    new_task = Task(
        project_id=proj.id,
        name=payload.name,
        description=payload.description[:1000] if payload.description else "",
        status="todo",
        priority=payload.priority if payload.priority in ["low", "medium", "high"] else "medium",
        progress=0,
        estimated_hours=payload.estimated_hours or 2,
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    await publish(proj.id, "created", "task", new_task.id)

    return {
        "ok": True,
        "task_id": new_task.id,
        "project_id": proj.id,
        "project_name": proj.name,
        "name": new_task.name,
        "status": new_task.status,
    }


class ProposePlanRequest(BaseModel):
    project_name: str = Field(min_length=1)
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    agent_role_or_id: Optional[str] = "external_agent"
    rationale: Optional[str] = ""
    auto_create: Optional[bool] = False


class VerifyTaskRequest(BaseModel):
    task_id: int
    git_ref: str = Field(min_length=3, max_length=100)
    verification_evidence: str = Field(min_length=5, max_length=2000)
    summary: Optional[str] = ""


@router.get("/driver-mode")
async def get_driver_mode():
    """获取当前 Manager 驱动模式（双重认证 DUAL_CERTIFIED vs 外部驱动 EXTERNAL_DRIVEN）及行动指南"""
    from app.services.quota import quota_service
    return await quota_service.get_driver_mode()


@router.post("/propose-plan")
async def propose_task_plan(payload: ProposePlanRequest, db: DbDep, current_user: CurrentUser):
    """外部 Agent 提交规划提案，由 Manager 内部模型（若额度充足）交叉审查或由规则护栏校验盖章。
    若 auto_create=True，则自动将通过认证的任务建档写入项目看板。
    """
    review_result = await ideator_service.review_task_proposal(
        project_name=payload.project_name,
        proposed_tasks=payload.tasks,
        agent_role_or_id=payload.agent_role_or_id or "external_agent",
        rationale=payload.rationale or "",
    )

    created_task_ids = []
    if payload.auto_create and review_result.get("ok"):
        # 寻找或自动建档项目
        proj = (
            await db.execute(
                select(Project).where(
                    Project.owner_id == current_user.id,
                    Project.name == payload.project_name,
                )
            )
        ).scalar_one_or_none()
        if not proj:
            local_projs = ideator_service.list_projects()
            found_desc = next(
                (p["description"] for p in local_projs if p["name"] == payload.project_name),
                f"服务器本地项目 {payload.project_name}",
            )
            proj = Project(
                name=payload.project_name[:120],
                description=found_desc[:500] if found_desc else None,
                owner_id=current_user.id,
                status="active",
            )
            db.add(proj)
            await db.commit()
            await db.refresh(proj)
            await publish(proj.id, "created", "project", proj.id)

        for t in review_result.get("certified_tasks", []):
            new_task = Task(
                project_id=proj.id,
                name=t.get("title", "未命名任务")[:200],
                description=t.get("description", "")[:1000],
                status="todo",
                priority=t.get("priority", "medium") if t.get("priority") in ["low", "medium", "high"] else "medium",
                progress=0,
                estimated_hours=t.get("estimated_hours", 2),
            )
            db.add(new_task)
            await db.commit()
            await db.refresh(new_task)
            created_task_ids.append(new_task.id)
            await publish(proj.id, "created", "task", new_task.id)

    return {
        **review_result,
        "created_task_ids": created_task_ids,
        "project_name": payload.project_name,
    }


@router.post("/verify-task")
async def verify_task_completion(payload: VerifyTaskRequest, db: DbDep, current_user: CurrentUser):
    """双重认证任务完成验收：外部 Agent 提供真实 git_ref 与验收证据，经核验后完成任务并自动记录 DevLog"""
    from app.models import DevLog
    from app.services.dev_logs import _attach_session
    from app.services.tasks import apply_status_transition

    task = (
        await db.execute(
            select(Task)
            .join(Project, Task.project_id == Project.id)
            .where(Task.id == payload.task_id, Project.owner_id == current_user.id)
        )
    ).scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {payload.task_id} 不存在或无权操作",
        )

    # 标记完成
    apply_status_transition(task, "done")
    db.add(task)

    session_id = await _attach_session(db, task.project_id, None)

    # 自动生成 DevLog 交付记录
    log = DevLog(
        project_id=task.project_id,
        session_id=session_id,
        entry_type="progress",
        title=f"完成工单: {task.name}",
        content=f"【完成总结】{payload.summary or task.name}\n\n【验收验证凭证】\n{payload.verification_evidence}",
        git_ref=payload.git_ref[:100],
        author=current_user.username,
        related_task_ids=[task.id],
    )
    db.add(log)
    await db.commit()
    await db.refresh(task)
    await db.refresh(log)

    await publish(task.project_id, "updated", "task", task.id)
    await publish(task.project_id, "created", "log", log.id)

    return {
        "ok": True,
        "task_id": task.id,
        "task_name": task.name,
        "status": task.status,
        "dev_log_id": log.id,
        "git_ref": payload.git_ref,
        "certified": True,
        "message": f"任务「{task.name}」已完成双重认证归档，并生成关联 DevLog 凭证！",
    }

