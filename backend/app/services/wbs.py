"""WBS 서비스(상위 과제/하위 작업 최대 2단계).

공개 규칙(docs/01-product-plan.md §9):
- 팀원 화면에는 공개 행만 읽기 전용으로 보여 준다.
- 비공개 부모의 이름은 노출하지 않는다. 부모가 비공개인 공개 자식은 parentId 없이 독립 행으로 보낸다.
- 부모가 공개여도 비공개 자식은 보내지 않는다. 제목·메모·집계로 비공개 내용을 추정시키지 않는다.
"""
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, WbsTask


def task_out(t: WbsTask, *, parent_id: uuid.UUID | None | str = "keep") -> dict:
    pid = t.parent_id if parent_id == "keep" else parent_id
    return {
        "id": str(t.id),
        "parentId": str(pid) if pid else None,
        "title": t.title,
        "startDate": t.start_date.isoformat(),
        "endDate": t.end_date.isoformat(),
        "status": t.status,
        "progress": t.progress,
        "memo": t.memo,
        "isPublic": t.is_public,
    }


async def tasks_for(db: AsyncSession, user_id: uuid.UUID) -> list[WbsTask]:
    return list(
        (
            await db.execute(
                select(WbsTask).where(WbsTask.user_id == user_id).order_by(WbsTask.start_date, WbsTask.sort_order, WbsTask.created_at)
            )
        )
        .scalars()
        .all()
    )


async def public_tasks_for(db: AsyncSession, viewer: User, member_id: uuid.UUID) -> dict:
    member = await db.get(User, member_id)
    if member is None or member.status != "active" or viewer.status != "active":
        return {"member": None, "items": []}
    tasks = await tasks_for(db, member.id)
    by_id = {t.id: t for t in tasks}
    items = []
    for t in tasks:
        if not t.is_public:
            continue
        parent = by_id.get(t.parent_id) if t.parent_id else None
        if parent is not None and not parent.is_public:
            items.append(task_out(t, parent_id=None))
        else:
            items.append(task_out(t))
    return {
        "member": {"id": str(member.id), "displayName": member.display_name, "avatarEmoji": member.avatar_emoji, "bio": member.bio},
        "items": items,
    }


def overlaps(t: WbsTask, start: date, end: date) -> bool:
    return t.start_date <= end and t.end_date >= start
