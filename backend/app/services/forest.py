"""개인 숲 조회: 구역별 칸 상태(묘목/나무/시든 나무)."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FocusSession, PersonalZone, SessionPlot, Tree


async def personal_forest(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    zones = (
        await db.execute(select(PersonalZone).where(PersonalZone.user_id == user_id).order_by(PersonalZone.zone_index))
    ).scalars().all()
    rows = (
        await db.execute(
            select(SessionPlot, FocusSession, Tree)
            .join(FocusSession, FocusSession.id == SessionPlot.session_id)
            .outerjoin(Tree, Tree.plot_id == SessionPlot.id)
            .where(SessionPlot.user_id == user_id)
        )
    ).all()
    by_zone: dict[uuid.UUID, list[dict]] = {z.id: [] for z in zones}
    for plot, session, tree in rows:
        if tree is not None:
            cell = {"row": plot.row, "col": plot.col, "state": tree.state, "species": tree.species, "size": tree.size}
        else:
            # 진행 중 세션의 예약 칸은 묘목으로 표시한다(보상 확정 아님).
            cell = {"row": plot.row, "col": plot.col, "state": "seedling", "species": session.species, "size": session.size}
        cell["sessionId"] = str(session.id)
        by_zone.setdefault(plot.zone_id, []).append(cell)
    result = [{"index": z.zone_index, "cells": by_zone.get(z.id, [])} for z in zones]
    if not result:
        result = [{"index": 0, "cells": []}]
    return result
