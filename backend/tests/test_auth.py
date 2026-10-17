"""가입·승인·JWT·refresh 회전·CSRF·로그아웃 검증(docs/10-focus-and-jwt.md)."""
import asyncio
import uuid
from datetime import timedelta

import jwt

from app.core.clock import clock
from app.core.config import get_settings
from app.core.security import create_access_token
from tests.conftest import ORIGIN, PASSWORD, create_user, csrf_headers, login, make_client

settings = get_settings()


async def _invite(client) -> str:
    op = await create_user("op@test.io", role="operator")
    await login(client, "op@test.io")
    res = await client.post("/api/admin/invites", json={"maxUses": 20})
    assert res.status_code == 201
    client.headers.pop("authorization")
    return res.json()["code"]


async def test_register_pending_then_approve_gives_access(client):
    code = await _invite(client)
    res = await client.post(
        "/api/auth/register",
        json={"inviteCode": code, "email": " New@Test.io ", "realName": "김실명", "password": PASSWORD, "passwordConfirm": PASSWORD},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "pending"

    async with make_client() as member:
        await login(member, "new@test.io")
        me = await member.get("/api/me")
        assert me.status_code == 200 and me.json()["status"] == "pending"
        # pending은 스터디 데이터 접근 불가
        assert (await member.get("/api/dashboard")).status_code == 403

        await login(client, "op@test.io")
        pending = (await client.get("/api/admin/membership-requests")).json()["items"]
        assert [p["email"] for p in pending] == ["new@test.io"]
        assert (await client.post(f"/api/admin/membership-requests/{pending[0]['id']}/approve")).status_code == 200

        assert (await member.get("/api/dashboard")).status_code == 200


async def test_register_rejects_bad_invite_and_duplicate_email(client):
    code = await _invite(client)
    base = {"email": "a@test.io", "realName": "가", "password": PASSWORD, "passwordConfirm": PASSWORD}
    assert (await client.post("/api/auth/register", json={**base, "inviteCode": "nope"})).status_code == 400
    assert (await client.post("/api/auth/register", json={**base, "inviteCode": code})).status_code == 201
    dup = await client.post("/api/auth/register", json={**base, "email": "A@TEST.IO", "inviteCode": code})
    assert dup.status_code == 409
    short = await client.post("/api/auth/register", json={**base, "email": "b@test.io", "inviteCode": code, "password": "short", "passwordConfirm": "short"})
    assert short.status_code == 400


async def test_expired_invite_rejected(client):
    code = await _invite(client)
    clock.advance(8 * 86400)
    res = await client.post(
        "/api/auth/register",
        json={"inviteCode": code, "email": "late@test.io", "realName": "늦음", "password": PASSWORD, "passwordConfirm": PASSWORD},
    )
    assert res.status_code == 400


async def test_wrong_password_and_tokens_rejected(client):
    await create_user("m@test.io")
    bad = await client.post("/api/auth/login", json={"email": "m@test.io", "password": "wrong-password-123"})
    assert bad.status_code == 401
    token = await login(client, "m@test.io")
    claims = jwt.decode(token, options={"verify_signature": False})
    assert "email" not in claims and "real_name" not in claims

    async def call(tok):
        return (await client.get("/api/me", headers={"authorization": f"Bearer {tok}"})).status_code

    assert await call(token) == 200
    # 서명 오류
    assert await call(jwt.encode(claims, "other-secret-" + "y" * 40, algorithm="HS256")) == 401
    # alg none
    assert await call(jwt.encode(claims, None, algorithm="none")) == 401
    # iss / aud / token_use 위조
    secret = settings.jwt_secret
    assert await call(jwt.encode({**claims, "iss": "evil"}, secret, algorithm="HS256")) == 401
    assert await call(jwt.encode({**claims, "aud": "evil"}, secret, algorithm="HS256")) == 401
    assert await call(jwt.encode({**claims, "token_use": "refresh"}, secret, algorithm="HS256")) == 401
    # 만료
    clock.advance(settings.access_ttl_seconds + 60)
    assert await call(token) == 401


async def test_refresh_rotation_and_reuse_detection(client):
    await create_user("r@test.io")
    await login(client, "r@test.io")
    old_refresh = client.cookies.get("tfs_refresh")
    res = await client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert res.status_code == 200
    new_refresh = client.cookies.get("tfs_refresh")
    assert new_refresh and new_refresh != old_refresh

    # 회전 직후 옛 토큰 재사용(유예 안) → 409, 패밀리는 유지
    async with make_client() as attacker:
        attacker.cookies.set("tfs_refresh", old_refresh, path="/api/auth")
        attacker.cookies.set("tfs_csrf", "x")
        res = await attacker.post("/api/auth/refresh", headers={"x-csrf-token": "x", "origin": ORIGIN})
        assert res.status_code == 409
        # 유예 후 재사용 → 패밀리 전체 폐기
        clock.advance(settings.refresh_race_grace_seconds + 1)
        res = await attacker.post("/api/auth/refresh", headers={"x-csrf-token": "x", "origin": ORIGIN})
        assert res.status_code == 401
    # 정상 사용자 쪽 최신 refresh도 폐기됨
    res = await client.post("/api/auth/refresh", headers=csrf_headers(client))
    assert res.status_code == 401


async def test_concurrent_refresh_only_one_rotates(client):
    await create_user("c@test.io")
    await login(client, "c@test.io")
    refresh = client.cookies.get("tfs_refresh")
    csrf = client.cookies.get("tfs_csrf")

    async def attempt():
        async with make_client() as c:
            c.cookies.set("tfs_refresh", refresh, path="/api/auth")
            c.cookies.set("tfs_csrf", csrf)
            return (await c.post("/api/auth/refresh", headers={"x-csrf-token": csrf, "origin": ORIGIN})).status_code

    codes = sorted(await asyncio.gather(attempt(), attempt(), attempt()))
    assert codes.count(200) == 1
    assert all(code in (200, 409) for code in codes)


async def test_refresh_requires_csrf_and_origin(client):
    await create_user("x@test.io")
    await login(client, "x@test.io")
    assert (await client.post("/api/auth/refresh", headers={"origin": ORIGIN})).status_code == 403
    bad_origin = {**csrf_headers(client), "origin": "http://evil.example"}
    assert (await client.post("/api/auth/refresh", headers=bad_origin)).status_code == 403
    assert (await client.post("/api/auth/refresh", headers=csrf_headers(client))).status_code == 200


async def test_logout_revokes_existing_access_jwt(client):
    await create_user("l@test.io")
    token = await login(client, "l@test.io")
    assert (await client.post("/api/auth/logout", headers=csrf_headers(client))).status_code == 200
    res = await client.get("/api/me", headers={"authorization": f"Bearer {token}"})
    assert res.status_code == 401


async def test_password_change_revokes_other_sessions(client):
    await create_user("p@test.io")
    old = await login(client, "p@test.io")
    async with make_client() as other:
        other_token = await login(other, "p@test.io")
        res = await client.post(
            "/api/auth/password",
            json={"currentPassword": PASSWORD, "newPassword": "brand-new-password-1", "newPasswordConfirm": "brand-new-password-1"},
        )
        assert res.status_code == 200
        assert (await other.get("/api/me", headers={"authorization": f"Bearer {other_token}"})).status_code == 401
    assert (await client.get("/api/me", headers={"authorization": f"Bearer {old}"})).status_code == 401
    new_token = res.json()["accessToken"]
    assert (await client.get("/api/me", headers={"authorization": f"Bearer {new_token}"})).status_code == 200


async def test_capacity_eleventh_approval_rejected(client):
    await create_user("op@test.io", role="operator")
    # 운영자도 활성 멤버 정원에 포함된다: 운영자 1 + 멤버 8 = 9명
    for i in range(8):
        await create_user(f"m{i}@test.io")
    pending = [await create_user(f"p{i}@test.io", status="pending") for i in range(2)]
    await login(client, "op@test.io")
    # 동시에 두 명 승인 → 정원 10명이므로 하나만 성공
    r1, r2 = await asyncio.gather(
        client.post(f"/api/admin/membership-requests/{pending[0].id}/approve"),
        client.post(f"/api/admin/membership-requests/{pending[1].id}/approve"),
    )
    assert sorted([r1.status_code, r2.status_code]) == [200, 409]


async def test_non_operator_cannot_use_admin(client):
    await create_user("m@test.io")
    await login(client, "m@test.io")
    assert (await client.get("/api/admin/membership-requests")).status_code == 403


async def test_disabled_user_access_revoked(client):
    await create_user("op@test.io", role="operator")
    target = await create_user("t@test.io")
    async with make_client() as t:
        token = await login(t, "t@test.io")
        await login(client, "op@test.io")
        assert (await client.post(f"/api/admin/members/{target.id}/disable")).status_code == 200
        assert (await t.get("/api/me", headers={"authorization": f"Bearer {token}"})).status_code == 401


async def test_unknown_sid_rejected(client):
    user = await create_user("s@test.io")
    forged = create_access_token(user_id=str(user.id), session_id=str(uuid.uuid4()))
    assert (await client.get("/api/me", headers={"authorization": f"Bearer {forged}"})).status_code == 401


async def test_login_rate_limited(client):
    await create_user("rl@test.io")
    codes = [
        (await client.post("/api/auth/login", json={"email": "rl@test.io", "password": "wrong-password-xx"})).status_code
        for _ in range(11)
    ]
    assert codes[-1] == 429
    clock.advance(timedelta(minutes=6).total_seconds())
    assert (await client.post("/api/auth/login", json={"email": "rl@test.io", "password": PASSWORD})).status_code == 200
