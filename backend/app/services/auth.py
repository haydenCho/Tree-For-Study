"""가입·로그인·refresh 회전·로그아웃 서비스(docs/10-focus-and-jwt.md).

refresh 회전 규칙:
- 사용할 때마다 현재 행을 rotated 처리하고 같은 family_id로 새 행(새 sid)을 만든다.
- 이미 회전된 토큰이 다시 오면 재사용으로 보고 family 전체를 폐기한다.
  단, 회전 직후 짧은 유예(refresh_race_grace_seconds) 안에서는 여러 탭의 동시 refresh로
  보고 폐기하지 않고 409(refresh_race)를 돌려준다. 쿠키 저장소는 탭끼리 공유되므로
  프론트엔드가 잠시 후 한 번 재시도하면 새 쿠키로 성공한다.
"""
import random
import re
import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.core.config import get_settings
from app.core.errors import ApiError, bad_request, conflict, forbidden, unauthorized
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_opaque_token,
    verify_password,
)
from app.models import AuthTokenSession, Invite, User

settings = get_settings()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN = 12
PASSWORD_MAX = 128


def normalize_email(raw: str) -> str:
    """이메일 정규화 규칙: 앞뒤 공백 제거 후 전체 소문자. DB unique로 중복을 막는다."""
    return (raw or "").strip().lower()


def validate_email(email: str) -> None:
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise bad_request("invalid_email", "이메일 형식을 확인해 주세요.")


def validate_password(password: str) -> None:
    if not PASSWORD_MIN <= len(password or "") <= PASSWORD_MAX:
        raise bad_request("invalid_password", f"비밀번호는 {PASSWORD_MIN}~{PASSWORD_MAX}자여야 합니다.")


def _default_display_name() -> str:
    # 실명/이메일이 공개 화면에 새지 않도록 임의의 기본 표시 이름을 만든다.
    return f"새싹{random.randint(1000, 9999)}"


async def register(
    db: AsyncSession, *, invite_code: str, email: str, real_name: str, password: str, password_confirm: str
) -> User:
    now = utcnow()
    email_n = normalize_email(email)
    validate_email(email_n)
    real_name = (real_name or "").strip()
    if not 1 <= len(real_name) <= 40:
        raise bad_request("invalid_real_name", "실명은 1~40자로 입력해 주세요.")
    validate_password(password)
    if password != password_confirm:
        raise bad_request("password_mismatch", "비밀번호 확인이 일치하지 않습니다.")

    invite = (
        await db.execute(
            select(Invite).where(Invite.code_hash == hash_token((invite_code or "").strip())).with_for_update()
        )
    ).scalar_one_or_none()
    if (
        invite is None
        or invite.revoked_at is not None
        or invite.expires_at <= now
        or invite.use_count >= invite.max_uses
    ):
        raise bad_request("invalid_invite", "초대 코드가 유효하지 않거나 만료되었습니다.")

    exists = (await db.execute(select(User.id).where(User.email_normalized == email_n))).first()
    if exists:
        raise conflict("email_taken", "이미 가입된 이메일입니다.")

    invite.use_count += 1
    user = User(
        email_normalized=email_n,
        real_name=real_name,
        display_name=_default_display_name(),
        password_hash=hash_password(password),
        status="pending",
        role="member",
        invite_id=invite.id,
        created_at=now,
    )
    db.add(user)
    await db.commit()
    return user


async def authenticate(db: AsyncSession, *, email: str, password: str) -> User:
    user = (
        await db.execute(select(User).where(User.email_normalized == normalize_email(email)))
    ).scalar_one_or_none()
    if not verify_password(password or "", user.password_hash if user else None):
        raise unauthorized("invalid_credentials", "이메일 또는 비밀번호가 올바르지 않습니다.")
    if user.status == "disabled":
        raise forbidden("account_disabled", "사용이 중지된 계정입니다. 운영자에게 문의해 주세요.")
    return user


async def issue_tokens(db: AsyncSession, user: User, *, family_id: uuid.UUID | None = None) -> tuple[str, str]:
    """새 토큰 세션 행을 만들고 (access JWT, refresh 원문)을 돌려준다. 커밋은 호출자 몫."""
    now = utcnow()
    refresh = new_opaque_token()
    row = AuthTokenSession(
        user_id=user.id,
        family_id=family_id or uuid.uuid4(),
        refresh_hash=hash_token(refresh),
        created_at=now,
        expires_at=now + timedelta(seconds=settings.refresh_ttl_seconds),
    )
    db.add(row)
    await db.flush()
    access = create_access_token(user_id=str(user.id), session_id=str(row.sid))
    return access, refresh


async def revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    await db.execute(
        update(AuthTokenSession)
        .where(AuthTokenSession.family_id == family_id, AuthTokenSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


async def revoke_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(AuthTokenSession)
        .where(AuthTokenSession.user_id == user_id, AuthTokenSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


async def rotate_refresh(db: AsyncSession, refresh: str | None) -> tuple[User, str, str]:
    if not refresh:
        raise unauthorized("no_refresh", "다시 로그인해 주세요.")
    now = utcnow()
    row = (
        await db.execute(
            select(AuthTokenSession).where(AuthTokenSession.refresh_hash == hash_token(refresh)).with_for_update()
        )
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        raise unauthorized("invalid_refresh", "다시 로그인해 주세요.")
    if row.rotated_at is not None:
        if (now - row.rotated_at).total_seconds() <= settings.refresh_race_grace_seconds:
            raise ApiError(409, "refresh_race", "다른 탭에서 갱신 중입니다. 잠시 후 다시 시도합니다.")
        # 오래전에 회전된 토큰의 재사용 = 탈취 의심 → 패밀리 전체 폐기
        await revoke_family(db, row.family_id)
        await db.commit()
        raise unauthorized("refresh_reused", "보안을 위해 로그아웃되었습니다. 다시 로그인해 주세요.")
    if row.expires_at <= now:
        raise unauthorized("refresh_expired", "로그인이 만료되었습니다. 다시 로그인해 주세요.")

    user = await db.get(User, row.user_id)
    if user is None or user.status in ("disabled",):
        await revoke_family(db, row.family_id)
        await db.commit()
        raise unauthorized("account_unavailable", "계정을 사용할 수 없습니다.")

    row.rotated_at = now
    access, new_refresh = await issue_tokens(db, user, family_id=row.family_id)
    await db.commit()
    return user, access, new_refresh


async def logout(db: AsyncSession, refresh: str | None) -> None:
    if not refresh:
        return
    row = (
        await db.execute(select(AuthTokenSession).where(AuthTokenSession.refresh_hash == hash_token(refresh)))
    ).scalar_one_or_none()
    if row is not None:
        await revoke_family(db, row.family_id)
        await db.commit()
