"""3단계 라우트: WBS CRUD, 드래그 시간표, 주말 보충, 주간 회고.

GET/POST /api/wbs, PATCH/DELETE /api/wbs/{id}
GET /api/timetable-blocks?date=, POST /api/timetable-blocks, PATCH/DELETE /api/timetable-blocks/{id}
GET /api/goals?from=&to=&done=, POST /api/goals/{id}/carry
GET/PUT /api/weekly-reviews/{date}           — date가 속한 주(월요일 시작)
GET     /api/members/{id}/weekly-reviews/{date} — 공개 회고만
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import active_member
from app.core.db import get_session
from app.core.errors import bad_request
from app.models import Goal, User
from app.schemas.common import CamelModel
from app.services import planner, records, wbs

router = APIRouter(tags=["planner"])


# ── WBS ──────────────────────────────────────────────────────────
class WbsIn(CamelModel):
    title: str = Field(max_length=120)
    start_date: date
    end_date: date
    parent_id: uuid.UUID | None = None
    status: str = "planned"
    progress: int = 0
    memo: str = Field(default="", max_length=2000)
    is_public: bool = False


class WbsPatch(CamelModel):
    title: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    progress: int | None = None
    memo: str | None = Field(default=None, max_length=2000)
    is_public: bool | None = None


@router.get("/wbs")
async def list_wbs(user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return {"items": [wbs.task_out(t) for t in await wbs.tasks_for(db, user.id)]}


@router.post("/wbs", status_code=201)
async def create_wbs(body: WbsIn, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return wbs.task_out(await wbs.create_task(db, user, body.model_dump()))


@router.patch("/wbs/{task_id}")
async def update_wbs(task_id: uuid.UUID, body: WbsPatch, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return wbs.task_out(await wbs.update_task(db, user, task_id, body.model_dump()))


@router.delete("/wbs/{task_id}", status_code=204)
async def delete_wbs(task_id: uuid.UUID, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> None:
    await wbs.delete_task(db, user, task_id)


# ── 시간표 ───────────────────────────────────────────────────────
class BlockIn(CamelModel):
    date: date
    layer: str
    start_min: int
    end_min: int
    title: str = Field(max_length=80)
    memo: str = Field(default="", max_length=500)


class BlockPatch(CamelModel):
    layer: str | None = None
    start_min: int | None = None
    end_min: int | None = None
    title: str | None = Field(default=None, max_length=80)
    memo: str | None = Field(default=None, max_length=500)


@router.get("/timetable-blocks")
async def list_blocks(date: str, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return {"items": [planner.block_out(b) for b in await planner.blocks_for(db, user.id, records.parse_date(date))]}


@router.post("/timetable-blocks", status_code=201)
async def create_block(body: BlockIn, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    b = await planner.create_block(
        db, user, day=body.date, layer=body.layer, start=body.start_min, end=body.end_min, title=body.title, memo=body.memo
    )
    return planner.block_out(b)


@router.patch("/timetable-blocks/{block_id}")
async def update_block(block_id: uuid.UUID, body: BlockPatch, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    b = await planner.update_block(
        db,
        user,
        block_id,
        {"layer": body.layer, "start": body.start_min, "end": body.end_min, "title": body.title, "memo": body.memo},
    )
    return planner.block_out(b)


@router.delete("/timetable-blocks/{block_id}", status_code=204)
async def delete_block(block_id: uuid.UUID, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> None:
    b = await planner.own_block(db, user, block_id)
    await db.delete(b)
    await db.commit()


# ── 목표 범위 조회·주말 보충 ─────────────────────────────────────
class CarryIn(CamelModel):
    target_date: date


@router.get("/goals")
async def list_goals(
    from_: str = Query(alias="from"),
    to: str = "",
    done: bool | None = None,
    user: User = Depends(active_member),
    db: AsyncSession = Depends(get_session),
) -> dict:
    start = records.parse_date(from_)
    end = records.parse_date(to) if to else start
    if (end - start).days > 62:
        raise bad_request("range_too_long", "조회 기간은 62일 이하로 지정해 주세요.")
    q = select(Goal).where(Goal.user_id == user.id, Goal.goal_date >= start, Goal.goal_date <= end)
    if done is not None:
        q = q.where(Goal.done.is_(done))
    goals = (await db.execute(q.order_by(Goal.goal_date, Goal.sort_order))).scalars().all()
    return {"items": [records.goal_out(g) for g in goals]}


@router.post("/goals/{goal_id}/carry", status_code=201)
async def carry(goal_id: uuid.UUID, body: CarryIn, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return records.goal_out(await planner.carry_goal(db, user, goal_id, body.target_date))


# ── 주간 회고 ────────────────────────────────────────────────────
class ReviewIn(CamelModel):
    good: str | None = Field(default=None, max_length=planner.MAX_TEXT)
    hard: str | None = Field(default=None, max_length=planner.MAX_TEXT)
    next_plan: str | None = Field(default=None, max_length=planner.MAX_TEXT)
    is_public: bool | None = None


@router.get("/weekly-reviews/{day}")
async def get_review(day: str, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    ws = planner.week_start_of(records.parse_date(day))
    return {
        **planner.review_out(await planner.get_review(db, user.id, ws), ws),
        "totals": await planner.weekly_totals(db, user.id, ws),
    }


@router.put("/weekly-reviews/{day}")
async def put_review(day: str, body: ReviewIn, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    ws = planner.week_start_of(records.parse_date(day))
    r = await planner.upsert_review(db, user, ws, body.model_dump())
    return {**planner.review_out(r, ws), "totals": await planner.weekly_totals(db, user.id, ws)}


@router.get("/members/{member_id}/weekly-reviews/{day}")
async def member_review(member_id: uuid.UUID, day: str, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    ws = planner.week_start_of(records.parse_date(day))
    member = await db.get(User, member_id)
    hidden = {"weekStart": ws.isoformat(), "public": False}
    if member is None or member.status != "active":
        return hidden
    r = await planner.get_review(db, member.id, ws)
    if r is None or not r.is_public:
        return hidden
    out = planner.review_out(r, ws)
    out.pop("updatedAt", None)
    return {
        **out,
        "public": True,
        "member": {"id": str(member.id), "displayName": member.display_name, "avatarEmoji": member.avatar_emoji},
        "totals": await planner.weekly_totals(db, member.id, ws),
    }
