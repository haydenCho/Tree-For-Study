"""회원·인증 요청/응답 스키마."""
import uuid

from pydantic import Field

from app.schemas.common import CamelModel


class RegisterIn(CamelModel):
    invite_code: str = Field(max_length=200)
    email: str = Field(max_length=254)
    real_name: str = Field(max_length=40)
    password: str = Field(max_length=256)
    password_confirm: str = Field(max_length=256)


class LoginIn(CamelModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


class PasswordChangeIn(CamelModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(max_length=256)
    new_password_confirm: str = Field(max_length=256)


class MeOut(CamelModel):
    """본인 전용 응답. 실명·이메일을 포함하므로 다른 사람에게 반환하지 않는다."""

    id: uuid.UUID
    email: str
    real_name: str
    display_name: str
    bio: str
    avatar_emoji: str
    status: str
    role: str
    default_focus_minutes: int
    default_rest_minutes: int


class ProfileIn(CamelModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_emoji: str | None = None
    default_focus_minutes: int | None = None
    default_rest_minutes: int | None = None


class PublicMemberOut(CamelModel):
    """공개 카드용. 이메일·실명·계정 상태를 넣지 않는다."""

    id: uuid.UUID
    display_name: str
    avatar_emoji: str
    bio: str


def me_out(user) -> MeOut:
    return MeOut(
        id=user.id,
        email=user.email_normalized,
        real_name=user.real_name,
        display_name=user.display_name,
        bio=user.bio,
        avatar_emoji=user.avatar_emoji,
        status=user.status,
        role=user.role,
        default_focus_minutes=user.default_focus_minutes,
        default_rest_minutes=user.default_rest_minutes,
    )
