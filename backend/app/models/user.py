"""회원·초대·토큰 세션 모델(docs/10-focus-and-jwt.md).

- users.status: pending(가입 대기) → active(운영자 승인) / rejected / disabled.
- users.role: member / operator.
- 실명·이메일은 본인과 운영자만 조회한다. 공개 화면은 display_name + avatar_emoji만 쓴다.
- auth_token_sessions: refresh 토큰의 해시만 저장한다. 회전마다 새 행(sid)을 만들고
  같은 family_id로 묶어 재사용 감지 시 패밀리 전체를 폐기한다.
"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

USER_STATUSES = ("pending", "active", "rejected", "disabled")
USER_ROLES = ("member", "operator")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(f"status IN {USER_STATUSES}", name="status"),
        CheckConstraint(f"role IN {USER_ROLES}", name="role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # 정규화 규칙: 앞뒤 공백 제거 + 전체 소문자(app.services.auth.normalize_email)
    email_normalized: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    real_name: Mapped[str] = mapped_column(String(40), nullable=False)
    display_name: Mapped[str] = mapped_column(String(20), nullable=False)
    bio: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    avatar_emoji: Mapped[str] = mapped_column(String(64), nullable=False, default="🌱")
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="member")
    default_focus_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    default_rest_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    invite_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invites.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 온라인 표시용 heartbeat 시각(집중 상태와 별개)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", use_alter=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuthTokenSession(Base):
    __tablename__ = "auth_token_sessions"

    sid: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    """운영자 조치(승인/거부/출석 정정 등) 기록. 비밀번호·토큰·IP는 남기지 않는다."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    target: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    reason: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
