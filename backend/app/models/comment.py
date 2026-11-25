from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Comment(Base):
    """评论：挂在任务上（task_id）或项目上（project_id），二者恰好一个非空。

    - 任务评论（P5）：对单个任务的讨论，author_username 为创建时快照。
    - 项目评论（工作方向指示）：负责人写给「下一次接手该项目的 Agent」的上下文——
      工作方向、优先级调整、禁忌、结论。Agent 通过 get_project_state / MCP
      list_comments(project_id=...) 读取；落实后用 resolved_at 标记已处理，
      避免旧指示一直被重复执行。

    author_id 允许置空（用户删除后评论保留，显示为历史作者）。
    """

    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_task_created", "task_id", "created_at"),
        Index("ix_comments_project_created", "project_id", "created_at"),
        CheckConstraint(
            "(task_id IS NOT NULL) <> (project_id IS NOT NULL)",
            name="ck_comments_exactly_one_anchor",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=True
    )
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True
    )
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    author_username: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # 仅项目评论使用：指示被落实的时间；NULL = 仍待处理
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
