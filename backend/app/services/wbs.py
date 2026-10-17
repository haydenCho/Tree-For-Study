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

from app.core.clock import utcnow
from app.core.errors import bad_request, not_found
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


# ── 본인 WBS 생성·수정·삭제(3단계) ────────────────────────────────
MAX_MEMO = 2000


async def own_task(db: AsyncSession, user: User, task_id: uuid.UUID) -> WbsTask:
    t = await db.get(WbsTask, task_id)
    if t is None or t.user_id != user.id:
        raise not_found("wbs_not_found", "WBS 항목을 찾을 수 없어요.")
    return t


def _validate_fields(title: str, start: date, end: date, status: str, progress: int, memo: str) -> None:
    if not 1 <= len(title) <= 120:
        raise bad_request("invalid_title", "제목은 1~120자로 입력해 주세요.")
    if end < start:
        raise bad_request("invalid_range", "종료일은 시작일과 같거나 늦어야 해요.")
    if status not in ("planned", "in_progress", "done"):
        raise bad_request("invalid_status", "상태를 확인해 주세요.")
    if not 0 <= progress <= 100:
        raise bad_request("invalid_progress", "진행률은 0~100 사이예요.")
    if len(memo) > MAX_MEMO:
        raise bad_request("invalid_memo", f"메모는 {MAX_MEMO}자 이하로 입력해 주세요.")


async def _validate_parent(db: AsyncSession, user: User, parent_id: uuid.UUID | None, start: date, end: date, self_id=None) -> None:
    if parent_id is None:
        return
    if self_id is not None and parent_id == self_id:
        raise bad_request("invalid_parent", "자기 자신을 상위 과제로 지정할 수 없어요.")
    parent = await db.get(WbsTask, parent_id)
    if parent is None or parent.user_id != user.id:
        raise bad_request("invalid_parent", "상위 과제를 찾을 수 없어요.")
    if parent.parent_id is not None:
        raise bad_request("too_deep", "WBS는 상위 과제/하위 작업 2단계까지예요.")
    if start < parent.start_date or end > parent.end_date:
        raise bad_request("outside_parent", "하위 작업 기간은 상위 과제 기간 안이어야 해요.")


async def create_task(db: AsyncSession, user: User, data: dict) -> WbsTask:
    title = (data.get("title") or "").strip()
    memo = (data.get("memo") or "").strip()
    status = data.get("status") or "planned"
    progress = int(data.get("progress") or 0)
    _validate_fields(title, data["start_date"], data["end_date"], status, progress, memo)
    await _validate_parent(db, user, data.get("parent_id"), data["start_date"], data["end_date"])
    now = utcnow()
    t = WbsTask(
        user_id=user.id,
        parent_id=data.get("parent_id"),
        title=title,
        start_date=data["start_date"],
        end_date=data["end_date"],
        status=status,
        progress=progress,
        memo=memo,
        is_public=bool(data.get("is_public")),
        created_at=now,
        updated_at=now,
    )
    db.add(t)
    await db.commit()
    return t


async def update_task(db: AsyncSession, user: User, task_id: uuid.UUID, data: dict) -> WbsTask:
    t = await own_task(db, user, task_id)
    title = (data["title"] if data.get("title") is not None else t.title).strip()
    memo = (data["memo"] if data.get("memo") is not None else t.memo).strip()
    start = data.get("start_date") or t.start_date
    end = data.get("end_date") or t.end_date
    status = data.get("status") or t.status
    progress = data["progress"] if data.get("progress") is not None else t.progress
    _validate_fields(title, start, end, status, progress, memo)
    await _validate_parent(db, user, t.parent_id, start, end, self_id=t.id)
    # 상위 과제 기간을 줄일 때 하위 작업이 밖으로 나가면 거부한다.
    children = (await db.execute(select(WbsTask).where(WbsTask.parent_id == t.id))).scalars().all()
    if any(c.start_date < start or c.end_date > end for c in children):
        raise bad_request("children_outside", "하위 작업이 새 기간 밖에 있어요. 하위 작업 기간을 먼저 조정해 주세요.")
    t.title, t.memo, t.start_date, t.end_date, t.status, t.progress = title, memo, start, end, status, progress
    if data.get("is_public") is not None:
        t.is_public = data["is_public"]
    t.updated_at = utcnow()
    await db.commit()
    return t


async def delete_task(db: AsyncSession, user: User, task_id: uuid.UUID) -> None:
    t = await own_task(db, user, task_id)
    await db.delete(t)  # 하위 작업은 FK ondelete=CASCADE로 함께 삭제
    await db.commit()
