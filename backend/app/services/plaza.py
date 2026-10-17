"""공동 숲(광장) 조회.

공개 정보만 담는다: 표시 이름·아바타·소개·공부 상태(공부 중/일시정지/휴식/대기)·성공 집계·
공개 기록 피드. 이메일·실명·계정 ID 외 식별자·접속 IP·비공개 제목은 넣지 않는다.
순위·경쟁 요소는 없다.
"""
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import kst_day_bounds, kst_today, utcnow
from app.models import CommunityPlacement, DailyEntry, FocusSession, Goal, Tree, User
from app.services import attendance, focus

ONLINE_SECONDS = 90
FEED_DAYS = 14


def public_member(u: User) -> dict:
    return {"id": str(u.id), "displayName": u.display_name, "avatarEmoji": u.avatar_emoji, "bio": u.bio}


async def _presence(db: AsyncSession, members: list[User]) -> dict:
    now = utcnow()
    ids = [m.id for m in members]
    if not ids:
        return {}
    active = (
        await db.execute(select(FocusSession).where(FocusSession.user_id.in_(ids), FocusSession.status.in_(("focusing", "paused"))))
    ).scalars().all()
    state = {s.user_id: s.status for s in active}
    # 최근 완료 세션의 휴식 상태
    resting = (
        await db.execute(
            select(FocusSession).where(
                FocusSession.user_id.in_(ids),
                FocusSession.status == "completed",
                FocusSession.rest_started_at.is_not(None),
                FocusSession.rest_ended_at.is_(None),
                FocusSession.rest_started_at > now - timedelta(hours=1),
            )
        )
    ).scalars().all()
    for s in resting:
        if s.user_id not in state and focus.rest_state(s, now) == "resting":
            state[s.user_id] = "resting"
    return state


async def build(db: AsyncSession) -> dict:
    today = kst_today()
    start, end = kst_day_bounds(today)
    now = utcnow()
    members = list((await db.execute(select(User).where(User.status == "active").order_by(User.created_at))).scalars().all())
    by_id = {m.id: m for m in members}
    presence = await _presence(db, members)

    # 숲 배치
    rows = (
        await db.execute(
            select(CommunityPlacement, Tree)
            .join(Tree, Tree.id == CommunityPlacement.tree_id)
            .order_by(CommunityPlacement.zone_index)
        )
    ).all()
    zones: dict[int, list[dict]] = {}
    for p, t in rows:
        owner = by_id.get(p.user_id)
        zones.setdefault(p.zone_index, []).append(
            {
                "row": p.row,
                "col": p.col,
                "species": t.species,
                "size": t.size,
                "state": t.state,
                "owner": public_member(owner) if owner else None,
            }
        )
    zone_list = [{"index": i, "cells": zones[i]} for i in sorted(zones)] or [{"index": 0, "cells": []}]

    # 오늘 출석
    kind = await attendance.kind_of(db, today)
    att_rows = await attendance.rows_for(db, list(by_id), today, today)

    cards = []
    for m in members:
        cards.append(
            {
                **public_member(m),
                "state": presence.get(m.id, "idle"),
                "online": bool(m.last_seen_at and (now - m.last_seen_at).total_seconds() <= ONLINE_SECONDS),
                "todaySuccessSeconds": await focus.success_seconds_between(db, m.id, start, end),
                "todayTrees": await focus.count_trees(db, m.id, start, end),
                "attendance": attendance.derive_status(kind, att_rows.get((m.id, today)), today, today),
            }
        )

    member_ids = list(by_id)
    total_seconds = 0
    total_trees = 0
    if member_ids:
        total_seconds = (
            await db.execute(
                select(func.coalesce(func.sum(FocusSession.credited_seconds), 0)).where(
                    FocusSession.status == "completed", FocusSession.user_id.in_(member_ids)
                )
            )
        ).scalar_one()
        total_trees = (
            await db.execute(
                select(func.count()).select_from(Tree).where(Tree.state.in_(("normal", "library")), Tree.user_id.in_(member_ids))
            )
        ).scalar_one()

    # 공개 일일 기록 피드(최근 14일)
    feed = []
    if member_ids:
        entries = (
            await db.execute(
                select(DailyEntry)
                .where(
                    DailyEntry.is_public.is_(True),
                    DailyEntry.user_id.in_(member_ids),
                    DailyEntry.entry_date >= today - timedelta(days=FEED_DAYS),
                )
                .order_by(DailyEntry.entry_date.desc(), DailyEntry.updated_at.desc())
                .limit(20)
            )
        ).scalars().all()
        for e in entries:
            goals = (
                await db.execute(select(Goal.done).where(Goal.user_id == e.user_id, Goal.goal_date == e.entry_date))
            ).scalars().all()
            text = (e.plan_text or e.record_text or "").strip().replace("\n", " ")
            feed.append(
                {
                    "kind": "daily",
                    "member": public_member(by_id[e.user_id]),
                    "date": e.entry_date.isoformat(),
                    "excerpt": text[:80],
                    "goalsDone": sum(1 for g in goals if g),
                    "goalsTotal": len(goals),
                }
            )

    return {
        "today": today.isoformat(),
        "summary": {
            "totalSuccessSeconds": int(total_seconds),
            "totalTrees": int(total_trees),
            "todaySuccessSeconds": sum(c["todaySuccessSeconds"] for c in cards),
            "todayPresent": sum(1 for c in cards if c["attendance"] == "present"),
            "todayKind": kind,
            "members": len(cards),
            "focusingNow": sum(1 for c in cards if c["state"] in ("focusing", "paused")),
        },
        "zones": zone_list,
        "members": cards,
        "feed": feed,
    }
