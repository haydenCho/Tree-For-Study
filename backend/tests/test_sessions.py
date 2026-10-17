"""집중 세션: 보상·예약·pause·포기·경합·중복 완료 검증(주입 시계 사용)."""
import asyncio
import uuid

from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models import FocusSession, Tree
from app.services.focus import settle_due
from tests.conftest import create_user, login, make_client, tick


def _cells(n, start=0):
    return [{"row": (start + i) // 6, "col": (start + i) % 6} for i in range(n)]


async def _start(client, minutes=60, cells=None, species="oak", zone=0, request_id=None):
    n = minutes // 20
    return await client.post(
        "/api/sessions",
        json={
            "species": species,
            "targetMinutes": minutes,
            "zoneIndex": zone,
            "plots": cells if cells is not None else _cells(n),
            "requestId": request_id or uuid.uuid4().hex,
        },
    )


async def _trees(state=None):
    async with SessionLocal() as s:
        q = select(func.count()).select_from(Tree)
        if state:
            q = q.where(Tree.state == state)
        return (await s.execute(q)).scalar_one()


async def _member(client, email="u@test.io"):
    await create_user(email)
    await login(client, email)


async def test_start_requires_exact_distinct_cells(client):
    await _member(client)
    assert (await _start(client, 60, _cells(2))).status_code == 400
    dup = [{"row": 0, "col": 0}] * 3
    assert (await _start(client, 60, dup)).status_code == 400
    assert (await _start(client, 60, [{"row": 0, "col": 6}, {"row": 0, "col": 1}, {"row": 0, "col": 2}])).status_code == 400
    assert (await _start(client, 19, [])).status_code == 400
    assert (await _start(client, 181, _cells(9))).status_code == 400
    res = await _start(client, 60)
    assert res.status_code == 201
    body = res.json()
    assert body["treeCount"] == 3 and body["size"] == "large" and body["status"] == "focusing"
    assert body["libraryAtStart"] is False


async def test_full_success_confirms_trees_atomically(client):
    await _member(client)
    sid = (await _start(client, 40)).json()["id"]
    await tick(client, 39 * 60)
    assert (await client.get(f"/api/sessions/{sid}")).json()["status"] == "focusing"
    assert await _trees() == 0  # 중간 지급 없음
    await tick(client, 60)
    body = (await client.get(f"/api/sessions/{sid}")).json()
    assert body["status"] == "completed" and body["creditedSeconds"] == 2400
    assert await _trees("normal") == 2
    dash = (await client.get("/api/dashboard")).json()
    assert dash["today"]["successSeconds"] == 2400 and dash["today"]["successTrees"] == 2


async def test_two_30_minute_sessions_give_two_small_trees(client):
    await _member(client)
    sid = (await _start(client, 30, _cells(1, 0))).json()["id"]
    await tick(client, 1800)
    await client.get(f"/api/sessions/{sid}")
    sid = (await _start(client, 30, _cells(1, 1))).json()["id"]
    await tick(client, 1800)
    await client.get(f"/api/sessions/{sid}")
    async with SessionLocal() as s:
        sizes = (await s.execute(select(Tree.size))).scalars().all()
    assert sorted(sizes) == ["small", "small"]


async def test_abandon_59_minutes_gives_zero_and_keeps_previous(client):
    await _member(client)
    first = (await _start(client, 20, _cells(1, 0))).json()["id"]
    await tick(client, 1200)
    await client.get(f"/api/sessions/{first}")
    sid = (await _start(client, 60, _cells(3, 1))).json()["id"]
    await tick(client, 59 * 60)
    res = await client.post(f"/api/sessions/{sid}/abandon")
    body = res.json()
    assert body["status"] == "abandoned" and body["creditedSeconds"] == 0
    assert await _trees("wilted") == 3
    assert await _trees("normal") == 1  # 이전 성공 유지
    dash = (await client.get("/api/dashboard")).json()
    assert dash["today"]["successSeconds"] == 1200 and dash["today"]["wiltedTrees"] == 3


async def test_pause_excludes_time_and_resume_keeps_settings(client):
    await _member(client)
    sid = (await _start(client, 20, species="cherry")).json()["id"]
    await tick(client, 600)
    paused = (await client.post(f"/api/sessions/{sid}/pause")).json()
    assert paused["status"] == "paused" and paused["focusedSeconds"] == 600
    await tick(client, 3600)  # 일시정지 중 경과는 제외
    still = (await client.get(f"/api/sessions/{sid}")).json()
    assert still["status"] == "paused" and still["focusedSeconds"] == 600
    resumed = (await client.post(f"/api/sessions/{sid}/resume")).json()
    assert resumed["species"] == "cherry" and resumed["plots"] == paused["plots"]
    assert resumed["remainingSeconds"] == 600
    await tick(client, 600)
    assert (await client.get(f"/api/sessions/{sid}")).json()["status"] == "completed"


async def test_abandon_after_target_reached_returns_completed(client):
    await _member(client)
    sid = (await _start(client, 20)).json()["id"]
    await tick(client, 1201)
    body = (await client.post(f"/api/sessions/{sid}/abandon")).json()
    assert body["status"] == "completed"
    assert await _trees("normal") == 1 and await _trees("wilted") == 0
    # 이후 포기 재요청도 성공 나무를 회수하지 않는다.
    assert (await client.post(f"/api/sessions/{sid}/abandon")).json()["status"] == "completed"


async def test_concurrent_complete_and_abandon_no_duplicates(client):
    await _member(client)
    sid = (await _start(client, 60)).json()["id"]
    await tick(client, 3600)

    async def worker():
        async with SessionLocal() as s:
            return await settle_due(s)

    results = await asyncio.gather(
        worker(), worker(), client.post(f"/api/sessions/{sid}/abandon"), client.get(f"/api/sessions/{sid}")
    )
    assert results[2].json()["status"] == "completed"
    assert await _trees() == 3


async def test_two_tabs_start_race_only_one_wins(client):
    await _member(client)
    async with make_client() as tab2:
        await login(tab2, "u@test.io")
        r1, r2 = await asyncio.gather(_start(client, 20, _cells(1, 0)), _start(tab2, 20, _cells(1, 1)))
    assert sorted([r1.status_code, r2.status_code]) == [201, 409]


async def test_same_request_id_is_idempotent(client):
    await _member(client)
    rid = uuid.uuid4().hex
    a = await _start(client, 20, request_id=rid)
    b = await _start(client, 20, request_id=rid)
    assert a.status_code == 201 and b.status_code == 201 and a.json()["id"] == b.json()["id"]


async def test_occupied_cell_rejected_and_plots_fixed(client):
    await _member(client)
    sid = (await _start(client, 20, _cells(1, 0))).json()["id"]
    await tick(client, 1200)
    await client.get(f"/api/sessions/{sid}")
    assert (await _start(client, 20, _cells(1, 0))).status_code == 409
    # 이동 API 없음
    assert (await client.post(f"/api/sessions/{sid}/move", json={})).status_code in (404, 405)
    assert (await client.patch(f"/api/sessions/{sid}", json={"plots": []})).status_code == 405


async def test_new_zone_only_when_full(client):
    await _member(client)
    assert (await _start(client, 20, _cells(1), zone=1)).status_code == 400
    # 36칸 중 30칸을 채운 뒤 9칸이 필요한 세션은 새 구역에서만 가능
    used = 0
    for _ in range(3):
        sid = (await _start(client, 180, _cells(9, used))).json()["id"]
        used += 9
        await tick(client, 180 * 60)
        await client.get(f"/api/sessions/{sid}")
    sid = (await _start(client, 60, _cells(3, used))).json()["id"]
    used += 3
    await tick(client, 3600)
    await client.get(f"/api/sessions/{sid}")
    # 남은 칸 6개 < 9칸 → 새 구역 허용
    res = await _start(client, 180, _cells(9), zone=1)
    assert res.status_code == 201 and res.json()["zoneIndex"] == 1


async def test_other_users_session_hidden(client):
    await _member(client)
    sid = (await _start(client, 20)).json()["id"]
    async with make_client() as other:
        await create_user("o@test.io")
        await login(other, "o@test.io")
        assert (await other.get(f"/api/sessions/{sid}")).status_code == 404
        assert (await other.post(f"/api/sessions/{sid}/abandon")).status_code == 404


async def test_worker_restart_recovers_due_sessions(client):
    await _member(client)
    sid = (await _start(client, 20)).json()["id"]
    await tick(client, 5000)
    async with SessionLocal() as s:
        assert await settle_due(s) == 1
    async with SessionLocal() as s:
        assert await settle_due(s) == 0
        session = await s.get(FocusSession, uuid.UUID(sid))
        # 완료 시각은 요청 시각이 아니라 목표 도달 시각
        assert (session.completed_at - session.started_at).total_seconds() == 1200
    assert await _trees() == 1


async def test_rest_after_completion(client):
    await _member(client)
    sid = (await _start(client, 20, request_id="rest-" + uuid.uuid4().hex)).json()["id"]
    assert (await client.post(f"/api/sessions/{sid}/rest", json={"action": "start"})).status_code == 409
    await tick(client, 1200)
    res = await client.post(f"/api/sessions/{sid}/rest", json={"action": "start"})
    body = res.json()
    assert body["rest"]["state"] == "resting"
    await tick(client, 600)
    assert (await client.get(f"/api/sessions/{sid}")).json()["rest"]["state"] == "rest_completed"


async def test_active_endpoint_restores_session(client):
    await _member(client)
    assert (await client.get("/api/sessions/active")).json()["session"] is None
    sid = (await _start(client, 20)).json()["id"]
    assert (await client.get("/api/sessions/active")).json()["session"]["id"] == sid
