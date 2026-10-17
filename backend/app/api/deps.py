"""인증·권한 의존성.

매 요청마다 JWT 서명/claims를 검증한 뒤 DB에서 sid 폐기 여부와 회원 상태를 확인한다
(10명 규모라 매번 조회해도 부담이 없다). 그래서 로그아웃·차단 즉시 기존 access JWT도
거부된다.
- current_user: 로그인만 확인(pending도 허용) — /me 등 승인 대기 화면용.
- active_member: 운영자 승인(active)된 회원만 — 모든 스터디 데이터 API.
- operator: 운영자 전용.
"""
import uuid

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import forbidden, unauthorized
from app.core.security import TokenError, decode_access_token
from app.models import AuthTokenSession, User


async def current_user(request: Request, db: AsyncSession = Depends(get_session)) -> User:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise unauthorized()
    try:
        claims = decode_access_token(token.strip())
        sid = uuid.UUID(claims["sid"])
        user_id = uuid.UUID(claims["sub"])
    except (TokenError, ValueError, KeyError):
        raise unauthorized("invalid_token", "인증이 만료되었습니다.")

    token_session = await db.get(AuthTokenSession, sid)
    if token_session is None or token_session.revoked_at is not None or token_session.user_id != user_id:
        raise unauthorized("session_revoked", "인증이 만료되었습니다.")
    user = await db.get(User, user_id)
    if user is None:
        raise unauthorized("invalid_token", "인증이 만료되었습니다.")
    if user.status == "disabled":
        raise forbidden("account_disabled", "사용이 중지된 계정입니다.")
    request.state.sid = sid
    request.state.family_id = token_session.family_id
    return user


async def active_member(user: User = Depends(current_user)) -> User:
    if user.status != "active":
        raise forbidden("membership_not_active", "운영자 승인 후 이용할 수 있습니다.")
    return user


async def operator(user: User = Depends(active_member)) -> User:
    if user.role != "operator":
        raise forbidden("operator_only", "운영자만 사용할 수 있습니다.")
    return user
