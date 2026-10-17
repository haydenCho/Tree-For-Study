"""도서관 보너스 판정(docs/05-library-ip.md).

세션 시작 요청 시점의 서버 검증 IP(app.core.client_ip)가 등록 목록에 속하면
library_at_start=true로 고정한다. 이후 네트워크 변경·재개·종료 IP는 다시 판정하지 않는다.
규칙을 바꿀 때마다 버전을 올려 세션에 '어떤 규칙으로 판정했는지'를 남긴다.
"""
import ipaddress
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.core.errors import bad_request, conflict, not_found
from app.models import AppSetting, LibraryNetwork

RULE_VERSION_KEY = "library_rule_version"
# 확인하지 않은 큰 범위 등록을 막기 위한 최소 prefix 길이
MIN_PREFIX_V4 = 24
MIN_PREFIX_V6 = 56


def normalize_network(raw: str) -> str:
    raw = (raw or "").strip()
    try:
        net = ipaddress.ip_network(raw, strict=False)
    except ValueError:
        raise bad_request("invalid_network", "IPv4/IPv6 주소 또는 CIDR 형식을 확인해 주세요.")
    limit = MIN_PREFIX_V4 if net.version == 4 else MIN_PREFIX_V6
    if net.prefixlen < limit:
        raise bad_request("network_too_wide", f"/{limit}보다 넓은 범위는 등록할 수 없어요. 실제 도서관 주소를 확인해 주세요.")
    return str(net)


async def rule_version(db: AsyncSession) -> int:
    row = await db.get(AppSetting, RULE_VERSION_KEY)
    return row.value if row else 0


async def _bump_version(db: AsyncSession) -> None:
    row = await db.get(AppSetting, RULE_VERSION_KEY, with_for_update=True)
    if row is None:
        db.add(AppSetting(key=RULE_VERSION_KEY, value=1))
    else:
        row.value += 1


async def list_networks(db: AsyncSession) -> list[LibraryNetwork]:
    return list((await db.execute(select(LibraryNetwork).order_by(LibraryNetwork.created_at))).scalars().all())


async def is_library_ip(db: AsyncSession, ip: str | None) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for n in await list_networks(db):
        net = ipaddress.ip_network(n.network, strict=False)
        if addr.version == net.version and addr in net:
            return True
    return False


async def detect(db: AsyncSession, ip: str | None) -> tuple[bool, int]:
    return await is_library_ip(db, ip), await rule_version(db)


async def add_network(db: AsyncSession, raw: str, label: str) -> LibraryNetwork:
    normalized = normalize_network(raw)
    exists = (await db.execute(select(LibraryNetwork.id).where(LibraryNetwork.network == normalized))).first()
    if exists:
        raise conflict("network_exists", "이미 등록된 주소예요.")
    await _bump_version(db)
    net = LibraryNetwork(network=normalized, label=(label or "")[:60], created_at=utcnow())
    db.add(net)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise conflict("network_exists", "이미 등록된 주소예요.")
    return net


async def remove_network(db: AsyncSession, network_id: uuid.UUID) -> None:
    net = await db.get(LibraryNetwork, network_id)
    if net is None:
        raise not_found()
    await db.delete(net)
    await _bump_version(db)
    await db.commit()
