"""서버가 검증한 클라이언트 IP(docs/05-library-ip.md).

규칙:
- 직접 연결한 상대(request.client.host)가 TRUSTED_PROXY_IPS(주소 또는 CIDR)에 속할 때만
  X-Forwarded-For를 읽는다. 그렇지 않으면 전달 헤더를 무시하고 연결 주소를 쓴다.
- 신뢰된 프록시 뒤라도 헤더의 '첫 값'을 쓰지 않는다. 오른쪽(가장 최근에 추가된 값)부터
  거슬러 올라가며 신뢰 프록시가 아닌 첫 주소를 클라이언트로 본다. 클라이언트가 위조해
  넣은 왼쪽 값은 이렇게 해서 무시된다.
"""
import ipaddress
from functools import lru_cache

from fastapi import Request

from app.core.config import get_settings


@lru_cache
def _trusted_networks(raw: str) -> tuple:
    nets = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            nets.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            continue
    return tuple(nets)


def _parse_ip(value: str | None):
    if not value:
        return None
    value = value.strip()
    # "[v6]:port" 또는 "v4:port" 형태 정리
    if value.startswith("[") and "]" in value:
        value = value[1 : value.index("]")]
    elif value.count(":") == 1 and "." in value:
        value = value.split(":")[0]
    try:
        return ipaddress.ip_address(value)
    except ValueError:
        return None


def _is_trusted(ip, nets) -> bool:
    return ip is not None and any(ip in net for net in nets)


def resolve_client_ip(peer: str | None, forwarded_for: str | None, trusted_raw: str) -> str | None:
    """순수 함수 형태의 판정 로직(테스트 용이성)."""
    nets = _trusted_networks(trusted_raw)
    peer_ip = _parse_ip(peer)
    if peer_ip is None:
        return None
    if not _is_trusted(peer_ip, nets) or not forwarded_for:
        return str(peer_ip)
    chain = [part for part in forwarded_for.split(",") if part.strip()]
    for raw in reversed(chain):
        ip = _parse_ip(raw)
        if ip is None:
            # 형식이 깨진 값이 섞여 있으면 신뢰할 수 없으므로 판정을 중단한다.
            return None
        if not _is_trusted(ip, nets):
            return str(ip)
    return str(peer_ip)


def client_ip(request: Request) -> str | None:
    peer = request.client.host if request.client else None
    return resolve_client_ip(peer, request.headers.get("x-forwarded-for"), get_settings().trusted_proxy_ips)
