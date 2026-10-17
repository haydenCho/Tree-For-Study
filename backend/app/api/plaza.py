"""광장·출석·공개 WBS·도서관 상태 라우트(2단계).

GET  /api/plaza                       — 공동 숲 + 팀원 카드 + 공개 피드
POST /api/attendance/check-in         — 오늘 체크인
GET  /api/attendance/me?month=YYYY-MM — 본인 월간 출석
GET  /api/members/{id}/wbs            — 팀원 공개 WBS(읽기 전용)
GET  /api/library-status              — 현재 접속이 도서관으로 인식되는지(참고용, IP 미노출)
"""
import calendar
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import active_member
from app.core.client_ip import client_ip
from app.core.clock import kst_today
from app.core.db import get_session
from app.core.errors import bad_request
from app.models import User
from app.services import attendance, library, plaza, wbs

router = APIRouter(tags=["plaza"])


def parse_month(raw: str | None) -> tuple[date, date]:
    if not raw:
        today = kst_today()
        y, m = today.year, today.month
    else:
        try:
            y, m = (int(x) for x in raw.split("-"))
            date(y, m, 1)
        except ValueError:
            raise bad_request("invalid_month", "월 형식은 YYYY-MM 입니다.")
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


@router.get("/plaza")
async def get_plaza(_: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return await plaza.build(db)


@router.post("/attendance/check-in")
async def check_in(user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    await attendance.check_in(db, user)
    return await attendance.summary_for(db, user)


@router.get("/attendance/me")
async def my_attendance(month: str | None = None, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    start, end = parse_month(month)
    return {"summary": await attendance.summary_for(db, user), "days": await attendance.month_for(db, user, start, end)}


@router.get("/members/{member_id}/wbs")
async def member_wbs(member_id: uuid.UUID, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return await wbs.public_tasks_for(db, user, member_id)


@router.get("/library-status")
async def library_status(request: Request, _: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    """일반 사용자에게는 인식 여부만 알려 준다. 실제 판정은 세션 시작 요청에서 다시 한다."""
    return {"recognized": await library.is_library_ip(db, client_ip(request))}
