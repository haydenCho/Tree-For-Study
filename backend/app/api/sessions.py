"""집중 세션 라우트.

POST /api/sessions (species, targetMinutes, restMinutes, zoneIndex, plots, requestId)
POST /api/sessions/{id}/pause | resume | abandon | rest
GET  /api/sessions/active, /api/sessions/{id}

성공 완료는 서버(워커 또는 조회 시 settle)만 처리한다. 운영용 강제 완료·시간 조작 API는 없다.
"""
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import active_member
from app.core.client_ip import client_ip
from app.core.db import get_session
from app.models import User
from app.schemas.common import CamelModel
from app.services import focus

router = APIRouter(prefix="/sessions", tags=["sessions"])


class PlotIn(CamelModel):
    row: int
    col: int


class StartIn(CamelModel):
    species: str = Field(max_length=16)
    target_minutes: int
    rest_minutes: int | None = None
    zone_index: int = 0
    plots: list[PlotIn] = Field(max_length=9)
    request_id: str = Field(min_length=8, max_length=64)


class RestIn(CamelModel):
    action: str


@router.post("", status_code=201)
async def start(body: StartIn, request: Request, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    s = await focus.start_session(
        db,
        user,
        species=body.species,
        target_minutes=body.target_minutes,
        rest_minutes=body.rest_minutes,
        zone_index=body.zone_index,
        plots=[(p.row, p.col) for p in body.plots],
        request_id=body.request_id,
        client_ip=client_ip(request),
    )
    return await focus.serialize(db, s)


@router.get("/active")
async def active(user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    s = await focus.get_active(db, user.id)
    if s is None:
        return {"session": None}
    s = await focus.get_for_user(db, user, s.id)
    if s.status not in ("focusing", "paused"):
        return {"session": None, "justFinished": await focus.serialize(db, s)}
    return {"session": await focus.serialize(db, s)}


@router.get("/{session_id}")
async def get_one(session_id: uuid.UUID, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return await focus.serialize(db, await focus.get_for_user(db, user, session_id))


@router.post("/{session_id}/pause")
async def pause(session_id: uuid.UUID, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return await focus.serialize(db, await focus.pause(db, user, session_id))


@router.post("/{session_id}/resume")
async def resume(session_id: uuid.UUID, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return await focus.serialize(db, await focus.resume(db, user, session_id))


@router.post("/{session_id}/abandon")
async def abandon(session_id: uuid.UUID, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return await focus.serialize(db, await focus.abandon(db, user, session_id))


@router.post("/{session_id}/rest")
async def rest(session_id: uuid.UUID, body: RestIn, user: User = Depends(active_member), db: AsyncSession = Depends(get_session)) -> dict:
    return await focus.serialize(db, await focus.rest(db, user, session_id, body.action))
