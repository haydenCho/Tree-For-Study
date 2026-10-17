"""테스트 공통 설정.

- 실제 PostgreSQL(개발 compose의 db)에 `<DB이름>_test` 데이터베이스를 따로 만들어 쓴다.
  운영/개발 데이터에는 손대지 않는다. 테스트 계정은 이 테스트 DB에만 존재한다.
- 시간은 주입 시계(app.core.clock)로 고정·이동한다. 실제 분 단위 대기를 하지 않는다.
- 백그라운드 워커는 끄고, 필요한 테스트에서 settle_due를 직접 호출한다.
"""
import asyncio
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

# ── 앱 import 전에 환경을 테스트용으로 바꾼다 ─────────────────────
_base_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://tfs:tfs@localhost:5432/tree_for_study")
_prefix, _, _dbname = _base_url.rpartition("/")
TEST_DB = _dbname.split("?")[0] + "_test"
os.environ["DATABASE_URL"] = f"{_prefix}/{TEST_DB}"
os.environ["DB_NULLPOOL"] = "true"
os.environ["RUN_WORKERS"] = "false"
os.environ["APP_ORIGIN"] = "http://test.local"
os.environ["COOKIE_SECURE"] = "false"
os.environ["JWT_SECRET"] = "test-secret-" + "x" * 40
os.environ["TRUSTED_PROXY_IPS"] = "10.0.0.2"


def _ensure_database() -> None:
    import asyncpg

    async def run():
        admin_dsn = _prefix.replace("postgresql+asyncpg", "postgresql") + "/postgres"
        conn = await asyncpg.connect(admin_dsn)
        try:
            exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", TEST_DB)
            if not exists:
                await conn.execute(f'CREATE DATABASE "{TEST_DB}"')
        finally:
            await conn.close()

    asyncio.run(run())


_ensure_database()

import httpx  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.clock import clock  # noqa: E402
from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.core.ratelimit import login_ip_limiter, login_limiter, register_limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
import app.models as _models  # noqa: E402,F401

KST = ZoneInfo("Asia/Seoul")
ORIGIN = "http://test.local"
PASSWORD = "correct-horse-battery"
# 해시 비용을 줄이기 위해 한 번만 계산해 재사용한다.
_PASSWORD_HASH = hash_password(PASSWORD)


def _create_schema() -> None:
    async def run():
        async with engine.begin() as conn:
            # 이전 실행의 잔여 스키마까지 깨끗이 지운다(테스트 DB 전용).
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(run())


_create_schema()


@pytest.fixture(autouse=True)
async def _clean_state():
    tables = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    clock.set(datetime(2026, 10, 21, 10, 0, tzinfo=KST))
    login_limiter.reset()
    login_ip_limiter.reset()
    register_limiter.reset()
    yield
    clock.reset()


@pytest.fixture
async def db():
    async with SessionLocal() as session:
        yield session


def make_client(ip: str = "203.0.113.9", headers: dict | None = None) -> httpx.AsyncClient:
    """ip는 ASGI 연결 상대 주소(=Caddy 없이 직접 접속했을 때의 클라이언트 주소)."""
    transport = httpx.ASGITransport(app=fastapi_app, client=(ip, 50000))
    return httpx.AsyncClient(transport=transport, base_url=ORIGIN, headers={"origin": ORIGIN, **(headers or {})})


@pytest.fixture
async def client():
    async with make_client() as c:
        yield c


async def create_user(email: str, *, status: str = "active", role: str = "member", display_name: str = "멤버") -> "app.models.User":
    from app.models import User

    async with SessionLocal() as s:
        user = User(
            email_normalized=email.lower(),
            real_name="실명" + email.split("@")[0],
            display_name=display_name,
            password_hash=_PASSWORD_HASH,
            status=status,
            role=role,
            created_at=clock.now(),
            approved_at=clock.now() if status == "active" else None,
        )
        s.add(user)
        await s.commit()
        return user


async def login(client: httpx.AsyncClient, email: str, password: str = PASSWORD) -> str:
    res = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    token = res.json()["accessToken"]
    client.headers["authorization"] = f"Bearer {token}"
    return token


def csrf_headers(client: httpx.AsyncClient) -> dict:
    return {"x-csrf-token": client.cookies.get("tfs_csrf", ""), "origin": ORIGIN}


async def member_client(email: str, ip: str = "203.0.113.9", **kwargs) -> tuple[httpx.AsyncClient, "app.models.User"]:
    user = await create_user(email, **kwargs)
    c = make_client(ip)
    await login(c, email)
    return c, user


async def tick(client: httpx.AsyncClient, seconds: float) -> None:
    """시계를 옮기고, 프론트엔드처럼 refresh로 새 access 토큰을 받는다."""
    clock.advance(seconds)
    res = await client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert res.status_code == 200, res.text
    client.headers["authorization"] = f"Bearer {res.json()['accessToken']}"
