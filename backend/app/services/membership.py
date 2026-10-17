"""운영자 승인·초대 관리 서비스.

승인 시 정원(최대 10명) 검사는 advisory lock으로 직렬화한 트랜잭션 안에서 수행한다.
동시에 두 명을 승인해도 11번째 활성 회원은 생기지 않는다.
"""
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.core.config import get_settings
from app.core.db import LOCK_MEMBERSHIP, advisory_xact_lock
from app.core.errors import bad_request, conflict, not_found
from app.core.security import hash_token, new_opaque_token
from app.models import AuditEvent, Invite, User
from app.services.auth import revoke_all_for_user

settings = get_settings()


async def audit(db: AsyncSession, actor: User | None, action: str, target: str = "", reason: str = "") -> None:
    db.add(AuditEvent(actor_id=actor.id if actor else None, action=action, target=target, reason=reason, created_at=utcnow()))


async def approve(db: AsyncSession, operator: User, user_id: uuid.UUID) -> User:
    await advisory_xact_lock(db, LOCK_MEMBERSHIP)
    user = (await db.execute(select(User).where(User.id == user_id).with_for_update())).scalar_one_or_none()
    if user is None:
        raise not_found()
    if user.status == "active":
        return user
    if user.status not in ("pending", "rejected"):
        raise bad_request("invalid_status", "승인할 수 없는 상태입니다.")
    active_count = (await db.execute(select(func.count()).select_from(User).where(User.status == "active"))).scalar_one()
    if active_count >= settings.max_active_members:
        raise conflict("capacity_full", f"활성 멤버 정원({settings.max_active_members}명)이 찼습니다.")
    user.status = "active"
    user.approved_at = utcnow()
    await audit(db, operator, "membership.approve", str(user.id))
    await db.commit()
    return user


async def reject(db: AsyncSession, operator: User, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise not_found()
    if user.status != "pending":
        raise bad_request("invalid_status", "대기 중인 신청만 거부할 수 있습니다.")
    user.status = "rejected"
    await revoke_all_for_user(db, user.id)
    await audit(db, operator, "membership.reject", str(user.id))
    await db.commit()
    return user


async def disable(db: AsyncSession, operator: User, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise not_found()
    if user.id == operator.id:
        raise bad_request("cannot_disable_self", "자기 자신은 중지할 수 없습니다.")
    user.status = "disabled"
    await revoke_all_for_user(db, user.id)
    await audit(db, operator, "membership.disable", str(user.id))
    await db.commit()
    return user


async def create_invite(
    db: AsyncSession, creator: User | None, *, max_uses: int | None = None, ttl_days: int | None = None, label: str = ""
) -> tuple[Invite, str]:
    """초대 코드를 만들고 원문을 한 번만 돌려준다. DB에는 해시만 저장한다."""
    max_uses = max_uses or settings.invite_default_max_uses
    ttl_days = ttl_days or settings.invite_ttl_days
    if not 1 <= max_uses <= 50 or not 1 <= ttl_days <= 30:
        raise bad_request("invalid_invite_options", "사용 횟수 1~50, 유효기간 1~30일로 설정해 주세요.")
    code = new_opaque_token()[:16]
    now = utcnow()
    invite = Invite(
        code_hash=hash_token(code),
        label=label[:60],
        max_uses=max_uses,
        expires_at=now + timedelta(days=ttl_days),
        created_by=creator.id if creator else None,
        created_at=now,
    )
    db.add(invite)
    await db.commit()
    return invite, code


async def revoke_invite(db: AsyncSession, invite_id: uuid.UUID) -> Invite:
    invite = await db.get(Invite, invite_id)
    if invite is None:
        raise not_found()
    if invite.revoked_at is None:
        invite.revoked_at = utcnow()
        await db.commit()
    return invite
