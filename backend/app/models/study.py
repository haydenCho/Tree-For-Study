"""스터디 일정·출석·도서관 네트워크·공동 숲·WBS 모델(2단계).

- study_dates: 날짜별 종류. in_person(화~금 대면) / self(자율일: 월·주말 보충) / holiday(운영자 휴무).
- attendance: 체크인 또는 운영자 정정 기록만 행으로 남긴다. 결석은 '지난 대면일 + 기록 없음'으로
  조회 시 계산한다(다음 날 00:00 KST부터 결석). 지각 상태는 없다.
- library_networks: 운영자가 확인해 등록한 도서관 공인 IP(정확한 주소 기본, 확인된 CIDR만).
- app_settings: 정수 설정값(도서관 규칙 버전 등).
- community_placements: 공동 숲 배치. (구역, 행, 열)과 tree_id 각각 고유. 정상 완료 나무만.
- wbs_tasks: 상위 과제/하위 작업(최대 2단계), 행별 공개.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

DATE_KINDS = ("in_person", "self", "holiday")
ATTENDANCE_STATUSES = ("present", "absent", "holiday")
WBS_STATUSES = ("planned", "in_progress", "done")


class StudyDate(Base):
    __tablename__ = "study_dates"
    __table_args__ = (CheckConstraint(f"kind IN {DATE_KINDS}", name="kind"),)

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str] = mapped_column(String(100), nullable=False, default="")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("user_id", "day", name="uq_attendance_user_day"),
        CheckConstraint(f"status IN {ATTENDANCE_STATUSES}", name="status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    corrected_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LibraryNetwork(Base):
    __tablename__ = "library_networks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # 정확한 IPv4/IPv6 주소 또는 확인된 CIDR (정규화된 network 표기로 저장)
    network: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class CommunityPlacement(Base):
    __tablename__ = "community_placements"
    __table_args__ = (
        UniqueConstraint("zone_index", "row", "col", name="uq_community_cell"),
        UniqueConstraint("tree_id", name="uq_community_tree"),
        CheckConstraint("row BETWEEN 0 AND 5 AND col BETWEEN 0 AND 5", name="cell_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tree_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trees.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    zone_index: Mapped[int] = mapped_column(Integer, nullable=False)
    row: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    col: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WbsTask(Base):
    __tablename__ = "wbs_tasks"
    __table_args__ = (
        CheckConstraint(f"status IN {WBS_STATUSES}", name="status"),
        CheckConstraint("progress BETWEEN 0 AND 100", name="progress"),
        CheckConstraint("end_date >= start_date", name="date_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("wbs_tasks.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="planned")
    progress: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    memo: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
