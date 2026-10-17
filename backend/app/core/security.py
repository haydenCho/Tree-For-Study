"""인증 기본 요소: Argon2id 비밀번호 해시, 액세스 JWT, 불투명 토큰 해시.

강화 규칙(docs/10-focus-and-jwt.md):
- 알고리즘을 명시적으로 고정한다. 토큰 헤더의 `alg`를 그대로 신뢰하지 않는다.
- 매 요청마다 서명 + exp/nbf + issuer + audience + token_use를 검증한다.
  exp/nbf는 주입 가능한 서버 시계(app.core.clock)로 직접 비교한다.
- 액세스 JWT에는 실명/이메일/비밀번호/공부 기록을 넣지 않는다.
- refresh 토큰과 초대 코드는 불투명 난수이며 DB에는 SHA-256 해시만 저장한다.
"""
import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta

import jwt
from pwdlib import PasswordHash

from app.core.clock import utcnow
from app.core.config import get_settings

settings = get_settings()
_password_hash = PasswordHash.recommended()  # Argon2id

# 존재하지 않는 계정 로그인에도 비슷한 시간을 쓰도록 하는 더미 해시
_DUMMY_HASH = _password_hash.hash("dummy-password-for-timing")

# 시계 오차 허용(초)
_LEEWAY = 5


class TokenError(Exception):
    """액세스 토큰 검증 단계 중 하나라도 실패하면 발생한다."""


def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        # 타이밍 차이를 줄이기 위해 더미 검증을 수행한다.
        _password_hash.verify(plain, _DUMMY_HASH)
        return False
    try:
        return _password_hash.verify(plain, hashed)
    except Exception:
        return False


def new_opaque_token() -> str:
    """refresh 토큰·초대 코드·CSRF 토큰용 256비트 난수."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_equal(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return hmac.compare_digest(a, b)


def create_access_token(*, user_id: str, session_id: str) -> str:
    """짧은 수명의 액세스 JWT를 발급한다. `sub`는 불변 사용자 ID, `sid`는 토큰 세션 ID."""
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.access_ttl_seconds)).timestamp()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "token_use": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """액세스 JWT를 디코드하고 완전히 검증한다. 실패 시 TokenError를 발생시킨다."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],  # 고정 — 헤더의 alg는 무시
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            # exp/nbf는 아래에서 주입 시계로 직접 검사한다.
            options={
                "require": ["exp", "iat", "nbf", "sub", "aud", "iss", "sid", "jti"],
                "verify_exp": False,
                "verify_nbf": False,
                "verify_iat": False,
            },
        )
    except jwt.InvalidTokenError as exc:
        raise TokenError(str(exc)) from exc

    now = utcnow().timestamp()
    try:
        exp = float(claims["exp"])
        nbf = float(claims["nbf"])
    except (TypeError, ValueError) as exc:
        raise TokenError("잘못된 시간 claim") from exc
    if now >= exp + _LEEWAY:
        raise TokenError("만료된 토큰")
    if now + _LEEWAY < nbf:
        raise TokenError("아직 유효하지 않은 토큰")
    if claims.get("token_use") != "access":
        raise TokenError("access 토큰이 아님")
    return claims
