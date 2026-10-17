"""대시보드 조회: 개인 숲, 활성 세션, 오늘 성공 집계, 오늘 목표, 스터디 일정.

성공 집계는 '정상 완료된 세션'의 집중 구간만 한국 날짜 기준으로 나눠 더한다
(자정을 넘는 구간은 날짜별로 분할). 포기 세션의 원시 경과는 포함하지 않는다.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import active_member
from app.core.clock import kst_day_bounds, kst_today, utcnow
from app.core.config import get_settings
from app.core.db import get_session
from app.models import User
from app.services import focus, forest, records

router = APIRouter(tags=["dashboard"])
settings = get_settings()


def study_info() -> dict:
    today = kst_today()
    return {
        "today": today.isoformat(),
        "studyStart": settings.study_start.isoformat(),
        "studyEnd": settings.study_end.isoformat(),
        "examDate": settings.exam_date.isoformat(),
        "daysToExam": (settings.exam_date - today).days,
        "studyEnded": today > settings.study_end,
    }


@router.get("/study")
async def study() -> dict:
    """D-day 표시용 공개 일정 정보(로그인 화면에서도 사용)."""
    return study_info()


@router.get("/dashboard")
async def dashboard(user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    today = kst_today()
    start, end = kst_day_bounds(today)
    active = await focus.get_active(db, user.id)
    active_payload = None
    if active is not None:
        active = await focus.get_for_user(db, user, active.id)
        if active.status in ("focusing", "paused"):
            active_payload = await focus.serialize(db, active)
    goals = await records.goals_for(db, user.id, today)
    return {
        "study": study_info(),
        "serverNow": utcnow().isoformat(),
        "defaults": {"focusMinutes": user.default_focus_minutes, "restMinutes": user.default_rest_minutes},
        "zones": await forest.personal_forest(db, user.id),
        "activeSession": active_payload,
        "today": {
            "successSeconds": await focus.success_seconds_between(db, user.id, start, end),
            "successTrees": await focus.count_trees(db, user.id, start, end),
            "wiltedTrees": await focus.count_trees(db, user.id, start, end, states=("wilted",)),
        },
        "goals": [records.goal_out(g) for g in goals],
    }
