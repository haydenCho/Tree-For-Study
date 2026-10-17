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


def test_production_settings_guard():
    from app.core.config import Settings

    bad = Settings(environment="production", jwt_secret="short", cookie_secure=False, app_origin="http://x", trusted_proxy_ips="")
    assert len(bad.production_problems()) == 4
    good = Settings(
        environment="production",
        jwt_secret="z" * 48,
        cookie_secure=True,
        app_origin="https://tree.example.com",
        trusted_proxy_ips="172.30.0.10",
    )
    assert good.production_problems() == []
    assert Settings(environment="development").production_problems() == []
