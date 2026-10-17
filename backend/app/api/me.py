"""본인 정보·프로필 라우트.

GET /api/me는 승인 대기(pending) 상태에서도 호출할 수 있다(승인 게이트 화면용).
프로필 수정은 active 회원만 가능하며, 표시 이름 2~20자, 소개 160자 이하,
아바타는 서버 이모지 허용 목록으로 검증한다.
"""
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import active_member, current_user
from app.core.clock import utcnow
from app.core.db import get_session
from app.core.emoji import is_allowed_emoji
from app.core.errors import bad_request
from app.core.policy import validate_focus_minutes, validate_rest_minutes
from app.models import User
from app.schemas.user import MeOut, ProfileIn, me_out

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeOut, response_model_by_alias=True)
async def get_me(user: User = Depends(current_user)) -> MeOut:
    return me_out(user)


@router.get("/me/profile", response_model=MeOut, response_model_by_alias=True)
async def get_profile(user: User = Depends(active_member)) -> MeOut:
    return me_out(user)


@router.patch("/me/profile", response_model=MeOut, response_model_by_alias=True)
async def update_profile(
    body: ProfileIn, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)
) -> MeOut:
    if body.display_name is not None:
        name = body.display_name.strip()
        if not 2 <= len(name) <= 20:
            raise bad_request("invalid_display_name", "표시 이름은 2~20자로 입력해 주세요.")
        user.display_name = name
    if body.bio is not None:
        bio = body.bio.strip()
        if len(bio) > 160:
            raise bad_request("invalid_bio", "소개는 160자 이하로 입력해 주세요.")
        user.bio = bio
    if body.avatar_emoji is not None:
        if not is_allowed_emoji(body.avatar_emoji):
            raise bad_request("invalid_emoji", "목록에 있는 이모지 하나를 선택해 주세요.")
        user.avatar_emoji = body.avatar_emoji
    if body.default_focus_minutes is not None:
        try:
            validate_focus_minutes(body.default_focus_minutes)
        except ValueError as exc:
            raise bad_request("invalid_focus_minutes", str(exc))
        user.default_focus_minutes = body.default_focus_minutes
    if body.default_rest_minutes is not None:
        try:
            validate_rest_minutes(body.default_rest_minutes)
        except ValueError as exc:
            raise bad_request("invalid_rest_minutes", str(exc))
        user.default_rest_minutes = body.default_rest_minutes
    await db.commit()
    return me_out(user)


@router.post("/presence")
async def heartbeat(user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    """30초 heartbeat. 온라인 표시 전용이며 집중 세션 상태에는 영향을 주지 않는다."""
    now = utcnow()
    # 쓰기 빈도를 줄이기 위해 15초 이내 갱신은 건너뛴다.
    if user.last_seen_at is None or now - user.last_seen_at > timedelta(seconds=15):
        user.last_seen_at = now
        await db.commit()
    return {"ok": True}
