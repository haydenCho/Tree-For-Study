"""Auth primitives: Argon2id password hashing and access-JWT encode/decode.

Stage 0 provides the verified building blocks. The register/login/refresh flows that
USE them land in stage 1. Refresh tokens are opaque random strings (handled in the
auth service, stage 1) — only the access token is a JWT.

Hardening rules (docs/10-focus-and-jwt.md):
- Pin the algorithm explicitly; never honor the token header's `alg`.
- Verify signature + exp/nbf + issuer + audience + token_use on every request.
- Access JWT carries NO real name / email / password / study content.
"""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

settings = get_settings()
_password_hash = PasswordHash.recommended()  # Argon2id


class TokenError(Exception):
    """Raised when an access token fails any verification step."""


def hash_password(plain: str) -> str:
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hash.verify(plain, hashed)


def create_access_token(*, user_id: str, session_id: str) -> str:
    """Mint a short-lived access JWT. `sub` is the immutable user id, `sid` the token session."""
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
    """Decode and fully verify an access JWT. Raises TokenError on any failure."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],  # pinned — header alg is ignored
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iat", "nbf", "sub", "aud", "iss"]},
        )
    except jwt.InvalidTokenError as exc:
        raise TokenError(str(exc)) from exc

    if claims.get("token_use") != "access":
        raise TokenError("not an access token")
    return claims
