"""운영자 전용 라우트: 가입 승인/거부, 회원 중지, 초대 발급/폐기,
도서관 IP 등록·접속 IP 진단, 휴무일 지정, 출석 정정.

이 응답에는 실명·이메일이 포함되므로 operator 의존성으로만 접근한다.
"""
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import operator
from app.core.client_ip import client_ip
from app.core.clock import kst_today, utcnow
from app.core.db import get_session
from app.models import Invite, User
from app.schemas.common import CamelModel
from app.services import attendance, library, membership, records

router = APIRouter(prefix="/admin", tags=["admin"])


def _member_row(u: User) -> dict:
    return {
        "id": str(u.id),
        "email": u.email_normalized,
        "realName": u.real_name,
        "displayName": u.display_name,
        "avatarEmoji": u.avatar_emoji,
        "status": u.status,
        "role": u.role,
        "createdAt": u.created_at.isoformat(),
        "approvedAt": u.approved_at.isoformat() if u.approved_at else None,
    }


@router.get("/membership-requests")
async def membership_requests(_: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> dict:
    rows = (await db.execute(select(User).where(User.status == "pending").order_by(User.created_at))).scalars().all()
    return {"items": [_member_row(u) for u in rows]}


@router.post("/membership-requests/{user_id}/approve")
async def approve(user_id: uuid.UUID, op: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> dict:
    return _member_row(await membership.approve(db, op, user_id))


@router.post("/membership-requests/{user_id}/reject")
async def reject(user_id: uuid.UUID, op: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> dict:
    return _member_row(await membership.reject(db, op, user_id))


@router.get("/members")
async def members(_: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> dict:
    rows = (await db.execute(select(User).order_by(User.created_at))).scalars().all()
    return {"items": [_member_row(u) for u in rows]}


@router.post("/members/{user_id}/disable")
async def disable(user_id: uuid.UUID, op: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> dict:
    return _member_row(await membership.disable(db, op, user_id))


class InviteIn(CamelModel):
    max_uses: int | None = Field(default=None, ge=1, le=50)
    ttl_days: int | None = Field(default=None, ge=1, le=30)
    label: str = Field(default="", max_length=60)


def _invite_row(inv: Invite) -> dict:
    now = utcnow()
    state = "revoked" if inv.revoked_at else "expired" if inv.expires_at <= now else "used_up" if inv.use_count >= inv.max_uses else "active"
    return {
        "id": str(inv.id),
        "label": inv.label,
        "maxUses": inv.max_uses,
        "useCount": inv.use_count,
        "expiresAt": inv.expires_at.isoformat(),
        "state": state,
    }


@router.get("/invites")
async def list_invites(_: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> dict:
    rows = (await db.execute(select(Invite).order_by(Invite.created_at.desc()))).scalars().all()
    return {"items": [_invite_row(i) for i in rows]}


@router.post("/invites", status_code=201)
async def create_invite(body: InviteIn, op: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> dict:
    invite, code = await membership.create_invite(db, op, max_uses=body.max_uses, ttl_days=body.ttl_days, label=body.label)
    # 코드 원문은 이 응답에서 한 번만 보여 준다.
    return {**_invite_row(invite), "code": code}


@router.post("/invites/{invite_id}/revoke")
async def revoke_invite(invite_id: uuid.UUID, _: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> dict:
    return _invite_row(await membership.revoke_invite(db, invite_id))


# ── 2단계: 도서관 네트워크·진단, 스터디 날짜, 출석 정정 ─────────────────
@router.get("/network-diagnostic")
async def network_diagnostic(request: Request, _: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> dict:
    """서버가 관측한 현재 접속 IP(운영자 전용, 캐시 금지). Caddy를 거친 신뢰 판정 결과다."""
    ip = client_ip(request)
    return {
        "observedIp": ip,
        "viaTrustedProxy": bool(request.client and ip != request.client.host),
        "recognized": await library.is_library_ip(db, ip),
        "ruleVersion": await library.rule_version(db),
    }


class NetworkIn(CamelModel):
    network: str = Field(max_length=64)
    label: str = Field(default="", max_length=60)


def _network_row(n) -> dict:
    return {"id": str(n.id), "network": n.network, "label": n.label, "createdAt": n.created_at.isoformat()}


@router.get("/library-networks")
async def list_library_networks(_: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> dict:
    return {"items": [_network_row(n) for n in await library.list_networks(db)], "ruleVersion": await library.rule_version(db)}


@router.post("/library-networks", status_code=201)
async def add_library_network(body: NetworkIn, _: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> dict:
    return _network_row(await library.add_network(db, body.network, body.label))


@router.delete("/library-networks/{network_id}", status_code=204)
async def delete_library_network(network_id: uuid.UUID, _: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> None:
    await library.remove_network(db, network_id)


class StudyDateIn(CamelModel):
    kind: str
    note: str = Field(default="", max_length=100)


@router.put("/study-dates/{day}")
async def set_study_date(day: str, body: StudyDateIn, op: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> dict:
    row = await attendance.set_date_kind(db, op, records.parse_date(day), body.kind, body.note)
    return {"date": row.day.isoformat(), "kind": row.kind, "note": row.note}


@router.get("/attendance")
async def attendance_roster(day: str | None = None, _: User = Depends(operator), db: AsyncSession = Depends(get_session)) -> dict:
    """특정 날짜(기본 오늘)의 멤버별 출석 상태."""
    d = records.parse_date(day) if day else kst_today()
    kind = await attendance.kind_of(db, d)
    members = (await db.execute(select(User).where(User.status == "active").order_by(User.created_at))).scalars().all()
    rows = await attendance.rows_for(db, [m.id for m in members], d, d)
    today = kst_today()
    return {
        "date": d.isoformat(),
        "kind": kind,
        "items": [
            {
                "userId": str(m.id),
                "displayName": m.display_name,
                "realName": m.real_name,
                "status": attendance.derive_status(kind, rows.get((m.id, d)), d, today),
                "reason": rows[(m.id, d)].reason if (m.id, d) in rows else "",
            }
            for m in members
        ],
    }


class AttendanceFixIn(CamelModel):
    status: str
    reason: str = Field(max_length=300)


@router.put("/attendance/{user_id}/{day}")
async def correct_attendance(
    user_id: uuid.UUID, day: str, body: AttendanceFixIn, op: User = Depends(operator), db: AsyncSession = Depends(get_session)
) -> dict:
    row = await attendance.correct(db, op, user_id, records.parse_date(day), body.status, body.reason)
    return {"userId": str(row.user_id), "date": row.day.isoformat(), "status": row.status, "reason": row.reason}
