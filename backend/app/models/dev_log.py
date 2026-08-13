from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DevLog(Base):
    """结构化开发记录条目：比 git 粒度更细的语义记录。

    entry_type: progress / difficulty / todo / decision / blocker / milestone / note
    status:     open / done（仅 todo / blocker 使用）
    severity:   low / medium / high（仅 difficulty / blocker 使用）
    related_task_ids 存 JSON 数组（兼容 PG 与 SQLite），不强制绑 Task。
    git_ref   仅作溯源引用（commit/分支名），不解析 git。
    """

    __tablename__ = "dev_logs"
    __table_args__ = (
        Index("ix_dev_logs_project_type", "project_id", "entry_type"),
        Index("ix_dev_logs_project_created", "project_id", "created_at"),
        Index("ix_dev_logs_project_status", "project_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("dev_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    entry_type: Mapped[str] = mapped_column(String(20), default="note")
    status: Mapped[str] = mapped_column(String(10), default="open")  # open/done
    severity: Mapped[str | None] = mapped_column(String(10), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_task_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    git_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    author: Mapped[str] = mapped_column(String(50), default="web")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    project: Mapped["Project"] = relationship(back_populates="dev_logs")
    session: Mapped["DevSession | None"] = relationship(back_populates="logs")
