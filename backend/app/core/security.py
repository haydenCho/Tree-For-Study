"""인증 기본 요소: Argon2id 비밀번호 해시와 액세스 JWT 인코드/디코드.

0단계에서는 검증된 구성 요소만 제공한다. 이를 실제로 사용하는 가입/로그인/갱신
흐름은 docs/10-focus-and-jwt.md에 따라 1단계에서 구현한다. refresh 토큰은
불투명(opaque) 난수 문자열(1단계 인증 서비스에서 처리)이며 JWT는 액세스 토큰만이다.

강화 규칙(docs/10-focus-and-jwt.md):
- 알고리즘을 명시적으로 고정한다. 토큰 헤더의 `alg`를 그대로 신뢰하지 않는다.
- 매 요청마다 서명 + exp/nbf + issuer + audience + token_use를 검증한다.
- 액세스 JWT에는 실명/이메일/비밀번호/공부 기록을 넣지 않는다.
"""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

settings = get_settings()
_password_hash = PasswordHash.recommended()  # Argon2id


class TokenError(Exception):
    """액세스 토큰 검증 단계 중 하나라도 실패하면 발생한다."""


def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


def create_access_token(*, user_id: str, session_id: str) -> str:
    """짧은 수명의 액세스 JWT를 발급한다. `sub`는 불변 사용자 ID, `sid`는 토큰 세션 ID."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "jti": uuid.uuid4().hex,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(seconds=settings.access_ttl_seconds),
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
            options={"require": ["exp", "iat", "nbf", "sub", "aud", "iss"]},
        )
    except jwt.InvalidTokenError as exc:
        raise TokenError(str(exc)) from exc

    if claims.get("token_use") != "access":
        raise TokenError("access 토큰이 아님")
    return claims
