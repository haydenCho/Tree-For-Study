"""캘린더 조회.

GET /api/calendar?month=YYYY-MM            — 본인: 날짜 종류(대면/자율/휴무) + 날짜별 목표 수·기록 여부
GET /api/calendar?month=YYYY-MM&member=ID  — 팀원: 날짜 종류 + 공개 기록이 있는 날짜만 표시
비공개 날짜는 팀원 화면에서 어떤 집계도 드러내지 않는다.
"""
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import active_member
from app.api.plaza import parse_month
from app.core.db import get_session
from app.models import DailyEntry, Goal, User
from app.services import attendance

router = APIRouter(tags=["calendar"])


@router.get("/calendar")
async def calendar_month(
    month: str | None = None,
    member: uuid.UUID | None = None,
    user: User = Depends(active_member),
    db: AsyncSession = Depends(get_session),
) -> dict:
    start, end = parse_month(month)
    kinds = await attendance.kinds_between(db, start, end)
    days = []
    if member is not None and member != user.id:
        target = await db.get(User, member)
        public_dates = set()
        if target is not None and target.status == "active":
            public_dates = set(
                (
                    await db.execute(
                        select(DailyEntry.entry_date).where(
                            DailyEntry.user_id == target.id,
                            DailyEntry.is_public.is_(True),
                            DailyEntry.entry_date >= start,
                            DailyEntry.entry_date <= end,
                        )
                    )
                ).scalars().all()
            )
        d = start
        while d <= end:
            days.append({"date": d.isoformat(), "kind": kinds.get(d), "hasPublicEntry": d in public_dates})
            d += timedelta(days=1)
        member_info = None
        if target is not None and target.status == "active":
            member_info = {"id": str(target.id), "displayName": target.display_name, "avatarEmoji": target.avatar_emoji}
        return {"month": start.isoformat()[:7], "member": member_info, "days": days}

    goal_counts = dict(
        (
            await db.execute(
                select(Goal.goal_date, func.count())
                .where(Goal.user_id == user.id, Goal.goal_date >= start, Goal.goal_date <= end)
                .group_by(Goal.goal_date)
            )
        ).all()
    )
    entries = {
        e.entry_date: e
        for e in (
            await db.execute(
                select(DailyEntry).where(DailyEntry.user_id == user.id, DailyEntry.entry_date >= start, DailyEntry.entry_date <= end)
            )
        ).scalars().all()
    }
    d = start
    while d <= end:
        e = entries.get(d)
        days.append(
            {
                "date": d.isoformat(),
                "kind": kinds.get(d),
                "goalCount": goal_counts.get(d, 0),
                "hasEntry": bool(e and (e.plan_text or e.record_text)),
                "isPublic": bool(e and e.is_public),
            }
        )
        d += timedelta(days=1)
    return {"month": start.isoformat()[:7], "member": None, "days": days}
