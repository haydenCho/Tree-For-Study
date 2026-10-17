"""운영자 전용 라우트: 가입 승인/거부, 회원 중지, 초대 발급/폐기.

이 응답에는 실명·이메일이 포함되므로 operator 의존성으로만 접근한다.
"""
import uuid

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import operator
from app.core.clock import utcnow
from app.core.db import get_session
from app.models import Invite, User
from app.schemas.common import CamelModel
from app.services import membership

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
