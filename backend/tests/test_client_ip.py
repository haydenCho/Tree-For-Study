"""신뢰 프록시 기반 클라이언트 IP 판정(전달 헤더 위조 거부)."""
from app.core.client_ip import resolve_client_ip

TRUSTED = "10.0.0.2,172.18.0.0/16"


def test_direct_connection_ignores_forwarded_header():
    # 신뢰하지 않는 상대가 보낸 X-Forwarded-For는 무시한다.
    assert resolve_client_ip("198.51.100.7", "1.2.3.4", TRUSTED) == "198.51.100.7"


def test_trusted_proxy_uses_rightmost_untrusted():
    # 클라이언트가 왼쪽에 위조 값을 넣어도 Caddy가 덧붙인 실제 주소를 쓴다.
    assert resolve_client_ip("10.0.0.2", "1.2.3.4, 203.0.113.50", TRUSTED) == "203.0.113.50"


def test_chain_of_trusted_proxies():
    assert resolve_client_ip("172.18.0.5", "203.0.113.50, 10.0.0.2", TRUSTED) == "203.0.113.50"


def test_garbage_header_is_not_trusted():
    assert resolve_client_ip("10.0.0.2", "not-an-ip", TRUSTED) is None


def test_ipv6():
    assert resolve_client_ip("10.0.0.2", "2001:db8::1", TRUSTED) == "2001:db8::1"
