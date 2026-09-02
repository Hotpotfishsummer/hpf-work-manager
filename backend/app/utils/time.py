from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import settings


def utcnow() -> datetime:
    """统一 UTC 时间戳（带时区），数据库存 UTC，前端按本地时区展示。"""
    return datetime.now(UTC)


def display_tz() -> ZoneInfo:
    """展示时区（用户日历语义），默认 Asia/Shanghai，DISPLAY_TIMEZONE 可覆盖。"""
    return ZoneInfo(settings.display_timezone)


def today_utc() -> date:
    """UTC 日历的今天（仅用于确需 UTC 语义的场景）。"""
    return utcnow().date()


def display_today() -> date:
    """用户日历意义的"今天"（按 display_timezone 判定，而非服务器本地时区）。

    逾期判定、每日快照、燃尽分桶、今日完成数等统计口径统一使用本函数，
    避免 UTC+8 用户在本地 0:00-8:00 期间统计错位一天。
    """
    return utcnow().astimezone(display_tz()).date()


def display_date(dt: datetime) -> date:
    """时间戳按展示时区折算的日期（完成时间分桶用）。

    历史 naive 数据按 UTC 解释（库内时间戳均为 UTC）。
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(display_tz()).date()


def display_day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    """展示时区某日 [00:00, 24:00) 对应的 UTC 时间窗（SQL 时间戳过滤用）。"""
    tz = display_tz()
    start = datetime(day.year, day.month, day.day, tzinfo=tz).astimezone(UTC)
    end = (start + timedelta(days=1)).astimezone(UTC)
    return start, end
