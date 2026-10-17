"""일일 기록·목표·공개 필터·프로필 검증."""
from tests.conftest import create_user, login, make_client


async def test_entry_default_private_and_owner_only(client):
    other = await create_user("o@test.io")
    await create_user("me@test.io")
    await login(client, "me@test.io")
    empty = (await client.get("/api/daily-entries/2026-10-21")).json()
    assert empty["isPublic"] is False and empty["planText"] == ""
    res = await client.put("/api/daily-entries/2026-10-21", json={"planText": "VPC", "recordText": "비밀 메모"})
    assert res.status_code == 200 and res.json()["isPublic"] is False

    me_id = (await client.get("/api/me")).json()["id"]
    async with make_client() as o:
        await login(o, "o@test.io")
        hidden = (await o.get(f"/api/members/{me_id}/daily-entries/2026-10-21")).json()
        assert hidden == {"date": "2026-10-21", "public": False}
        # 존재하지 않는 날짜도 같은 응답(존재 여부 추정 불가)
        assert (await o.get(f"/api/members/{me_id}/daily-entries/2026-10-22")).json()["public"] is False

        await client.put("/api/daily-entries/2026-10-21", json={"isPublic": True})
        shown = (await o.get(f"/api/members/{me_id}/daily-entries/2026-10-21")).json()
        assert shown["public"] is True and shown["planText"] == "VPC"
        assert "email" not in str(shown) and "실명" not in str(shown)

        # 다시 비공개로 바꾸면 즉시 사라진다
        await client.put("/api/daily-entries/2026-10-21", json={"isPublic": False})
        assert (await o.get(f"/api/members/{me_id}/daily-entries/2026-10-21")).json()["public"] is False
    assert other is not None


async def test_goals_crud_and_ownership(client):
    await create_user("me@test.io")
    await login(client, "me@test.io")
    g = (await client.post("/api/goals", json={"date": "2026-10-21", "title": "S3 정리"})).json()
    assert (await client.patch(f"/api/goals/{g['id']}", json={"done": True})).json()["done"] is True
    entry = (await client.get("/api/daily-entries/2026-10-21")).json()
    assert [x["title"] for x in entry["goals"]] == ["S3 정리"]
    async with make_client() as o:
        await create_user("o@test.io")
        await login(o, "o@test.io")
        assert (await o.patch(f"/api/goals/{g['id']}", json={"done": False})).status_code == 404
        assert (await o.delete(f"/api/goals/{g['id']}")).status_code == 404
    assert (await client.delete(f"/api/goals/{g['id']}")).status_code == 204


async def test_invalid_date_rejected(client):
    await create_user("me@test.io")
    await login(client, "me@test.io")
    assert (await client.get("/api/daily-entries/2026-13-40")).status_code == 400


async def test_profile_update_and_emoji_allowlist(client):
    await create_user("me@test.io")
    await login(client, "me@test.io")
    ok = await client.patch("/api/me/profile", json={"displayName": "숲지기", "bio": "SAA 합격!", "avatarEmoji": "👩🏽‍💻"})
    assert ok.status_code == 200 and ok.json()["avatarEmoji"] == "👩🏽‍💻"
    assert (await client.patch("/api/me/profile", json={"avatarEmoji": "abc"})).status_code == 400
    assert (await client.patch("/api/me/profile", json={"avatarEmoji": "😀😀"})).status_code == 400
    assert (await client.patch("/api/me/profile", json={"displayName": "a"})).status_code == 400
    assert (await client.patch("/api/me/profile", json={"bio": "x" * 161})).status_code == 400
    assert (await client.patch("/api/me/profile", json={"defaultFocusMinutes": 15})).status_code == 400
    assert (await client.patch("/api/me/profile", json={"defaultFocusMinutes": 50, "defaultRestMinutes": 5})).status_code == 200


async def test_pending_member_blocked_from_records(client):
    await create_user("p@test.io", status="pending")
    await login(client, "p@test.io")
    assert (await client.get("/api/daily-entries/2026-10-21")).status_code == 403
    assert (await client.patch("/api/me/profile", json={"bio": "x"})).status_code == 403
