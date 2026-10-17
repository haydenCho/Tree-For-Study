"""공동 숲(광장) 무작위 배치.

정상 완료로 확정된 나무만 공동 숲에 올린다(시든 나무 제외). 개인 좌표와 무관하게 서버가
빈 칸을 무작위로 골라 저장하며, 새로고침마다 다시 추첨하지 않는다. 가장 최근 구역에
빈 칸이 없으면 다음 구역을 연다. advisory lock으로 배치를 직렬화하고 (구역, 행, 열)·tree_id
unique 제약이 겹침을 최종적으로 막는다. 사용자·운영자 모두 공동 나무를 옮기는 기능은 없다.
"""
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.core.db import LOCK_COMMUNITY, advisory_xact_lock
from app.core.policy import ZONE_SIZE
from app.models import CommunityPlacement, Tree

_rng = random.SystemRandom()


def choose_cells(occupied: set[tuple[int, int, int]], count: int, rng=_rng) -> list[tuple[int, int, int]]:
    """이미 찬 (구역, 행, 열) 집합에서 count개의 서로 다른 빈 칸을 무작위로 고른다.

    가장 최근 구역부터 채우고, 꽉 차면 다음 구역을 연다. 순수 함수라 단위 테스트가 쉽다.
    """
    taken = set(occupied)
    zone = max((z for z, _, _ in taken), default=0)
    chosen = []
    for _ in range(count):
        free = [(r, c) for r in range(ZONE_SIZE) for c in range(ZONE_SIZE) if (zone, r, c) not in taken]
        if not free:
            zone += 1
            free = [(r, c) for r in range(ZONE_SIZE) for c in range(ZONE_SIZE)]
        r, c = rng.choice(free)
        taken.add((zone, r, c))
        chosen.append((zone, r, c))
    return chosen


async def place_trees(db: AsyncSession, trees: list[Tree]) -> list[CommunityPlacement]:
    trees = [t for t in trees if t.state in ("normal", "library")]
    if not trees:
        return []
    await advisory_xact_lock(db, LOCK_COMMUNITY)
    rows = (await db.execute(select(CommunityPlacement.zone_index, CommunityPlacement.row, CommunityPlacement.col))).all()
    cells = choose_cells({(z, r, c) for z, r, c in rows}, len(trees))
    now = utcnow()
    placed = []
    for tree, (zone, r, c) in zip(trees, cells):
        p = CommunityPlacement(tree_id=tree.id, user_id=tree.user_id, zone_index=zone, row=r, col=c, created_at=now)
        db.add(p)
        placed.append(p)
    await db.flush()
    return placed
