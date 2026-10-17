"""출석 서비스(docs/01-product-plan.md §7).

상태: not_checked(미체크인) / present(출석) / absent(결석) / holiday(휴무) / self(자율일).
- 예정일 당일 23:59:59 KST까지 언제 체크인해도 출석. 지각·유예·지각 통계 없음.
- 다음 날 00:00 KST부터 미체크인 대면일은 결석으로 계산한다(행을 만들지 않는 조회 시 판정).
- 휴무는 출석률 분모에서 제외한다. 결석으로 나무를 차감하지 않는다.
- 운영자 정정은 사유와 함께 행으로 남기고 감사 기록을 쓴다.
"""
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import kst_today, utcnow
from app.core.config import get_settings
from app.core.errors import bad_request, conflict, not_found
from app.models import Attendance, StudyDate, User
from app.services.membership import audit

settings = get_settings()

KIND_LABEL = {"in_person": "대면", "self": "자율", "holiday": "휴무"}


def default_kind(day: date) -> str | None:
    """기간 안의 기본 종류: 화~금 대면, 그 외 자율. 기간 밖은 None."""
    if not settings.study_start <= day <= settings.study_end:
        return None
    return "in_person" if day.weekday() in (1, 2, 3, 4) else "self"


async def kinds_between(db: AsyncSession, start: date, end: date) -> dict[date, str]:
    """[start, end] 날짜별 종류. DB(운영자 지정)가 기본값보다 우선한다."""
    result: dict[date, str] = {}
    d = start
    while d <= end:
        k = default_kind(d)
        if k:
            result[d] = k
        d += timedelta(days=1)
    rows = (await db.execute(select(StudyDate).where(StudyDate.day >= start, StudyDate.day <= end))).scalars().all()
    for r in rows:
        result[r.day] = r.kind
    return result


async def kind_of(db: AsyncSession, day: date) -> str | None:
    return (await kinds_between(db, day, day)).get(day)


def derive_status(kind: str | None, row: Attendance | None, day: date, today: date) -> str:
    if row is not None:
        return row.status
    if kind == "holiday":
        return "holiday"
    if kind == "in_person":
        return "absent" if day < today else "not_checked"
    if kind == "self":
        return "self"
    return "none"


async def check_in(db: AsyncSession, user: User) -> Attendance:
    today = kst_today()
    kind = await kind_of(db, today)
    if kind is None:
        raise bad_request("not_study_day", "스터디 기간의 날짜에만 체크인할 수 있어요.")
    if kind == "holiday":
        raise bad_request("holiday", "오늘은 휴무일이에요.")
    existing = (
        await db.execute(select(Attendance).where(Attendance.user_id == user.id, Attendance.day == today))
    ).scalar_one_or_none()
    if existing is not None:
        if existing.status == "present":
            return existing
        raise conflict("attendance_locked", "운영자가 정정한 출석이에요.")
    now = utcnow()
    row = Attendance(user_id=user.id, day=today, status="present", checked_in_at=now, updated_at=now)
    db.add(row)
    await db.commit()
    return row


async def rows_for(db: AsyncSession, user_ids: list[uuid.UUID], start: date, end: date) -> dict[tuple, Attendance]:
    if not user_ids:
        return {}
    rows = (
        await db.execute(
            select(Attendance).where(Attendance.user_id.in_(user_ids), Attendance.day >= start, Attendance.day <= end)
        )
    ).scalars().all()
    return {(r.user_id, r.day): r for r in rows}


async def summary_for(db: AsyncSession, user: User) -> dict:
    """본인 출석 요약: 오늘 상태 + 기간 출석률(오늘까지의 대면일 기준, 휴무 제외)."""
    today = kst_today()
    start, end = settings.study_start, min(settings.study_end, today)
    kinds = await kinds_between(db, settings.study_start, settings.study_end)
    rows = await rows_for(db, [user.id], settings.study_start, settings.study_end)
    present = 0
    total = 0
    d = start
    while d <= end:
        kind = kinds.get(d)
        status = derive_status(kind, rows.get((user.id, d)), d, today)
        if kind == "in_person" and status != "holiday":
            # 오늘은 체크인했을 때만 분모에 넣는다(아직 하루가 끝나지 않음).
            if d < today or status == "present":
                total += 1
        if status == "present":
            present += 1
        d += timedelta(days=1)
    # 오늘이 기간 밖이어도 운영자가 지정한 날짜면 그 종류를 따른다.
    today_kind = kinds.get(today) or await kind_of(db, today)
    if today not in kinds:
        rows.update(await rows_for(db, [user.id], today, today))
    return {
        "today": today.isoformat(),
        "todayKind": today_kind,
        "todayStatus": derive_status(today_kind, rows.get((user.id, today)), today, today),
        "presentDays": present,
        "countedDays": total,
    }


async def month_for(db: AsyncSession, user: User, start: date, end: date) -> list[dict]:
    today = kst_today()
    kinds = await kinds_between(db, start, end)
    rows = await rows_for(db, [user.id], start, end)
    out = []
    d = start
    while d <= end:
        kind = kinds.get(d)
        out.append({"date": d.isoformat(), "kind": kind, "status": derive_status(kind, rows.get((user.id, d)), d, today)})
        d += timedelta(days=1)
    return out


async def set_date_kind(db: AsyncSession, operator: User, day: date, kind: str, note: str) -> StudyDate:
    if kind not in ("in_person", "self", "holiday"):
        raise bad_request("invalid_kind", "날짜 종류를 확인해 주세요.")
    row = await db.get(StudyDate, day)
    if row is None:
        row = StudyDate(day=day, kind=kind, note=note[:100])
        db.add(row)
    else:
        row.kind = kind
        row.note = note[:100]
    await audit(db, operator, "study_date.set", day.isoformat(), f"{kind} {note}"[:300])
    await db.commit()
    return row


async def correct(db: AsyncSession, operator: User, user_id: uuid.UUID, day: date, status: str, reason: str) -> Attendance:
    if status not in ("present", "absent", "holiday"):
        raise bad_request("invalid_status", "출석 상태를 확인해 주세요.")
    reason = (reason or "").strip()
    if not reason:
        raise bad_request("reason_required", "정정 사유를 입력해 주세요.")
    target = await db.get(User, user_id)
    if target is None:
        raise not_found()
    row = (await db.execute(select(Attendance).where(Attendance.user_id == user_id, Attendance.day == day))).scalar_one_or_none()
    now = utcnow()
    if row is None:
        row = Attendance(user_id=user_id, day=day, status=status, updated_at=now)
        db.add(row)
    row.status = status
    row.corrected_by = operator.id
    row.reason = reason[:300]
    row.updated_at = now
    await audit(db, operator, "attendance.correct", f"{user_id}:{day.isoformat()}", f"{status}: {reason}"[:300])
    await db.commit()
    return row
