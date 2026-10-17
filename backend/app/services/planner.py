"""시간표·주간 회고·주말 보충 서비스(docs/01-product-plan.md §8, §11).

시간표 규칙: 15분 스냅, 최소 15분, 종료 > 시작, 0~1440(24:00은 종료로만), 같은 날짜·같은 레이어 겹침 거부.
겹침 검사는 사용자별 advisory lock 안에서 수행해 동시 요청에도 겹치는 블록이 생기지 않는다.
날짜를 넘는 블록은 받지 않는다(사용자가 자정에서 나눠 각 날짜에 작성).
"""
import uuid
from datetime import date, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import KST, split_by_kst_date, utcnow
from app.core.errors import bad_request, conflict, not_found
from app.models import FocusInterval, FocusSession, Goal, TimetableBlock, Tree, User, WeeklyReview

SNAP = 15
MAX_TEXT = 3000


# ── 시간표 ─────────────────────────────────────────────────────────
def block_out(b: TimetableBlock) -> dict:
    return {
        "id": str(b.id),
        "date": b.day.isoformat(),
        "layer": b.layer,
        "startMin": b.start_min,
        "endMin": b.end_min,
        "title": b.title,
        "memo": b.memo,
    }


def validate_range(start: int, end: int) -> None:
    if start % SNAP or end % SNAP:
        raise bad_request("not_snapped", "시간은 15분 단위로 입력해 주세요.")
    if not (0 <= start < end <= 1440):
        raise bad_request("invalid_range", "종료 시각은 시작 시각보다 늦어야 하고 하루(00:00~24:00) 안이어야 해요.")


async def _lock_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"timetable:{user_id}"})


async def _check_overlap(db: AsyncSession, user_id, day, layer, start, end, exclude_id=None) -> None:
    q = select(TimetableBlock.id).where(
        TimetableBlock.user_id == user_id,
        TimetableBlock.day == day,
        TimetableBlock.layer == layer,
        TimetableBlock.start_min < end,
        TimetableBlock.end_min > start,
    )
    if exclude_id is not None:
        q = q.where(TimetableBlock.id != exclude_id)
    if (await db.execute(q)).first():
        raise conflict("block_overlap", "같은 종류의 다른 블록과 시간이 겹쳐요.")


async def blocks_for(db: AsyncSession, user_id: uuid.UUID, day: date) -> list[TimetableBlock]:
    return list(
        (
            await db.execute(
                select(TimetableBlock).where(TimetableBlock.user_id == user_id, TimetableBlock.day == day).order_by(TimetableBlock.start_min)
            )
        )
        .scalars()
        .all()
    )


def _clean(title: str, memo: str) -> tuple[str, str]:
    title = (title or "").strip()
    if not 1 <= len(title) <= 80:
        raise bad_request("invalid_title", "제목은 1~80자로 입력해 주세요.")
    memo = (memo or "").strip()
    if len(memo) > 500:
        raise bad_request("invalid_memo", "메모는 500자 이하로 입력해 주세요.")
    return title, memo


async def create_block(db: AsyncSession, user: User, *, day: date, layer: str, start: int, end: int, title: str, memo: str) -> TimetableBlock:
    if layer not in ("plan", "actual"):
        raise bad_request("invalid_layer", "계획 또는 실제 기록 중 하나를 골라 주세요.")
    validate_range(start, end)
    title, memo = _clean(title, memo)
    await _lock_user(db, user.id)
    await _check_overlap(db, user.id, day, layer, start, end)
    now = utcnow()
    b = TimetableBlock(user_id=user.id, day=day, layer=layer, start_min=start, end_min=end, title=title, memo=memo, created_at=now, updated_at=now)
    db.add(b)
    await db.commit()
    return b


async def own_block(db: AsyncSession, user: User, block_id: uuid.UUID) -> TimetableBlock:
    b = await db.get(TimetableBlock, block_id)
    if b is None or b.user_id != user.id:
        raise not_found("block_not_found", "시간표 블록을 찾을 수 없어요.")
    return b


async def update_block(db: AsyncSession, user: User, block_id: uuid.UUID, changes: dict) -> TimetableBlock:
    await _lock_user(db, user.id)
    b = await own_block(db, user, block_id)
    layer = changes.get("layer") or b.layer
    if layer not in ("plan", "actual"):
        raise bad_request("invalid_layer", "계획 또는 실제 기록 중 하나를 골라 주세요.")
    start = changes["start"] if changes.get("start") is not None else b.start_min
    end = changes["end"] if changes.get("end") is not None else b.end_min
    validate_range(start, end)
    title, memo = _clean(
        changes["title"] if changes.get("title") is not None else b.title,
        changes["memo"] if changes.get("memo") is not None else b.memo,
    )
    await _check_overlap(db, user.id, b.day, layer, start, end, exclude_id=b.id)
    b.layer, b.start_min, b.end_min, b.title, b.memo = layer, start, end, title, memo
    b.updated_at = utcnow()
    await db.commit()
    return b


# ── 주말 보충 ─────────────────────────────────────────────────────
async def carry_goal(db: AsyncSession, user: User, goal_id: uuid.UUID, target: date) -> Goal:
    """미완료 목표를 토/일로 이월한다. 원본 링크를 유지하고 같은 대상일 중복은 거부한다."""
    orig = await db.get(Goal, goal_id)
    if orig is None or orig.user_id != user.id:
        raise not_found("goal_not_found", "목표를 찾을 수 없어요.")
    if orig.done:
        raise bad_request("goal_done", "이미 완료한 목표예요.")
    if target.weekday() not in (5, 6):
        raise bad_request("not_weekend", "주말 보충은 토요일이나 일요일로만 옮길 수 있어요.")
    if target <= orig.goal_date:
        raise bad_request("target_in_past", "원래 날짜 이후의 주말을 골라 주세요.")
    dup = (await db.execute(select(Goal.id).where(Goal.carried_from_id == orig.id, Goal.goal_date == target))).first()
    if dup:
        raise conflict("already_carried", "이미 그 날짜로 보충한 목표예요.")
    count = (await db.execute(select(func.count()).select_from(Goal).where(Goal.user_id == user.id, Goal.goal_date == target))).scalar_one()
    g = Goal(user_id=user.id, goal_date=target, title=orig.title, carried_from_id=orig.id, sort_order=count, created_at=utcnow())
    db.add(g)
    await db.commit()
    return g


# ── 주간 회고·합계 ────────────────────────────────────────────────
def week_start_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


async def weekly_totals(db: AsyncSession, user_id: uuid.UUID, week_start: date) -> dict:
    """성공 세션의 집중 구간만 한국 날짜별로 나눠 합산한다(자정 분할)."""
    from datetime import datetime

    start = datetime(week_start.year, week_start.month, week_start.day, tzinfo=KST)
    end = start + timedelta(days=7)
    rows = (
        await db.execute(
            select(FocusInterval.started_at, FocusInterval.ended_at)
            .join(FocusSession, FocusSession.id == FocusInterval.session_id)
            .where(
                FocusSession.user_id == user_id,
                FocusSession.status == "completed",
                FocusInterval.ended_at.is_not(None),
                FocusInterval.started_at < end,
                FocusInterval.ended_at > start,
            )
        )
    ).all()
    per_day = {week_start + timedelta(days=i): 0 for i in range(7)}
    for a, b in rows:
        for day, secs in split_by_kst_date(max(a, start), min(b, end)).items():
            if day in per_day:
                per_day[day] += secs
    trees = (
        await db.execute(
            select(func.count())
            .select_from(Tree)
            .where(Tree.user_id == user_id, Tree.state.in_(("normal", "library")), Tree.created_at >= start, Tree.created_at < end)
        )
    ).scalar_one()
    return {
        "days": [{"date": d.isoformat(), "successSeconds": s} for d, s in per_day.items()],
        "totalSeconds": sum(per_day.values()),
        "successTrees": trees,
    }


def review_out(r: WeeklyReview | None, week_start: date) -> dict:
    return {
        "weekStart": week_start.isoformat(),
        "good": r.good if r else "",
        "hard": r.hard if r else "",
        "nextPlan": r.next_plan if r else "",
        "isPublic": r.is_public if r else False,
        "updatedAt": r.updated_at.isoformat() if r else None,
    }


async def get_review(db: AsyncSession, user_id: uuid.UUID, week_start: date) -> WeeklyReview | None:
    return (
        await db.execute(select(WeeklyReview).where(WeeklyReview.user_id == user_id, WeeklyReview.week_start == week_start))
    ).scalar_one_or_none()


async def upsert_review(db: AsyncSession, user: User, week_start: date, data: dict) -> WeeklyReview:
    for key in ("good", "hard", "next_plan"):
        if data.get(key) is not None and len(data[key]) > MAX_TEXT:
            raise bad_request("text_too_long", f"회고는 항목당 {MAX_TEXT}자 이하로 입력해 주세요.")
    now = utcnow()
    r = await get_review(db, user.id, week_start)
    if r is None:
        r = WeeklyReview(user_id=user.id, week_start=week_start, created_at=now, updated_at=now)
        db.add(r)
    for key in ("good", "hard", "next_plan", "is_public"):
        if data.get(key) is not None:
            setattr(r, key, data[key])
    r.updated_at = now
    await db.commit()
    return r
