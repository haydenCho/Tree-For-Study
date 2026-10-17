"""3단계 모델: 드래그 시간표 블록, 주간 회고.

- timetable_blocks: 한국 시간 하루를 0~1440분으로 표현, 15분 단위. 같은 날짜·같은 레이어(plan/actual)
  안에서는 겹침을 거부하고, 계획/실제 레이어끼리는 겹쳐도 된다. 집중 보상과 무관한 자기 기록이다.
- weekly_reviews: 주 시작(월요일) 기준 사용자당 하나. 잘한 점/어려웠던 점/다음 주 계획, 기본 비공개.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, SmallInteger, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

LAYERS = ("plan", "actual")


class TimetableBlock(Base):
    __tablename__ = "timetable_blocks"
    __table_args__ = (
        CheckConstraint(f"layer IN {LAYERS}", name="layer"),
        CheckConstraint("start_min >= 0 AND end_min <= 1440 AND end_min > start_min", name="range"),
        CheckConstraint("start_min % 15 = 0 AND end_min % 15 = 0", name="snap"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    layer: Mapped[str] = mapped_column(String(8), nullable=False)
    start_min: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    end_min: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    memo: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WeeklyReview(Base):
    __tablename__ = "weekly_reviews"
    __table_args__ = (UniqueConstraint("user_id", "week_start", name="uq_weekly_review"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    good: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hard: Mapped[str] = mapped_column(Text, nullable=False, default="")
    next_plan: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
