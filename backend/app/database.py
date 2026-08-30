from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


def _build_engine(url: str):
    # SQLite（测试/内存库）不接受连接池参数
    if url.startswith("sqlite"):
        return create_async_engine(url, pool_pre_ping=True, echo=False)
    return create_async_engine(
        url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        echo=False,
    )


engine = _build_engine(settings.database_url)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI 依赖：按请求生命周期提供数据库会话。"""
    async with AsyncSessionLocal() as session:
        yield session
