"""3단계: WBS CRUD·계층 규칙, 시간표 스냅/역방향/겹침/수정, 주말 보충, 주간 회고·자정 분할·공개."""
import asyncio
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.clock import clock
from tests.conftest import create_user, login, make_client, tick

KST = ZoneInfo("Asia/Seoul")


async def _me(client, email="me@test.io"):
    user = await create_user(email)
    await login(client, email)
    return user


# ── WBS ──────────────────────────────────────────────────────────
async def test_wbs_crud_and_hierarchy_rules(client):
    await _me(client)
    parent = (await client.post("/api/wbs", json={"title": "AWS SAA", "startDate": "2026-10-20", "endDate": "2026-11-19", "isPublic": True})).json()
    child = await client.post(
        "/api/wbs", json={"title": "VPC", "startDate": "2026-10-21", "endDate": "2026-10-25", "parentId": parent["id"], "progress": 40, "status": "in_progress"}
    )
    assert child.status_code == 201
    cid = child.json()["id"]
    # 3단계 금지
    assert (await client.post("/api/wbs", json={"title": "손자", "startDate": "2026-10-21", "endDate": "2026-10-22", "parentId": cid})).status_code == 400
    # 자식은 부모 기간 안
    assert (await client.post("/api/wbs", json={"title": "밖", "startDate": "2026-10-10", "endDate": "2026-10-22", "parentId": parent["id"]})).status_code == 400
    # 종료 < 시작 거부, 진행률 범위
    assert (await client.post("/api/wbs", json={"title": "역순", "startDate": "2026-10-22", "endDate": "2026-10-21"})).status_code == 400
    assert (await client.patch(f"/api/wbs/{cid}", json={"progress": 101})).status_code == 400
    # 부모 기간을 줄여 자식이 밖으로 나가면 거부
    assert (await client.patch(f"/api/wbs/{parent['id']}", json={"endDate": "2026-10-22"})).status_code == 400
    ok = await client.patch(f"/api/wbs/{cid}", json={"progress": 100, "status": "done"})
    assert ok.json()["progress"] == 100
    items = (await client.get("/api/wbs")).json()["items"]
    assert [i["title"] for i in items] == ["AWS SAA", "VPC"]
    # 부모 삭제 시 하위도 삭제
    assert (await client.delete(f"/api/wbs/{parent['id']}")).status_code == 204
    assert (await client.get("/api/wbs")).json()["items"] == []


async def test_wbs_public_toggle_and_other_users(client):
    await _me(client)
    t = (await client.post("/api/wbs", json={"title": "공개 과제", "startDate": "2026-10-20", "endDate": "2026-10-30", "isPublic": True})).json()
    me_id = (await client.get("/api/me")).json()["id"]
    async with make_client() as o:
        await create_user("o@test.io")
        await login(o, "o@test.io")
        assert [i["title"] for i in (await o.get(f"/api/members/{me_id}/wbs")).json()["items"]] == ["공개 과제"]
        assert (await o.patch(f"/api/wbs/{t['id']}", json={"title": "해킹"})).status_code == 404
        assert (await o.delete(f"/api/wbs/{t['id']}")).status_code == 404
        await client.patch(f"/api/wbs/{t['id']}", json={"isPublic": False})
        assert (await o.get(f"/api/members/{me_id}/wbs")).json()["items"] == []


# ── 시간표 ───────────────────────────────────────────────────────
def _block(start, end, layer="actual", title="공부", date="2026-10-21"):
    return {"date": date, "layer": layer, "startMin": start, "endMin": end, "title": title}


async def test_timetable_snap_range_overlap(client):
    await _me(client)
    assert (await client.post("/api/timetable-blocks", json=_block(600, 610))).status_code == 400  # 15분 미스냅
    assert (await client.post("/api/timetable-blocks", json=_block(600, 600))).status_code == 400  # 0분
    assert (await client.post("/api/timetable-blocks", json=_block(660, 600))).status_code == 400  # 역방향(서버는 정규화된 값만 받음)
    assert (await client.post("/api/timetable-blocks", json=_block(1425, 1455))).status_code == 400  # 자정 넘김
    assert (await client.post("/api/timetable-blocks", json=_block(1425, 1440))).status_code == 201  # 24:00 종료 허용
    a = (await client.post("/api/timetable-blocks", json=_block(600, 690))).json()
    # 같은 레이어 겹침 거부, 다른 레이어는 허용, 맞닿음 허용
    assert (await client.post("/api/timetable-blocks", json=_block(660, 720))).status_code == 409
    assert (await client.post("/api/timetable-blocks", json=_block(660, 720, layer="plan"))).status_code == 201
    assert (await client.post("/api/timetable-blocks", json=_block(690, 720))).status_code == 201
    # 이동/끝 조절: 겹치면 거부, 아니면 저장
    assert (await client.patch(f"/api/timetable-blocks/{a['id']}", json={"endMin": 705})).status_code == 409
    moved = await client.patch(f"/api/timetable-blocks/{a['id']}", json={"startMin": 540, "endMin": 630, "title": "수정"})
    assert moved.status_code == 200 and moved.json()["title"] == "수정"
    items = (await client.get("/api/timetable-blocks?date=2026-10-21")).json()["items"]
    assert len(items) == 4
    # 일일 기록 payload에도 포함
    assert len((await client.get("/api/daily-entries/2026-10-21")).json()["blocks"]) == 4


async def test_timetable_concurrent_overlap_only_one(client):
    await _me(client)
    async with make_client() as tab2:
        await login(tab2, "me@test.io")
        r1, r2 = await asyncio.gather(
            client.post("/api/timetable-blocks", json=_block(600, 660)),
            tab2.post("/api/timetable-blocks", json=_block(630, 690)),
        )
    assert sorted([r1.status_code, r2.status_code]) == [201, 409]


async def test_timetable_private_unless_entry_public(client):
    await _me(client)
    await client.post("/api/timetable-blocks", json=_block(600, 660, title="비밀 블록"))
    me_id = (await client.get("/api/me")).json()["id"]
    async with make_client() as o:
        await create_user("o@test.io")
        await login(o, "o@test.io")
        assert "비밀 블록" not in str((await o.get(f"/api/members/{me_id}/daily-entries/2026-10-21")).json())
        await client.put("/api/daily-entries/2026-10-21", json={"isPublic": True})
        shown = (await o.get(f"/api/members/{me_id}/daily-entries/2026-10-21")).json()
        assert [b["title"] for b in shown["blocks"]] == ["비밀 블록"]
        b_id = shown["blocks"][0]["id"]
        assert (await o.patch(f"/api/timetable-blocks/{b_id}", json={"title": "x"})).status_code == 404


# ── 주말 보충 ────────────────────────────────────────────────────
async def test_weekend_makeup_rules(client):
    await _me(client)
    g = (await client.post("/api/goals", json={"date": "2026-10-21", "title": "IAM 정책"})).json()
    assert (await client.post(f"/api/goals/{g['id']}/carry", json={"targetDate": "2026-10-23"})).status_code == 400  # 금요일
    ok = await client.post(f"/api/goals/{g['id']}/carry", json={"targetDate": "2026-10-24"})
    assert ok.status_code == 201 and ok.json()["carriedFromId"] == g["id"]
    assert (await client.post(f"/api/goals/{g['id']}/carry", json={"targetDate": "2026-10-24"})).status_code == 409  # 중복
    assert (await client.post(f"/api/goals/{g['id']}/carry", json={"targetDate": "2026-10-25"})).status_code == 201  # 일요일
    # 원본은 그대로 유지
    assert [x["title"] for x in (await client.get("/api/daily-entries/2026-10-21")).json()["goals"]] == ["IAM 정책"]
    await client.patch(f"/api/goals/{g['id']}", json={"done": True})
    assert (await client.post(f"/api/goals/{g['id']}/carry", json={"targetDate": "2026-10-31"})).status_code == 400
    undone = (await client.get("/api/goals?from=2026-10-19&to=2026-10-25&done=false")).json()["items"]
    assert {x["date"] for x in undone} == {"2026-10-24", "2026-10-25"}


# ── 주간 회고 ────────────────────────────────────────────────────
async def test_weekly_review_totals_split_midnight_and_public(client):
    await _me(client)
    # 일요일(10/25) 23:40에 시작한 40분 세션 → 일요일 20분 + 다음 주 월요일 20분
    clock.set(datetime(2026, 10, 25, 23, 40, tzinfo=KST))
    await login(client, "me@test.io")
    sid = (
        await client.post(
            "/api/sessions",
            json={"species": "oak", "targetMinutes": 40, "zoneIndex": 0, "plots": [{"row": 0, "col": 0}, {"row": 0, "col": 1}], "requestId": uuid.uuid4().hex},
        )
    ).json()["id"]
    await tick(client, 2400)
    await client.get(f"/api/sessions/{sid}")
    this_week = (await client.get("/api/weekly-reviews/2026-10-21")).json()
    assert this_week["weekStart"] == "2026-10-19"
    sunday = next(d for d in this_week["totals"]["days"] if d["date"] == "2026-10-25")
    assert sunday["successSeconds"] == 1200 and this_week["totals"]["totalSeconds"] == 1200
    next_week = (await client.get("/api/weekly-reviews/2026-10-26")).json()
    assert next_week["totals"]["totalSeconds"] == 1200

    saved = await client.put("/api/weekly-reviews/2026-10-21", json={"good": "매일 출석", "hard": "VPC", "nextPlan": "모의고사", "isPublic": False})
    assert saved.json()["good"] == "매일 출석"
    me_id = (await client.get("/api/me")).json()["id"]
    async with make_client() as o:
        await create_user("o@test.io")
        await login(o, "o@test.io")
        assert (await o.get(f"/api/members/{me_id}/weekly-reviews/2026-10-21")).json()["public"] is False
        assert all(f["kind"] != "weekly" for f in (await o.get("/api/plaza")).json()["feed"])
        await client.put("/api/weekly-reviews/2026-10-21", json={"isPublic": True})
        shown = (await o.get(f"/api/members/{me_id}/weekly-reviews/2026-10-21")).json()
        assert shown["public"] is True and shown["nextPlan"] == "모의고사"
        assert any(f["kind"] == "weekly" for f in (await o.get("/api/plaza")).json()["feed"])
