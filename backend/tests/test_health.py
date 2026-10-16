"""Stage 0 smoke tests: app boots, /api/health responds, auth routes are stubbed.

/api/ready is not covered here because it needs a live DB; it is exercised via
compose (`curl /api/ready`) in the stage-0 manual check.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_root_ok():
    res = client.get("/api")
    assert res.status_code == 200
    assert res.json()["service"] == "tree-for-study"


def test_auth_routes_are_stubbed():
    # Skeleton endpoints must not fake success before stage 1.
    assert client.post("/api/auth/login").status_code == 501
    assert client.post("/api/auth/register").status_code == 501
