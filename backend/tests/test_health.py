"""0단계 스모크 테스트: 앱 부팅, /api/health 응답, auth 라우트가 스텁인지 확인.

/api/ready는 실제 DB가 필요하므로 여기서 다루지 않는다. compose에서
`curl /api/ready`로 0단계 수동 점검 시 확인한다.
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
    # 스텁 엔드포인트는 1단계 전까지 성공을 가장하면 안 된다.
    assert client.post("/api/auth/login").status_code == 501
    assert client.post("/api/auth/register").status_code == 501
