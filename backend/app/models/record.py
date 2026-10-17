"""날짜별 계획·기록·목표 모델(docs/01-product-plan.md §8).

daily_entries는 (사용자, 대상 날짜)당 하나이며 기본 비공개다. 공개하면 같은 스터디
멤버에게 해당 날짜의 계획·목표·기록·시간표를 함께 공유한다.
goals.carried_from_id는 주말 보충으로 이월한 원본 목표를 가리킨다.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DailyEntry(Base):
    __tablename__ = "daily_entries"
    __table_args__ = (UniqueConstraint("user_id", "entry_date", name="uq_daily_entry"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    plan_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    record_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (UniqueConstraint("carried_from_id", "goal_date", name="uq_goal_carry_target"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    goal_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    carried_from_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
