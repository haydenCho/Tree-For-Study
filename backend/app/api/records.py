"""날짜별 기록·목표 라우트.

GET/PUT /api/daily-entries/{date}          — 본인 기록(기본 비공개)
GET     /api/members/{id}/daily-entries/{date} — 타인 공개 기록(공개 필터 적용)
POST /api/goals, PATCH/DELETE /api/goals/{id}
"""
import uuid

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import active_member
from app.core.db import get_session
from app.core.errors import bad_request
from app.models import User
from app.schemas.common import CamelModel
from app.services import records

router = APIRouter(tags=["records"])


class EntryIn(CamelModel):
    plan_text: str | None = Field(default=None, max_length=records.MAX_TEXT)
    record_text: str | None = Field(default=None, max_length=records.MAX_TEXT)
    is_public: bool | None = None


class GoalIn(CamelModel):
    date: str
    title: str = Field(max_length=120)


class GoalPatch(CamelModel):
    title: str | None = Field(default=None, max_length=120)
    done: bool | None = None


@router.get("/daily-entries/{day}")
async def get_entry(day: str, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return await records.entry_payload(db, user.id, records.parse_date(day))


@router.put("/daily-entries/{day}")
async def put_entry(day: str, body: EntryIn, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    d = records.parse_date(day)
    await records.upsert_entry(db, user, d, plan_text=body.plan_text, record_text=body.record_text, is_public=body.is_public)
    return await records.entry_payload(db, user.id, d)


@router.get("/members/{member_id}/daily-entries/{day}")
async def member_entry(
    member_id: uuid.UUID, day: str, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)
) -> dict:
    return await records.public_entry_for(db, user, member_id, records.parse_date(day))


@router.post("/goals", status_code=201)
async def add_goal(body: GoalIn, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return records.goal_out(await records.add_goal(db, user, records.parse_date(body.date), body.title))


@router.patch("/goals/{goal_id}")
async def patch_goal(
    goal_id: uuid.UUID, body: GoalPatch, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)
) -> dict:
    goal = await records.own_goal(db, user, goal_id)
    if body.title is not None:
        title = body.title.strip()
        if not title:
            raise bad_request("invalid_goal", "목표는 1~120자로 입력해 주세요.")
        goal.title = title
    if body.done is not None:
        goal.done = body.done
    await db.commit()
    return records.goal_out(goal)


@router.delete("/goals/{goal_id}", status_code=204)
async def delete_goal(goal_id: uuid.UUID, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> None:
    goal = await records.own_goal(db, user, goal_id)
    await db.delete(goal)
    await db.commit()
