"""FastAPI 애플리케이션 진입점.

모든 라우트는 /api 아래에 둔다. 그래서 프론트엔드는 같은 출처의 단일 베이스
(VITE_API_BASE_URL=/api)를 사용하며, 개발에서는 Vite, 운영에서는 Caddy가 프록시한다.
"""
import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, calendar, dashboard, health, me, planner, plaza, records, sessions
from app.core.config import get_settings
from app.workers import completer

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    problems = settings.production_problems()
    if problems:
        # 안전하지 않은 운영 설정이면 서버를 띄우지 않는다(비밀 값은 출력하지 않음).
        raise RuntimeError("운영 설정 오류: " + " / ".join(problems))
    task = asyncio.create_task(completer.run_forever()) if settings.run_workers else None
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


app = FastAPI(
    title="Tree for Study API",
    version="1.0.0",
    lifespan=lifespan,
    # 운영에서는 API 문서 화면을 열지 않는다.
    docs_url=None if settings.environment == "production" else "/api/docs",
    redoc_url=None,
    openapi_url=None if settings.environment == "production" else "/api/openapi.json",
)

# 운영(Caddy) / 개발(Vite 프록시)에서는 같은 출처이다. CORS는 로컬 편의를 위해
# 직접 교차 출처로 접근하는 프론트엔드만 허용한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (health, auth, me, admin, sessions, dashboard, records, plaza, calendar, planner):
    app.include_router(module.router, prefix="/api")


@app.middleware("http")
async def no_store_api(request, call_next):
    """API 응답은 개인 데이터이므로 브라우저/중간 캐시에 저장하지 않는다."""
    response = await call_next(request)
    if request.url.path.startswith("/api"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.get("/api")
async def root() -> dict:
    return {"service": "tree-for-study", "status": "ok"}
