"""인증 라우트(docs/10-focus-and-jwt.md).

- access JWT: 응답 본문으로만 전달. 프론트는 메모리에만 보관하고 Bearer로 보낸다.
- refresh: HttpOnly + Secure(운영) + SameSite=Lax 쿠키, Path=/api/auth. DB에는 해시만.
- CSRF: refresh/logout은 자동 전송되는 쿠키를 쓰므로 이중 제출 토큰(X-CSRF-Token 헤더
  == tfs_csrf 쿠키)과 Origin(없으면 Referer) 검사를 모두 통과해야 한다.
- 로그인/가입도 Origin을 검사해 로그인 CSRF를 막는다.
"""
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.client_ip import client_ip
from app.core.config import get_settings
from app.core.db import get_session
from app.core.errors import ApiError, bad_request, forbidden
from app.core.ratelimit import login_ip_limiter, login_limiter, register_limiter
from app.core.security import hash_password, new_opaque_token, tokens_equal, verify_password
from app.models import User
from app.schemas.user import LoginIn, PasswordChangeIn, RegisterIn, me_out
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

REFRESH_COOKIE = "tfs_refresh"
CSRF_COOKIE = "tfs_csrf"
CSRF_HEADER = "x-csrf-token"


def _origin_of(request: Request) -> str | None:
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("referer")
    if referer:
        parts = urlsplit(referer)
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
    return None


def check_origin(request: Request, *, required: bool) -> None:
    origin = _origin_of(request)
    if origin is None:
        if required:
            raise forbidden("origin_required", "요청 출처를 확인할 수 없습니다.")
        return
    if origin not in settings.app_origin_list:
        raise forbidden("origin_mismatch", "허용되지 않은 출처의 요청입니다.")


def check_csrf(request: Request) -> None:
    check_origin(request, required=True)
    if not tokens_equal(request.headers.get(CSRF_HEADER), request.cookies.get(CSRF_COOKIE)):
        raise forbidden("csrf_failed", "보안 토큰이 일치하지 않습니다. 새로고침 후 다시 시도해 주세요.")


def _set_auth_cookies(response: Response, refresh: str) -> str:
    csrf = new_opaque_token()
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=settings.refresh_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/auth",
    )
    # CSRF 토큰은 JS가 읽어 헤더로 보내야 하므로 HttpOnly가 아니다(인증 수단 아님).
    response.set_cookie(
        CSRF_COOKIE,
        csrf,
        max_age=settings.refresh_ttl_seconds,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return csrf


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth", secure=settings.cookie_secure, httponly=True, samesite="lax")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=settings.cookie_secure, samesite="lax")


def _token_body(user: User, access: str) -> dict:
    return {
        "accessToken": access,
        "tokenType": "Bearer",
        "expiresIn": settings.access_ttl_seconds,
        "user": me_out(user).model_dump(by_alias=True, mode="json"),
    }


@router.post("/register", status_code=201)
async def register(body: RegisterIn, request: Request, db: AsyncSession = Depends(get_session)) -> dict:
    """초대 코드 + 이메일 + 실명 + 비밀번호 → pending 회원. 운영자 승인 전에는 데이터 접근 불가."""
    check_origin(request, required=False)
    if not register_limiter.hit(f"reg:{client_ip(request)}"):
        raise ApiError(429, "rate_limited", "잠시 후 다시 시도해 주세요.")
    user = await auth_service.register(
        db,
        invite_code=body.invite_code,
        email=body.email,
        real_name=body.real_name,
        password=body.password,
        password_confirm=body.password_confirm,
    )
    return {"status": user.status, "message": "가입 신청이 접수되었습니다. 운영자 승인 후 이용할 수 있습니다."}


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response, db: AsyncSession = Depends(get_session)) -> dict:
    """비밀번호 검증 → 액세스 JWT 발급 + refresh 쿠키 설정."""
    check_origin(request, required=False)
    ip_key = f"ip:{client_ip(request)}"
    email_key = f"email:{auth_service.normalize_email(body.email)}"
    if not login_ip_limiter.allowed(ip_key) or not login_limiter.allowed(email_key):
        raise ApiError(429, "rate_limited", "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    try:
        user = await auth_service.authenticate(db, email=body.email, password=body.password)
    except ApiError:
        # 실패한 시도만 센다.
        login_ip_limiter.record(ip_key)
        login_limiter.record(email_key)
        raise
    access, refresh = await auth_service.issue_tokens(db, user)
    await db.commit()
    _set_auth_cookies(response, refresh)
    return _token_body(user, access)


@router.post("/refresh")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_session)) -> dict:
    """refresh 토큰 회전(CSRF + Origin 검사) → 새 액세스 JWT."""
    check_csrf(request)
    try:
        user, access, new_refresh = await auth_service.rotate_refresh(db, request.cookies.get(REFRESH_COOKIE))
    except ApiError as exc:
        if exc.status_code == 401:
            # 쿠키를 지우는 응답을 직접 만들어 반환한다(예외 응답에는 쿠키를 붙일 수 없음).
            res = JSONResponse(status_code=401, content={"detail": exc.detail})
            _clear_auth_cookies(res)
            return res
        raise
    _set_auth_cookies(response, new_refresh)
    return _token_body(user, access)


@router.post("/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_session)) -> dict:
    """현재 refresh 패밀리 폐기. 같은 패밀리의 access JWT도 즉시 거부된다."""
    check_csrf(request)
    await auth_service.logout(db, request.cookies.get(REFRESH_COOKIE))
    _clear_auth_cookies(response)
    return {"status": "logged_out"}


@router.post("/password")
async def change_password(
    body: PasswordChangeIn,
    request: Request,
    response: Response,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """현재 비밀번호 확인 후 변경하고 모든 토큰 세션을 폐기한 뒤 새 세션을 발급한다."""
    check_origin(request, required=False)
    if not verify_password(body.current_password, user.password_hash):
        raise bad_request("wrong_password", "현재 비밀번호가 올바르지 않습니다.")
    auth_service.validate_password(body.new_password)
    if body.new_password != body.new_password_confirm:
        raise bad_request("password_mismatch", "새 비밀번호 확인이 일치하지 않습니다.")
    user.password_hash = hash_password(body.new_password)
    await auth_service.revoke_all_for_user(db, user.id)
    access, refresh_token = await auth_service.issue_tokens(db, user)
    await db.commit()
    _set_auth_cookies(response, refresh_token)
    return _token_body(user, access)

