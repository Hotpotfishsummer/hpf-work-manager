"""生成本地演示用 mock 数据（清空该用户下旧项目后重建）。

用法：
    cd backend && .venv/bin/python scripts/seed_mock.py
"""
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from app.core.security import hash_password
from app.database import AsyncSessionLocal
from app.models import DevLog, DevSession, Milestone, Project, Task, TaskDependency, User
from app.utils.time import utcnow

ADMIN = "admin"
PW = "admin123"

TODAY = date.today()


def d(offset: int) -> date:
    return TODAY + timedelta(days=offset)


def dt(offset: int) -> datetime:
    return datetime.combine(d(offset), time(0, 0), tzinfo=timezone.utc)


async def main() -> None:
    async with AsyncSessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.username == ADMIN))
        ).scalar_one_or_none()
        if not user:
            user = User(
                username=ADMIN,
                email="admin@example.com",
                hashed_password=hash_password(PW),
            )
            s.add(user)
            await s.flush()
        else:
            user.hashed_password = hash_password(PW)
        uid = user.id

        # 清空该用户旧项目（级联删除 tasks/milestones）
        old = (await s.execute(select(Project).where(Project.owner_id == uid))).scalars()
        for p in old:
            await s.delete(p)
        await s.flush()

        projects = []

        # ---- 项目 1：官网改版 2026 ----
        p1 = Project(
            owner_id=uid,
            name="官网改版 2026",
            description="品牌官网视觉与内容重构，含响应式与多语言。",
            status="active",
            start_date=d(-30),
            end_date=d(40),
        )
        s.add(p1)
        await s.flush()
        m1a = Milestone(project_id=p1.id, name="设计定稿", due_date=d(-5), status="done")
        m1b = Milestone(project_id=p1.id, name="开发联调", due_date=d(20), status="active")
        m1c = Milestone(project_id=p1.id, name="上线发布", due_date=d(40), status="active")
        s.add_all([m1a, m1b, m1c])
        await s.flush()
        t = [
            Task(project_id=p1.id, milestone_id=m1a.id, name="信息架构梳理", status="done", priority="high", progress=100, start_date=d(-30), due_date=d(-20), completed_at=dt(-20)),
            Task(project_id=p1.id, milestone_id=m1a.id, name="视觉稿设计", status="done", priority="high", progress=100, start_date=d(-22), due_date=d(-8), completed_at=dt(-8)),
            Task(project_id=p1.id, milestone_id=m1b.id, name="首页开发", status="in_progress", priority="high", progress=70, start_date=d(-6), due_date=d(8)),
            Task(project_id=p1.id, milestone_id=m1b.id, name="组件库搭建", status="in_progress", priority="medium", progress=45, start_date=d(-4), due_date=d(12)),
            Task(project_id=p1.id, milestone_id=m1b.id, name="多语言文案", status="todo", priority="medium", progress=0, start_date=d(2), due_date=d(18)),
            Task(project_id=p1.id, name="埋点与统计", status="todo", priority="low", progress=0, start_date=d(10), due_date=d(30)),
            Task(project_id=p1.id, name="遗留样式修复", status="todo", priority="low", progress=0, start_date=d(-12), due_date=d(-9)),  # 逾期
        ]
        s.add_all(t)
        await s.flush()
        # 依赖：首页开发 依赖 视觉稿设计；组件库 依赖 视觉稿设计
        s.add(TaskDependency(task_id=t[2].id, depends_on_task_id=t[1].id))
        s.add(TaskDependency(task_id=t[3].id, depends_on_task_id=t[1].id))
        projects.append(p1)

        # ---- 项目 2：移动 App v1.0 ----
        p2 = Project(
            owner_id=uid,
            name="移动 App v1.0",
            description="iOS / Android 双端首版，覆盖登录、项目看板与进度同步。",
            status="active",
            start_date=d(-20),
            end_date=d(60),
        )
        s.add(p2)
        await s.flush()
        m2a = Milestone(project_id=p2.id, name="需求评审", due_date=d(-10), status="done")
        m2b = Milestone(project_id=p2.id, name="Beta 内测", due_date=d(35), status="active")
        s.add_all([m2a, m2b])
        await s.flush()
        t2 = [
            Task(project_id=p2.id, milestone_id=m2a.id, name="需求评审会", status="done", priority="high", progress=100, start_date=d(-20), due_date=d(-12), completed_at=dt(-12)),
            Task(project_id=p2.id, milestone_id=m2b.id, name="登录与鉴权", status="done", priority="high", progress=100, start_date=d(-10), due_date=d(-2), completed_at=dt(-2)),
            Task(project_id=p2.id, milestone_id=m2b.id, name="看板交互", status="in_progress", priority="high", progress=60, start_date=d(0), due_date=d(22)),
            Task(project_id=p2.id, milestone_id=m2b.id, name="离线缓存", status="in_progress", priority="medium", progress=30, start_date=d(4), due_date=d(28)),
            Task(project_id=p2.id, name="推送通知", status="todo", priority="medium", progress=0, start_date=d(14), due_date=d(40)),
            Task(project_id=p2.id, name="灰度方案", status="todo", priority="low", progress=0, start_date=d(30), due_date=d(55)),
        ]
        s.add_all(t2)
        await s.flush()
        s.add(TaskDependency(task_id=t2[3].id, depends_on_task_id=t2[2].id))

        # ---- 项目 2 的开发记录：演示会话 + DevLog ----
        sess = DevSession(
            project_id=p2.id,
            title="实现登录与鉴权",
            started_at=dt(-3),
            ended_at=dt(-2),
            summary="完成 OAuth2 + JWT，覆盖刷新与吊销，12 个单测全绿。",
            author="claude",
        )
        s.add(sess)
        await s.flush()
        s.add_all([
            DevLog(project_id=p2.id, session_id=sess.id, entry_type="progress", title="完成登录与鉴权", content="OAuth2 授权码 + JWT 签发，含刷新令牌与主动吊销。", related_task_ids=[t2[1].id], git_ref="d3f9a1", author="claude", created_at=dt(-3), updated_at=dt(-3)),
            DevLog(project_id=p2.id, session_id=sess.id, entry_type="decision", title="鉴权方案选 OAuth2 而非自研 Token", content="第三方服务可直接集成，避免自维护会话表与过期逻辑。", related_task_ids=[t2[1].id], author="claude", created_at=dt(-3), updated_at=dt(-3)),
            DevLog(project_id=p2.id, session_id=sess.id, entry_type="difficulty", title="刷新令牌并发请求导致 token 覆盖", severity="medium", content="同时发起的两个刷新请求互相覆盖；改用单飞（single-flight）加锁。", author="claude", created_at=dt(-2), updated_at=dt(-2)),
            DevLog(project_id=p2.id, session_id=sess.id, entry_type="todo", title="补充刷新令牌的竞态回归测试", status="open", author="claude", created_at=dt(-2), updated_at=dt(-2)),
            DevLog(project_id=p2.id, session_id=sess.id, entry_type="blocker", title="等待第三方授权回调域名备案", severity="high", status="open", author="claude", created_at=dt(-1), updated_at=dt(-1)),
        ])
        projects.append(p2)

        # ---- 项目 3：数据中台建设 ----
        p3 = Project(
            owner_id=uid,
            name="数据中台建设",
            description="统一指标口径，建设采集、治理与可视化能力。",
            status="active",
            start_date=d(-45),
            end_date=d(75),
        )
        s.add(p3)
        await s.flush()
        m3a = Milestone(project_id=p3.id, name="数仓建模", due_date=d(5), status="active")
        m3b = Milestone(project_id=p3.id, name="治理平台", due_date=d(50), status="active")
        s.add_all([m3a, m3b])
        await s.flush()
        t3 = [
            Task(project_id=p3.id, milestone_id=m3a.id, name="数据源梳理", status="done", priority="high", progress=100, start_date=d(-45), due_date=d(-30), completed_at=dt(-30)),
            Task(project_id=p3.id, milestone_id=m3a.id, name="ODS 接入", status="in_progress", priority="high", progress=80, start_date=d(-28), due_date=d(2)),
            Task(project_id=p3.id, milestone_id=m3a.id, name="指标口径定义", status="in_progress", priority="medium", progress=50, start_date=d(-20), due_date=d(8)),
            Task(project_id=p3.id, milestone_id=m3a.id, name="历史数据回填", status="todo", priority="low", progress=0, start_date=d(-10), due_date=d(4)),  # 临近逾期
            Task(project_id=p3.id, milestone_id=m3b.id, name="质量监控", status="todo", priority="medium", progress=0, start_date=d(8), due_date=d(40)),
            Task(project_id=p3.id, name="看板模板", status="todo", priority="low", progress=0, start_date=d(20), due_date=d(60)),
        ]
        s.add_all(t3)
        await s.flush()
        projects.append(p3)

        # ---- 项目 4：内部工具迁移（已归档）----
        p4 = Project(
            owner_id=uid,
            name="内部工具迁移",
            description="将遗留脚本迁移到统一平台，已归档示例。",
            status="archived",
            start_date=d(-90),
            end_date=d(-10),
        )
        s.add(p4)
        await s.flush()
        t4 = [
            Task(project_id=p4.id, name="盘点遗留脚本", status="done", priority="medium", progress=100, start_date=d(-90), due_date=d(-70), completed_at=dt(-70)),
            Task(project_id=p4.id, name="平台接入", status="done", priority="high", progress=100, start_date=d(-68), due_date=d(-40), completed_at=dt(-40)),
            Task(project_id=p4.id, name="下线旧服务", status="done", priority="low", progress=100, start_date=d(-38), due_date=d(-12), completed_at=dt(-12)),
        ]
        s.add_all(t4)
        await s.flush()
        projects.append(p4)

        await s.commit()
        print(
            f"已生成 {len(projects)} 个项目、共 "
            f"{len(t)+len(t2)+len(t3)+len(t4)} 个任务（含逾期示例），"
            f"并在项目 2 中写入 1 个开发会话 + 5 条开发记录，账号 {ADMIN}/{PW}"
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
