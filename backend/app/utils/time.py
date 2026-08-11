from datetime import datetime, timezone


def utcnow() -> datetime:
    """统一 UTC 时间戳（带时区），数据库存 UTC，前端按本地时区展示。"""
    return datetime.now(timezone.utc)


def today_utc() -> datetime.date:
    return utcnow().date()
