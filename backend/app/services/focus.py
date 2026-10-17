"""집중 세션 서비스 — 서버 시각·구간·행 잠금이 권위다(docs/01-product-plan.md §3, §4).

핵심 규칙:
- 시작: 수종·목표·서로 다른 빈 칸 N개(N = floor(목표초/1200))를 검증하고 세션 생성과
  칸 예약을 한 트랜잭션으로 처리한다. 사용자 행을 FOR UPDATE로 잠가 두 탭 경합을
  직렬화하고, 활성 세션 부분 unique 인덱스와 칸 unique 제약이 마지막 방어선이다.
- pause는 현재 구간을 닫고, resume은 새 구간을 연다. 일시정지 시간은 집중에서 제외된다.
- 완료: 목표 도달 시각(target_end_at)이 지나면 워커나 다음 요청이 `settle`로 확정한다.
  완료 시각은 '요청이 도착한 시각'이 아니라 target_end_at이며 초과 적립하지 않는다.
- 포기: 목표 도달 전이면 인정 0초·모든 예약 칸을 시든 나무로 고정한다. 이미 목표에
  도달한 세션이면 완료가 우선이며 성공 나무를 회수하지 않는다.
- 나무 확정은 세션 상태 변경과 같은 트랜잭션에서 (세션, 순번) unique로 한 번만 만든다.
"""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import kst_today, utcnow
from app.core.config import get_settings
from app.core.errors import bad_request, conflict, forbidden, not_found
from app.core.policy import (
    SPECIES,
    ZONE_SIZE,
    tree_count,
    tree_size,
    validate_focus_minutes,
    validate_rest_minutes,
)
from app.models import FocusInterval, FocusSession, PersonalZone, SessionPlot, Tree, User
from app.services import hooks

settings = get_settings()


# ── 계산 helper ────────────────────────────────────────────────────
def focused_seconds(s: FocusSession, now: datetime) -> int:
    """지금까지 인정 대상이 되는 집중 초(목표 초과 없음)."""
    if s.status in ("completed",):
        return s.target_seconds
    total = s.accumulated_seconds
    if s.status == "focusing" and s.current_interval_started_at is not None:
        total += int((now - s.current_interval_started_at).total_seconds())
    return max(0, min(s.target_seconds, total))


def rest_state(s: FocusSession, now: datetime) -> str:
    if s.rest_started_at is None:
        return "none"
    if s.rest_ended_at is not None:
        return "rest_ended"
    if now >= s.rest_started_at + timedelta(seconds=s.rest_seconds):
        return "rest_completed"
    return "resting"


async def _zones_for(db: AsyncSession, user_id: uuid.UUID) -> list[PersonalZone]:
    return list(
        (await db.execute(select(PersonalZone).where(PersonalZone.user_id == user_id).order_by(PersonalZone.zone_index)))
        .scalars()
        .all()
    )


async def _ensure_first_zone(db: AsyncSession, user_id: uuid.UUID) -> list[PersonalZone]:
    zones = await _zones_for(db, user_id)
    if not zones:
        db.add(PersonalZone(user_id=user_id, zone_index=0, created_at=utcnow()))
        await db.flush()
        zones = await _zones_for(db, user_id)
    return zones


async def _used_cells(db: AsyncSession, zone_id: uuid.UUID) -> set[tuple[int, int]]:
    rows = (await db.execute(select(SessionPlot.row, SessionPlot.col).where(SessionPlot.zone_id == zone_id))).all()
    return {(r, c) for r, c in rows}


async def get_active(db: AsyncSession, user_id: uuid.UUID) -> FocusSession | None:
    return (
        await db.execute(
            select(FocusSession).where(FocusSession.user_id == user_id, FocusSession.status.in_(("focusing", "paused")))
        )
    ).scalar_one_or_none()


# ── 시작 ──────────────────────────────────────────────────────────
async def start_session(
    db: AsyncSession,
    user: User,
    *,
    species: str,
    target_minutes: int,
    rest_minutes: int | None,
    zone_index: int,
    plots: list[tuple[int, int]],
    request_id: str,
    client_ip: str | None,
) -> FocusSession:
    now = utcnow()
    if species not in SPECIES:
        raise bad_request("invalid_species", "수종을 다시 선택해 주세요.")
    try:
        validate_focus_minutes(target_minutes)
        rest_minutes = user.default_rest_minutes if rest_minutes is None else rest_minutes
        validate_rest_minutes(rest_minutes)
    except ValueError as exc:
        raise bad_request("invalid_minutes", str(exc))
    if not request_id or len(request_id) > 64:
        raise bad_request("invalid_request_id", "요청 ID가 필요합니다.")

    if kst_today() > settings.study_end:
        raise forbidden("study_ended", "스터디 기간이 끝나 새 집중 세션을 시작할 수 없습니다.")

    target_seconds = target_minutes * 60
    need = tree_count(target_seconds)
    cells = [(int(r), int(c)) for r, c in plots]
    if len(cells) != need:
        raise bad_request("wrong_plot_count", f"{need}칸을 선택해야 시작할 수 있습니다.")
    if len(set(cells)) != len(cells):
        raise bad_request("duplicate_plot", "서로 다른 칸을 선택해 주세요.")
    if any(not (0 <= r < ZONE_SIZE and 0 <= c < ZONE_SIZE) for r, c in cells):
        raise bad_request("plot_out_of_range", "숲 범위 밖의 칸입니다.")

    # 같은 사용자의 시작 요청을 직렬화한다(두 탭 경합).
    await db.execute(select(User.id).where(User.id == user.id).with_for_update())

    existing = (
        await db.execute(select(FocusSession).where(FocusSession.user_id == user.id, FocusSession.request_id == request_id))
    ).scalar_one_or_none()
    if existing is not None:
        # 같은 요청 ID 재전송(네트워크 재시도)은 같은 세션을 돌려준다.
        await db.commit()
        return existing

    active = await get_active(db, user.id)
    if active is not None:
        await settle(db, active, now)
        if active.status in ("focusing", "paused"):
            await db.rollback()
            raise conflict("active_session_exists", "이미 진행 중인 집중 세션이 있습니다.")

    zones = await _ensure_first_zone(db, user.id)
    if zone_index < 0 or zone_index > len(zones):
        raise bad_request("invalid_zone", "구역을 다시 선택해 주세요.")
    if zone_index == len(zones):
        # 새 구역은 기존 어떤 구역에도 필요한 빈 칸이 없을 때만 추가한다.
        for z in zones:
            if ZONE_SIZE * ZONE_SIZE - len(await _used_cells(db, z.id)) >= need:
                raise bad_request("zone_has_space", "기존 구역에 빈 칸이 남아 있어요.")
        zone = PersonalZone(user_id=user.id, zone_index=zone_index, created_at=now)
        db.add(zone)
        await db.flush()
    else:
        zone = zones[zone_index]

    taken = await _used_cells(db, zone.id)
    if any(cell in taken for cell in cells):
        await db.rollback()
        raise conflict("plot_taken", "이미 사용 중인 칸이 있어요. 다른 칸을 선택해 주세요.")

    library, rule_version = await hooks.detect_library(db, client_ip)

    session = FocusSession(
        user_id=user.id,
        request_id=request_id,
        zone_id=zone.id,
        species=species,
        size=tree_size(target_seconds),
        tree_count=need,
        target_seconds=target_seconds,
        rest_seconds=rest_minutes * 60,
        status="focusing",
        library_at_start=library,
        network_rule_version=rule_version,
        started_at=now,
        accumulated_seconds=0,
        current_interval_started_at=now,
        target_end_at=now + timedelta(seconds=target_seconds),
    )
    db.add(session)
    await db.flush()
    db.add(FocusInterval(session_id=session.id, started_at=now))
    for i, (r, c) in enumerate(cells):
        db.add(SessionPlot(session_id=session.id, user_id=user.id, zone_id=zone.id, row=r, col=c, ordinal=i))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise conflict("start_conflict", "다른 탭이나 기기에서 먼저 시작했어요. 새로고침해 주세요.")
    return session


# ── 상태 전이 ─────────────────────────────────────────────────────
async def _lock(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID | None = None) -> FocusSession:
    s = (
        await db.execute(select(FocusSession).where(FocusSession.id == session_id).with_for_update())
    ).scalar_one_or_none()
    if s is None or (user_id is not None and s.user_id != user_id):
        raise not_found("session_not_found", "집중 세션을 찾을 수 없습니다.")
    return s


async def _close_interval(db: AsyncSession, s: FocusSession, end: datetime) -> None:
    interval = (
        await db.execute(
            select(FocusInterval)
            .where(FocusInterval.session_id == s.id, FocusInterval.ended_at.is_(None))
            .order_by(FocusInterval.started_at.desc())
        )
    ).scalars().first()
    if interval is not None:
        interval.ended_at = max(interval.started_at, end)


async def _make_trees(db: AsyncSession, s: FocusSession, state: str, at: datetime) -> list[Tree]:
    plots = (
        await db.execute(select(SessionPlot).where(SessionPlot.session_id == s.id).order_by(SessionPlot.ordinal))
    ).scalars().all()
    trees = []
    for p in plots:
        t = Tree(
            session_id=s.id,
            user_id=s.user_id,
            plot_id=p.id,
            ordinal=p.ordinal,
            species=s.species,
            size=s.size,
            state=state,
            created_at=at,
        )
        db.add(t)
        trees.append(t)
    await db.flush()
    return trees


async def settle(db: AsyncSession, s: FocusSession, now: datetime) -> bool:
    """목표 시각이 지난 focusing 세션을 완료로 확정한다. 호출자가 행을 잠갔다고 가정한다.

    변경했으면 True. 커밋은 호출자 몫.
    """
    if s.status != "focusing" or s.target_end_at is None or now < s.target_end_at:
        return False
    end = s.target_end_at
    await _close_interval(db, s, end)
    s.status = "completed"
    s.accumulated_seconds = s.target_seconds
    s.observed_seconds = s.target_seconds
    s.credited_seconds = s.target_seconds
    s.current_interval_started_at = None
    s.completed_at = end
    s.version += 1
    trees = await _make_trees(db, s, "library" if s.library_at_start else "normal", end)
    await hooks.on_trees_confirmed(db, s, trees)
    return True


async def pause(db: AsyncSession, user: User, session_id: uuid.UUID) -> FocusSession:
    now = utcnow()
    s = await _lock(db, session_id, user.id)
    if await settle(db, s, now):
        await db.commit()
        return s
    if s.status != "focusing":
        await db.commit()
        raise conflict("not_focusing", "집중 중인 세션만 일시정지할 수 있습니다.")
    await _close_interval(db, s, now)
    s.accumulated_seconds = focused_seconds(s, now)
    s.current_interval_started_at = None
    s.target_end_at = None
    s.status = "paused"
    s.version += 1
    await db.commit()
    return s


async def resume(db: AsyncSession, user: User, session_id: uuid.UUID) -> FocusSession:
    now = utcnow()
    s = await _lock(db, session_id, user.id)
    if s.status != "paused":
        await db.commit()
        raise conflict("not_paused", "일시정지된 세션만 재개할 수 있습니다.")
    # 수종/크기/도서관 판정/예약 위치는 그대로 유지한다(재개는 새 시작이 아님).
    s.status = "focusing"
    s.current_interval_started_at = now
    s.target_end_at = now + timedelta(seconds=s.target_seconds - s.accumulated_seconds)
    s.version += 1
    db.add(FocusInterval(session_id=s.id, started_at=now))
    await db.commit()
    return s


async def abandon(db: AsyncSession, user: User, session_id: uuid.UUID) -> FocusSession:
    now = utcnow()
    s = await _lock(db, session_id, user.id)
    if await settle(db, s, now):
        # 서버 시각상 이미 목표에 도달 → 완료가 우선
        await db.commit()
        return s
    if s.status in ("completed", "abandoned"):
        await db.commit()
        return s
    if s.status == "focusing":
        await _close_interval(db, s, now)
    s.observed_seconds = focused_seconds(s, now)
    s.status = "abandoned"
    s.credited_seconds = 0
    s.current_interval_started_at = None
    s.target_end_at = None
    s.abandoned_at = now
    s.version += 1
    await _make_trees(db, s, "wilted", now)
    await db.commit()
    return s


async def rest(db: AsyncSession, user: User, session_id: uuid.UUID, action: str) -> FocusSession:
    """정상 완료 후 수동 휴식 시작/종료. 휴식은 보상과 무관하다."""
    now = utcnow()
    s = await _lock(db, session_id, user.id)
    await settle(db, s, now)
    if s.status != "completed":
        await db.commit()
        raise conflict("not_completed", "정상 완료한 세션에서만 휴식을 시작할 수 있습니다.")
    if action == "start":
        if s.rest_started_at is None:
            s.rest_started_at = now
            s.version += 1
    elif action == "end":
        if s.rest_started_at is not None and s.rest_ended_at is None:
            s.rest_ended_at = min(now, s.rest_started_at + timedelta(seconds=s.rest_seconds))
            s.version += 1
    else:
        await db.commit()
        raise bad_request("invalid_action", "알 수 없는 휴식 동작입니다.")
    await db.commit()
    return s


async def get_for_user(db: AsyncSession, user: User, session_id: uuid.UUID) -> FocusSession:
    """조회 시에도 목표 시각이 지났으면 확정해 최신 상태를 돌려준다."""
    s = await _lock(db, session_id, user.id)
    await settle(db, s, utcnow())
    await db.commit()
    return s


async def settle_due(db: AsyncSession, limit: int = 50) -> int:
    """워커용: 목표 시각이 지난 세션을 하나씩 잠가 확정한다. SKIP LOCKED로 요청과 충돌하지 않는다."""
    now = utcnow()
    ids = (
        await db.execute(
            select(FocusSession.id)
            .where(FocusSession.status == "focusing", FocusSession.target_end_at <= now)
            .limit(limit)
        )
    ).scalars().all()
    done = 0
    for sid in ids:
        s = (
            await db.execute(
                select(FocusSession).where(FocusSession.id == sid).with_for_update(skip_locked=True)
            )
        ).scalar_one_or_none()
        if s is not None and await settle(db, s, now):
            done += 1
        await db.commit()
    return done


# ── 직렬화 ────────────────────────────────────────────────────────
async def serialize(db: AsyncSession, s: FocusSession) -> dict:
    now = utcnow()
    zone = await db.get(PersonalZone, s.zone_id)
    plots = (
        await db.execute(select(SessionPlot).where(SessionPlot.session_id == s.id).order_by(SessionPlot.ordinal))
    ).scalars().all()
    focused = focused_seconds(s, now)
    rest_end = s.rest_started_at + timedelta(seconds=s.rest_seconds) if s.rest_started_at else None
    return {
        "id": str(s.id),
        "status": s.status,
        "species": s.species,
        "size": s.size,
        "treeCount": s.tree_count,
        "targetSeconds": s.target_seconds,
        "focusedSeconds": focused,
        "remainingSeconds": max(0, s.target_seconds - focused),
        "targetEndAt": s.target_end_at.isoformat() if s.target_end_at else None,
        "startedAt": s.started_at.isoformat(),
        "completedAt": s.completed_at.isoformat() if s.completed_at else None,
        "abandonedAt": s.abandoned_at.isoformat() if s.abandoned_at else None,
        "creditedSeconds": s.credited_seconds,
        "libraryAtStart": s.library_at_start,
        "zoneIndex": zone.zone_index if zone else 0,
        "plots": [{"row": p.row, "col": p.col} for p in plots],
        "rest": {
            "seconds": s.rest_seconds,
            "state": rest_state(s, now),
            "endsAt": rest_end.isoformat() if rest_end else None,
        },
        "version": s.version,
        "serverNow": now.isoformat(),
    }


async def success_seconds_between(db: AsyncSession, user_id: uuid.UUID | None, start: datetime, end: datetime) -> int:
    """[start, end)에 걸친 '성공 세션'의 집중 구간 초 합계(자정 분할용)."""
    q = (
        select(FocusInterval.started_at, FocusInterval.ended_at)
        .join(FocusSession, FocusSession.id == FocusInterval.session_id)
        .where(
            FocusSession.status == "completed",
            FocusInterval.ended_at.is_not(None),
            FocusInterval.started_at < end,
            FocusInterval.ended_at > start,
        )
    )
    if user_id is not None:
        q = q.where(FocusSession.user_id == user_id)
    total = 0
    for a, b in (await db.execute(q)).all():
        total += int((min(b, end) - max(a, start)).total_seconds())
    return total


async def count_trees(db: AsyncSession, user_id: uuid.UUID | None, start: datetime, end: datetime, states=("normal", "library")) -> int:
    q = select(func.count()).select_from(Tree).where(Tree.state.in_(states), Tree.created_at >= start, Tree.created_at < end)
    if user_id is not None:
        q = q.where(Tree.user_id == user_id)
    return (await db.execute(q)).scalar_one()
