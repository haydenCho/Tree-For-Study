"""2단계 스키마: 스터디 날짜(운영자 지정분), 출석, 도서관 네트워크, 정수 설정, 공동 숲 배치, WBS.

study_dates는 운영자가 바꾼 날짜만 저장한다. 기본값(화~금 대면, 그 외 자율)은 코드에서 계산한다.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-17 21:15:55.356388
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('app_settings',
    sa.Column('key', sa.String(length=60), nullable=False),
    sa.Column('value', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('key', name=op.f('pk_app_settings'))
    )
    op.create_table('library_networks',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('network', sa.String(length=64), nullable=False),
    sa.Column('label', sa.String(length=60), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_library_networks')),
    sa.UniqueConstraint('network', name=op.f('uq_library_networks_network'))
    )
    op.create_table('study_dates',
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('note', sa.String(length=100), nullable=False),
    sa.CheckConstraint("kind IN ('in_person', 'self', 'holiday')", name=op.f('ck_study_dates_kind')),
    sa.PrimaryKeyConstraint('day', name=op.f('pk_study_dates'))
    )
    op.create_table('attendance',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('checked_in_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('corrected_by', sa.Uuid(), nullable=True),
    sa.Column('reason', sa.String(length=300), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("status IN ('present', 'absent', 'holiday')", name=op.f('ck_attendance_status')),
    sa.ForeignKeyConstraint(['corrected_by'], ['users.id'], name=op.f('fk_attendance_corrected_by_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_attendance_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_attendance')),
    sa.UniqueConstraint('user_id', 'day', name='uq_attendance_user_day')
    )
    op.create_index(op.f('ix_attendance_user_id'), 'attendance', ['user_id'], unique=False)
    op.create_table('wbs_tasks',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('parent_id', sa.Uuid(), nullable=True),
    sa.Column('title', sa.String(length=120), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('progress', sa.SmallInteger(), nullable=False),
    sa.Column('memo', sa.Text(), nullable=False),
    sa.Column('is_public', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("status IN ('planned', 'in_progress', 'done')", name=op.f('ck_wbs_tasks_status')),
    sa.CheckConstraint('end_date >= start_date', name=op.f('ck_wbs_tasks_date_order')),
    sa.CheckConstraint('progress BETWEEN 0 AND 100', name=op.f('ck_wbs_tasks_progress')),
    sa.ForeignKeyConstraint(['parent_id'], ['wbs_tasks.id'], name=op.f('fk_wbs_tasks_parent_id_wbs_tasks'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_wbs_tasks_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_wbs_tasks'))
    )
    op.create_index(op.f('ix_wbs_tasks_parent_id'), 'wbs_tasks', ['parent_id'], unique=False)
    op.create_index(op.f('ix_wbs_tasks_user_id'), 'wbs_tasks', ['user_id'], unique=False)
    op.create_table('community_placements',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tree_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('zone_index', sa.Integer(), nullable=False),
    sa.Column('row', sa.SmallInteger(), nullable=False),
    sa.Column('col', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('row BETWEEN 0 AND 5 AND col BETWEEN 0 AND 5', name=op.f('ck_community_placements_cell_range')),
    sa.ForeignKeyConstraint(['tree_id'], ['trees.id'], name=op.f('fk_community_placements_tree_id_trees'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_community_placements_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_community_placements')),
    sa.UniqueConstraint('tree_id', name='uq_community_tree'),
    sa.UniqueConstraint('zone_index', 'row', 'col', name='uq_community_cell')
    )
    op.create_index(op.f('ix_community_placements_user_id'), 'community_placements', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_community_placements_user_id'), table_name='community_placements')
    op.drop_table('community_placements')
    op.drop_index(op.f('ix_wbs_tasks_user_id'), table_name='wbs_tasks')
    op.drop_index(op.f('ix_wbs_tasks_parent_id'), table_name='wbs_tasks')
    op.drop_table('wbs_tasks')
    op.drop_index(op.f('ix_attendance_user_id'), table_name='attendance')
    op.drop_table('attendance')
    op.drop_table('study_dates')
    op.drop_table('library_networks')
    op.drop_table('app_settings')
