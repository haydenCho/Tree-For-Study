"""2단계: 도서관 시작 IP·프록시, 공동 숲 무작위 배치, 출석, 광장 공개 범위, 공개 WBS."""
import asyncio
import uuid
from datetime import date

from sqlalchemy import func, select

from app.core.clock import clock, utcnow
from app.core.db import SessionLocal
from app.models import CommunityPlacement, WbsTask
from app.services import community
from tests.conftest import create_user, login, make_client, tick

LIB_IP = "203.0.113.9"


def _cells(n, start=0):
    return [{"row": (start + i) // 6, "col": (start + i) % 6} for i in range(n)]


async def _start(c, minutes=20, start=0):
    return await c.post(
        "/api/sessions",
        json={"species": "oak", "targetMinutes": minutes, "zoneIndex": 0, "plots": _cells(minutes // 20, start), "requestId": uuid.uuid4().hex},
    )


async def _operator(client, email="op@test.io"):
    await create_user(email, role="operator")
    await login(client, email)


async def _register_library(client, network="203.0.113.0/24"):
    await _operator(client)
    res = await client.post("/api/admin/library-networks", json={"network": network, "label": "도서관"})
    assert res.status_code == 201, res.text
    client.headers.pop("authorization")


async def _placements():
    async with SessionLocal() as s:
        return (await s.execute(select(func.count()).select_from(CommunityPlacement))).scalar_one()


# ── 도서관 보너스 ─────────────────────────────────────────────────
async def test_library_start_ip_decides_decoration(client):
    await _register_library(client)
    await create_user("lib@test.io")
    async with make_client(LIB_IP) as at_library:
        await login(at_library, "lib@test.io")
        body = (await _start(at_library)).json()
        assert body["libraryAtStart"] is True
        sid = body["id"]
    # 다른 네트워크(카페)에서 조회/완료해도 시작 판정 유지
    async with make_client("198.51.100.20") as elsewhere:
        await login(elsewhere, "lib@test.io")
        await tick(elsewhere, 1200)
        done = (await elsewhere.get(f"/api/sessions/{sid}")).json()
        assert done["status"] == "completed" and done["libraryAtStart"] is True
        dash = (await elsewhere.get("/api/dashboard")).json()
        assert dash["zones"][0]["cells"][0]["state"] == "library"
        # 반대: 외부에서 시작하면 도서관에서 끝나도 장식 없음
        assert (await _start(elsewhere, start=1)).json()["libraryAtStart"] is False


async def test_forged_forwarded_header_rejected(client):
    await _register_library(client)
    await create_user("f@test.io")
    # 신뢰하지 않는 직접 연결이 X-Forwarded-For로 도서관 IP를 주장
    async with make_client("198.51.100.20", {"x-forwarded-for": LIB_IP}) as forged:
        await login(forged, "f@test.io")
        assert (await forged.get("/api/library-status")).json()["recognized"] is False
        assert (await _start(forged)).json()["libraryAtStart"] is False


async def test_trusted_proxy_header_used_rightmost(client):
    await _register_library(client)
    await create_user("p@test.io")
    # 신뢰 프록시(10.0.0.2)가 실제 주소를 덧붙임 → 인정
    async with make_client("10.0.0.2", {"x-forwarded-for": LIB_IP}) as via_caddy:
        await login(via_caddy, "p@test.io")
        assert (await via_caddy.get("/api/library-status")).json()["recognized"] is True
    # 클라이언트가 왼쪽에 위조 값을 넣어도 Caddy가 붙인 오른쪽 실제 주소 기준
    async with make_client("10.0.0.2", {"x-forwarded-for": f"{LIB_IP}, 198.51.100.7"}) as spoof:
        await login(spoof, "p@test.io")
        assert (await spoof.get("/api/library-status")).json()["recognized"] is False


async def test_network_admin_rules(client):
    await _operator(client)
    assert (await client.post("/api/admin/library-networks", json={"network": "10.0.0.0/8"})).status_code == 400
    assert (await client.post("/api/admin/library-networks", json={"network": "nope"})).status_code == 400
    assert (await client.post("/api/admin/library-networks", json={"network": "2001:db8::1"})).status_code == 201
    assert (await client.post("/api/admin/library-networks", json={"network": "2001:db8::1"})).status_code == 409
    diag = await client.get("/api/admin/network-diagnostic")
    assert diag.json()["observedIp"] == LIB_IP and diag.headers["cache-control"] == "no-store"
    assert diag.json()["ruleVersion"] == 1
    async with make_client() as m:
        await create_user("m@test.io")
        await login(m, "m@test.io")
        assert (await m.get("/api/admin/network-diagnostic")).status_code == 403
        assert "observedIp" not in (await m.get("/api/library-status")).json()


# ── 공동 숲 ───────────────────────────────────────────────────────
async def test_community_only_successful_trees_and_stable(client):
    await create_user("c@test.io")
    await login(client, "c@test.io")
    sid = (await _start(client, 60)).json()["id"]
    await tick(client, 3600)
    await client.get(f"/api/sessions/{sid}")
    sid2 = (await _start(client, 20, start=3)).json()["id"]
    await client.post(f"/api/sessions/{sid2}/abandon")  # 시든 나무는 공동 숲 제외
    assert await _placements() == 3
    p1 = (await client.get("/api/plaza")).json()["zones"]
    p2 = (await client.get("/api/plaza")).json()["zones"]
    assert p1 == p2  # 새로고침마다 재추첨하지 않음
    cells = {(c["row"], c["col"]) for c in p1[0]["cells"]}
    assert len(cells) == 3


def test_community_fills_zone_then_opens_next_without_overlap():
    cells = community.choose_cells(set(), 40)
    assert len(set(cells)) == 40
    assert sum(1 for z, _, _ in cells if z == 0) == 36
    assert sum(1 for z, _, _ in cells if z == 1) == 4
    # 이미 찬 칸은 피한다
    more = community.choose_cells(set(cells), 5)
    assert not set(more) & set(cells) and {z for z, _, _ in more} == {1}


async def test_concurrent_completions_unique_cells(client):
    users = []
    for i in range(4):
        await create_user(f"u{i}@test.io")
    clients = [make_client() for _ in range(4)]
    for i, c in enumerate(clients):
        await login(c, f"u{i}@test.io")
        users.append((await _start(c, 60)).json()["id"])
    clock.advance(3600)
    from app.services.focus import settle_due

    async def worker():
        async with SessionLocal() as s:
            return await settle_due(s)

    await asyncio.gather(worker(), worker(), worker())
    async with SessionLocal() as s:
        rows = (await s.execute(select(CommunityPlacement.zone_index, CommunityPlacement.row, CommunityPlacement.col))).all()
    assert len(rows) == 12 and len(set(rows)) == 12
    for c in clients:
        await c.aclose()


# ── 출석 ─────────────────────────────────────────────────────────
async def test_attendance_check_in_and_absent_next_day(client):
    # 2026-10-21(수) 대면일
    await create_user("a@test.io")
    await login(client, "a@test.io")
    s = (await client.get("/api/attendance/me?month=2026-10")).json()
    assert s["summary"]["todayStatus"] == "not_checked"
    assert (await client.post("/api/attendance/check-in")).json()["todayStatus"] == "present"
    # 같은 날 늦게 다시 체크인해도 출석(지각 없음)
    await tick(client, 13 * 3600)
    assert (await client.post("/api/attendance/check-in")).json()["todayStatus"] == "present"
    # 다음 날(목) 체크인하지 않으면 그다음 날 00:00부터 결석 (현재 21일 23:00 → 23일 00:00)
    await tick(client, 25 * 3600)
    days = {d["date"]: d for d in (await client.get("/api/attendance/me?month=2026-10")).json()["days"]}
    assert days["2026-10-21"]["status"] == "present"
    assert days["2026-10-22"]["status"] == "absent"
    assert days["2026-10-20"]["status"] == "absent"  # 화요일(첫날)도 미체크인 → 결석
    assert days["2026-10-19"]["status"] == "none"  # 기간 밖
    assert days["2026-10-24"]["kind"] == "self"  # 토요일 자율
    statuses = {d["status"] for d in days.values()}
    assert "late" not in statuses


async def test_holiday_excluded_and_correction_requires_reason(client):
    await _operator(client)
    member = await create_user("h@test.io")
    assert (await client.put("/api/admin/study-dates/2026-10-21", json={"kind": "holiday", "note": "휴관"})).status_code == 200
    async with make_client() as m:
        await login(m, "h@test.io")
        assert (await m.post("/api/attendance/check-in")).status_code == 400
        assert (await m.get("/api/attendance/me")).json()["summary"]["todayStatus"] == "holiday"
    bad = await client.put(f"/api/admin/attendance/{member.id}/2026-10-20", json={"status": "present", "reason": " "})
    assert bad.status_code == 400
    ok = await client.put(f"/api/admin/attendance/{member.id}/2026-10-20", json={"status": "present", "reason": "출석부 확인"})
    assert ok.status_code == 200
    roster = (await client.get("/api/admin/attendance?day=2026-10-20")).json()
    assert {i["status"] for i in roster["items"] if i["userId"] == str(member.id)} == {"present"}


# ── 광장 ─────────────────────────────────────────────────────────
async def test_plaza_ten_members_public_fields_only(client):
    for i in range(10):
        await create_user(f"m{i}@test.io", display_name=f"멤버{i}")
    await create_user("pending@test.io", status="pending")
    await login(client, "m0@test.io")
    await client.put("/api/daily-entries/2026-10-21", json={"planText": "공개 계획", "isPublic": True})
    await client.put("/api/daily-entries/2026-10-20", json={"planText": "비밀 계획", "isPublic": False})
    plaza = (await client.get("/api/plaza")).json()
    assert len(plaza["members"]) == 10
    raw = str(plaza)
    assert "@test.io" not in raw and "실명" not in raw and "비밀 계획" not in raw
    assert [f["excerpt"] for f in plaza["feed"]] == ["공개 계획"]
    # 비공개로 바꾸면 피드에서 즉시 사라짐
    await client.put("/api/daily-entries/2026-10-21", json={"isPublic": False})
    assert (await client.get("/api/plaza")).json()["feed"] == []


async def test_plaza_presence_states(client):
    await create_user("s@test.io")
    await login(client, "s@test.io")
    sid = (await _start(client)).json()["id"]
    me = next(m for m in (await client.get("/api/plaza")).json()["members"])
    assert me["state"] == "focusing"
    await client.post(f"/api/sessions/{sid}/pause")
    assert (await client.get("/api/plaza")).json()["members"][0]["state"] == "paused"
    await client.post(f"/api/sessions/{sid}/resume")
    await tick(client, 1200)
    await client.post(f"/api/sessions/{sid}/rest", json={"action": "start"})
    assert (await client.get("/api/plaza")).json()["members"][0]["state"] == "resting"


# ── 공개 WBS ─────────────────────────────────────────────────────
async def test_public_wbs_hides_private_parent_name(client):
    owner = await create_user("w@test.io")
    now = utcnow()
    async with SessionLocal() as s:
        parent = WbsTask(user_id=owner.id, title="비밀 상위", start_date=date(2026, 10, 20), end_date=date(2026, 11, 19), is_public=False, created_at=now, updated_at=now)
        s.add(parent)
        await s.flush()
        s.add(WbsTask(user_id=owner.id, parent_id=parent.id, title="VPC 문제", start_date=date(2026, 10, 21), end_date=date(2026, 10, 23), is_public=True, created_at=now, updated_at=now))
        pub = WbsTask(user_id=owner.id, title="AWS SAA", start_date=date(2026, 10, 20), end_date=date(2026, 11, 19), is_public=True, created_at=now, updated_at=now)
        s.add(pub)
        await s.flush()
        s.add(WbsTask(user_id=owner.id, parent_id=pub.id, title="비밀 하위", start_date=date(2026, 10, 21), end_date=date(2026, 10, 22), is_public=False, created_at=now, updated_at=now))
        await s.commit()
    await create_user("v@test.io")
    await login(client, "v@test.io")
    body = (await client.get(f"/api/members/{owner.id}/wbs")).json()
    titles = {i["title"]: i for i in body["items"]}
    assert set(titles) == {"VPC 문제", "AWS SAA"}
    assert titles["VPC 문제"]["parentId"] is None
    assert "비밀" not in str(body)
    # 비활성(pending) 회원의 WBS는 조회되지 않음
    p = await create_user("pp@test.io", status="pending")
    assert (await client.get(f"/api/members/{p.id}/wbs")).json()["items"] == []


async def test_member_calendar_marks_only_public_dates(client):
    owner = await create_user("o@test.io")
    async with make_client() as o:
        await login(o, "o@test.io")
        await o.put("/api/daily-entries/2026-10-21", json={"planText": "공개", "isPublic": True})
        await o.put("/api/daily-entries/2026-10-22", json={"planText": "비밀", "isPublic": False})
        await o.post("/api/goals", json={"date": "2026-10-22", "title": "비밀 목표"})
        mine = {d["date"]: d for d in (await o.get("/api/calendar?month=2026-10")).json()["days"]}
        assert mine["2026-10-22"]["goalCount"] == 1 and mine["2026-10-20"]["kind"] == "in_person"
    await create_user("v@test.io")
    await login(client, "v@test.io")
    body = (await client.get(f"/api/calendar?month=2026-10&member={owner.id}")).json()
    days = {d["date"]: d for d in body["days"]}
    assert days["2026-10-21"]["hasPublicEntry"] is True
    assert days["2026-10-22"]["hasPublicEntry"] is False
    assert "goalCount" not in days["2026-10-22"]
