from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationWatermark(Base):
    """用户的通知已读水位（P4-4 通知中心服务端化）。

    记录该用户已读到的最新事件时间戳：跨设备/清缓存后不再丢失已读状态。
    一行一用户；时间戳为 UTC。
    """

    __tablename__ = "notification_watermarks"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    last_read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
