"""세션 흐름의 확장 지점.

- detect_library: 시작 요청 시점의 서버 검증 IP로 도서관 보너스를 판정한다(2단계).
- on_trees_confirmed: 정상 완료로 나무가 확정된 직후 같은 트랜잭션에서 공동 숲에 배치한다.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import community, library


async def detect_library(db: AsyncSession, client_ip: str | None) -> tuple[bool, int]:
    return await library.detect(db, client_ip)


async def on_trees_confirmed(db: AsyncSession, session, trees) -> None:
    await community.place_trees(db, trees)
