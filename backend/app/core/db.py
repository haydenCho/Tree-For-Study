"""비동기 SQLAlchemy 엔진과 세션 팩토리.

모델은 `Base`를 상속해 선언한다. 스키마는 Alembic 마이그레이션(1단계 이후)이
관리하며, 앱이 테이블을 자동 생성하지 않는다.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """요청 단위 비동기 세션을 제공하는 FastAPI 의존성."""
    async with SessionLocal() as session:
        yield session
