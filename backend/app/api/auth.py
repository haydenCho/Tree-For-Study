"""인증 라우트 뼈대 (0단계).

API 표면과 계약을 드러내기 위해 엔드포인트만 선언하고, 실제 흐름(Argon2 검증,
pending/승인 게이트, refresh 회전, CSRF/Origin 검사)은 docs/10-focus-and-jwt.md에
따라 1단계에서 구현한다. 그때까지는 가짜 인증이 '동작하는 것처럼' 보이지 않도록
각 엔드포인트가 501을 반환한다.
"""
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/auth", tags=["auth"])

_NOT_YET = "1단계에서 구현 예정 (docs/10-focus-and-jwt.md 참고)."


def _stage1():
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail=_NOT_YET)


@router.post("/register")
async def register() -> dict:
    """초대 코드 + 이메일 + 실명 + 비밀번호 -> pending 멤버십."""
    _stage1()


@router.post("/login")
async def login() -> dict:
    """비밀번호 검증 -> 액세스 JWT 발급 + refresh 쿠키 설정."""
    _stage1()


@router.post("/refresh")
async def refresh() -> dict:
    """refresh 토큰 회전(CSRF + Origin 검사) -> 새 액세스 JWT."""
    _stage1()


@router.post("/logout")
async def logout() -> dict:
    """현재 토큰 세션 / refresh 패밀리 폐기."""
    _stage1()


@router.post("/password")
async def change_password() -> dict:
    """현재 비밀번호 확인 후 변경하고 다른 세션을 폐기."""
    _stage1()
