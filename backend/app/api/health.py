"""생존(liveness) / 준비(readiness) 엔드포인트.

- /api/health — 프로세스가 떠 있음 (의존성 미접근).
- /api/ready  — 의존성 접근 가능 (DB 왕복). compose/EC2 점검에 사용.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> dict:
    await session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
