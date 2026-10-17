"""집중 세션·개인 숲 모델(docs/01-product-plan.md §3, §4, §12).

- focus_sessions: 세션 하나 = 수종 하나 = 구역 하나. 상태 focusing ↔ paused →
  completed / abandoned. 사용자당 활성(focusing/paused) 세션은 하나(부분 unique 인덱스).
- focus_intervals: 실제 집중 구간. pause 때 닫고 resume 때 새로 연다.
- session_plots: 시작 시 예약한 칸. (구역, 행, 열) 고유. 성공/포기와 무관하게 위치 고정.
- trees: 정상 완료(normal/library) 또는 포기(wilted) 시 확정. (세션, 순번) 고유,
  칸당 하나.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

SESSION_STATUSES = ("focusing", "paused", "completed", "abandoned")
ACTIVE_STATUSES = ("focusing", "paused")
TREE_STATES = ("normal", "library", "wilted")


class PersonalZone(Base):
    __tablename__ = "personal_zones"
    __table_args__ = (UniqueConstraint("user_id", "zone_index", name="uq_personal_zone"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    zone_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FocusSession(Base):
    __tablename__ = "focus_sessions"
    __table_args__ = (
        CheckConstraint(f"status IN {SESSION_STATUSES}", name="status"),
        CheckConstraint("size IN ('small','large')", name="size"),
        CheckConstraint("target_seconds BETWEEN 1200 AND 10800", name="target"),
        UniqueConstraint("user_id", "request_id", name="uq_focus_request"),
        # 사용자당 활성 세션 하나 — 두 탭/기기에서 동시에 시작해도 하나만 성공한다.
        Index(
            "uq_focus_one_active",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('focusing','paused')"),
        ),
        Index("ix_focus_due", "status", "target_end_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    zone_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("personal_zones.id"), nullable=False)
    species: Mapped[str] = mapped_column(String(16), nullable=False)
    size: Mapped[str] = mapped_column(String(8), nullable=False)
    tree_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    target_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=600)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    # 도서관 보너스: 시작 요청 시점에만 판정해 고정(docs/05-library-ip.md)
    library_at_start: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    network_rule_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # 닫힌 구간들의 누적 집중 초
    accumulated_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 진행 중인 구간의 시작(일시정지 상태면 NULL)
    current_interval_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 집중 중일 때 목표 도달 예정 시각(일시정지면 NULL)
    target_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 성공 시 목표 시간 전체, 포기 시 0
    credited_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 진단용 원시 집중 초(공식 통계에 포함하지 않음)
    observed_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    abandoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rest_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rest_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class FocusInterval(Base):
    __tablename__ = "focus_intervals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("focus_sessions.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SessionPlot(Base):
    __tablename__ = "session_plots"
    __table_args__ = (
        UniqueConstraint("zone_id", "row", "col", name="uq_plot_cell"),
        UniqueConstraint("session_id", "ordinal", name="uq_plot_ordinal"),
        CheckConstraint("row BETWEEN 0 AND 5 AND col BETWEEN 0 AND 5", name="cell_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("focus_sessions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    zone_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("personal_zones.id"), nullable=False)
    row: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    col: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ordinal: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class Tree(Base):
    __tablename__ = "trees"
    __table_args__ = (
        UniqueConstraint("session_id", "ordinal", name="uq_tree_session_ordinal"),
        UniqueConstraint("plot_id", name="uq_tree_plot"),
        CheckConstraint(f"state IN {TREE_STATES}", name="state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("focus_sessions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("session_plots.id", ondelete="CASCADE"))
    ordinal: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    species: Mapped[str] = mapped_column(String(16), nullable=False)
    size: Mapped[str] = mapped_column(String(8), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
