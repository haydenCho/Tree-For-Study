"""비동기 SQLAlchemy 엔진과 세션 팩토리.

모델은 `Base`를 상속해 선언한다. 스키마는 Alembic 마이그레이션이 관리하며,
앱이 테이블을 자동 생성하지 않는다(테스트만 metadata.create_all 사용).
"""
from collections.abc import AsyncGenerator

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


# 제약 조건 이름 규칙(Alembic 마이그레이션에서 이름이 안정적으로 유지되도록)
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


settings = get_settings()

_engine_kwargs: dict = {"pool_pre_ping": True}
if settings.db_nullpool:
    _engine_kwargs = {"poolclass": NullPool}

engine = create_async_engine(settings.database_url, **_engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """요청 단위 비동기 세션을 제공하는 FastAPI 의존성."""
    async with SessionLocal() as session:
        yield session


# 여러 행에 걸친 경합(정원 확인, 공동 숲 무작위 배치)을 트랜잭션 단위로 직렬화하는
# advisory lock 키. 10명 규모라 전역 직렬화로 충분하다.
LOCK_MEMBERSHIP = 7_001
LOCK_COMMUNITY = 7_002


async def advisory_xact_lock(session: AsyncSession, key: int) -> None:
    await session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": key})
