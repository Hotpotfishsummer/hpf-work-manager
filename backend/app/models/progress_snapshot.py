from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProgressSnapshot(Base):
    """项目每日进度快照：读取统计时按天 upsert（自愈式，无需定时任务）。

    用于进度趋势回溯；数值口径与 get_project_stats 完全一致。
    """

    __tablename__ = "progress_snapshots"
    __table_args__ = (
        UniqueConstraint("project_id", "date", name="uq_progress_snapshot_project_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date)
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    done_tasks: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 数量进度 0-100
    weighted_progress: Mapped[float] = mapped_column(Float, default=0.0)  # 工时加权 0-100
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
