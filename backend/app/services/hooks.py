"""세션 흐름의 확장 지점.

- detect_library: 시작 요청 시점의 서버 검증 IP로 도서관 보너스를 판정한다.
- on_trees_confirmed: 정상 완료로 나무가 확정된 직후(같은 트랜잭션) 호출된다.

1단계에서는 도서관 판정을 하지 않으므로 항상 False(예시 IP로 인정하지 않음),
공동 숲 배치도 하지 않는다. 2단계에서 실제 구현으로 교체한다.
"""
from sqlalchemy.ext.asyncio import AsyncSession


async def detect_library(db: AsyncSession, client_ip: str | None) -> tuple[bool, int]:
    return False, 0


async def on_trees_confirmed(db: AsyncSession, session, trees) -> None:
    return None
