"""날짜별 계획·기록·목표 서비스와 공개 필터.

공개 필터 원칙: 타인 조회는 (1) 조회자와 대상 모두 active 멤버이고 (2) 해당 날짜
기록이 공개일 때만 내용을 돌려준다. 그 외에는 존재 여부조차 구분되지 않도록
{"public": false}만 돌려준다.
"""
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.core.errors import bad_request, not_found
from app.models import DailyEntry, Goal, User
from app.services import planner

MAX_TEXT = 5000


def parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise bad_request("invalid_date", "날짜 형식은 YYYY-MM-DD 입니다.")


def goal_out(g: Goal) -> dict:
    return {
        "id": str(g.id),
        "date": g.goal_date.isoformat(),
        "title": g.title,
        "done": g.done,
        "carriedFromId": str(g.carried_from_id) if g.carried_from_id else None,
    }


async def goals_for(db: AsyncSession, user_id: uuid.UUID, day: date) -> list[Goal]:
    return list(
        (
            await db.execute(
                select(Goal).where(Goal.user_id == user_id, Goal.goal_date == day).order_by(Goal.sort_order, Goal.created_at)
            )
        )
        .scalars()
        .all()
    )


async def get_entry(db: AsyncSession, user_id: uuid.UUID, day: date) -> DailyEntry | None:
    return (
        await db.execute(select(DailyEntry).where(DailyEntry.user_id == user_id, DailyEntry.entry_date == day))
    ).scalar_one_or_none()


async def entry_payload(db: AsyncSession, user_id: uuid.UUID, day: date) -> dict:
    entry = await get_entry(db, user_id, day)
    goals = await goals_for(db, user_id, day)
    return {
        "date": day.isoformat(),
        "planText": entry.plan_text if entry else "",
        "recordText": entry.record_text if entry else "",
        "isPublic": entry.is_public if entry else False,
        "updatedAt": entry.updated_at.isoformat() if entry else None,
        "goals": [goal_out(g) for g in goals],
        "blocks": [planner.block_out(b) for b in await planner.blocks_for(db, user_id, day)],
    }


async def upsert_entry(
    db: AsyncSession, user: User, day: date, *, plan_text: str | None, record_text: str | None, is_public: bool | None
) -> DailyEntry:
    for value in (plan_text, record_text):
        if value is not None and len(value) > MAX_TEXT:
            raise bad_request("text_too_long", f"내용은 {MAX_TEXT}자 이하로 입력해 주세요.")
    now = utcnow()
    entry = await get_entry(db, user.id, day)
    if entry is None:
        entry = DailyEntry(user_id=user.id, entry_date=day, created_at=now, updated_at=now)
        db.add(entry)
    if plan_text is not None:
        entry.plan_text = plan_text
    if record_text is not None:
        entry.record_text = record_text
    if is_public is not None:
        entry.is_public = is_public
    entry.updated_at = now
    await db.commit()
    return entry


async def public_entry_for(db: AsyncSession, viewer: User, member_id: uuid.UUID, day: date) -> dict:
    """타인의 공개 일일 기록. 비공개/없음/비활성 회원은 모두 같은 응답."""
    hidden = {"date": day.isoformat(), "public": False}
    member = await db.get(User, member_id)
    if member is None or member.status != "active" or viewer.status != "active":
        return hidden
    entry = await get_entry(db, member.id, day)
    if entry is None or not entry.is_public:
        return hidden
    payload = await entry_payload(db, member.id, day)
    payload.pop("updatedAt", None)
    return {
        **payload,
        "public": True,
        "member": {"id": str(member.id), "displayName": member.display_name, "avatarEmoji": member.avatar_emoji},
    }


async def add_goal(db: AsyncSession, user: User, day: date, title: str) -> Goal:
    title = (title or "").strip()
    if not 1 <= len(title) <= 120:
        raise bad_request("invalid_goal", "목표는 1~120자로 입력해 주세요.")
    count = (
        await db.execute(select(func.count()).select_from(Goal).where(Goal.user_id == user.id, Goal.goal_date == day))
    ).scalar_one()
    if count >= 30:
        raise bad_request("too_many_goals", "하루 목표는 30개까지 추가할 수 있습니다.")
    goal = Goal(user_id=user.id, goal_date=day, title=title, sort_order=count, created_at=utcnow())
    db.add(goal)
    await db.commit()
    return goal


async def own_goal(db: AsyncSession, user: User, goal_id: uuid.UUID) -> Goal:
    goal = await db.get(Goal, goal_id)
    if goal is None or goal.user_id != user.id:
        raise not_found("goal_not_found", "목표를 찾을 수 없습니다.")
    return goal
