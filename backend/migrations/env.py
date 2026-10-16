"""Alembic 환경 — 비동기 엔진, URL과 메타데이터를 앱에서 가져온다.

아직 테이블이 없으며 1단계에서 첫 리비전을 추가한다. backend/에서 실행:
    alembic revision --autogenerate -m "..."
    alembic upgrade head
"""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.db import Base

# 모델 테이블이 Base.metadata에 등록되도록 모델 모듈을 import 한다.
import app.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
DATABASE_URL = get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
