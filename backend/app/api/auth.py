"""Auth route skeleton (stage 0).

Endpoints are declared so the API surface and contract are visible, but the real
flows (Argon2 verification, pending/approve gate, refresh rotation, CSRF/Origin
checks) are implemented in stage 1 per docs/10-focus-and-jwt.md. Until then each
returns 501 so nothing silently "works" with fake auth.
"""
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/auth", tags=["auth"])

_NOT_YET = "Implemented in stage 1 (see docs/10-focus-and-jwt.md)."


def _stage1():
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail=_NOT_YET)


@router.post("/register")
async def register() -> dict:
    """Invite code + email + real name + password -> pending membership."""
    _stage1()


@router.post("/login")
async def login() -> dict:
    """Verify password -> issue access JWT + set refresh cookie."""
    _stage1()


@router.post("/refresh")
async def refresh() -> dict:
    """Rotate refresh token (CSRF + Origin checked) -> new access JWT."""
    _stage1()


@router.post("/logout")
async def logout() -> dict:
    """Revoke the current token session / refresh family."""
    _stage1()


@router.post("/password")
async def change_password() -> dict:
    """Change password after verifying the current one; revoke other sessions."""
    _stage1()
