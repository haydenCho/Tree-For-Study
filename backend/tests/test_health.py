"""스모크 테스트: 앱 부팅과 /api/health 응답."""


async def test_health_ok(client):
    res = await client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


async def test_root_ok(client):
    res = await client.get("/api")
    assert res.status_code == 200
    assert res.json()["service"] == "tree-for-study"


async def test_api_is_not_cached(client):
    res = await client.get("/api/health")
    assert res.headers["cache-control"] == "no-store"
