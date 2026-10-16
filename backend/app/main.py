"""FastAPI 애플리케이션 진입점.

모든 라우트는 /api 아래에 둔다. 그래서 프론트엔드는 같은 출처의 단일 베이스
(VITE_API_BASE_URL=/api)를 사용하며, 개발에서는 Vite, 운영에서는 Caddy가 프록시한다.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="Tree for Study API", version="0.0.0")

# 운영(Caddy) / 개발(Vite 프록시)에서는 같은 출처이다. CORS는 로컬 편의를 위해
# 직접 교차 출처로 접근하는 프론트엔드만 허용한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


@app.get("/api")
async def root() -> dict:
    return {"service": "tree-for-study", "status": "ok"}
