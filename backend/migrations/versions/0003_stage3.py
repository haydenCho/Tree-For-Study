"""3단계 스키마: 드래그 시간표 블록(15분 스냅·범위 검사), 주간 회고.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-17 22:01:05.367311
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('timetable_blocks',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('layer', sa.String(length=8), nullable=False),
    sa.Column('start_min', sa.SmallInteger(), nullable=False),
    sa.Column('end_min', sa.SmallInteger(), nullable=False),
    sa.Column('title', sa.String(length=80), nullable=False),
    sa.Column('memo', sa.String(length=500), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("layer IN ('plan', 'actual')", name=op.f('ck_timetable_blocks_layer')),
    sa.CheckConstraint('start_min % 15 = 0 AND end_min % 15 = 0', name=op.f('ck_timetable_blocks_snap')),
    sa.CheckConstraint('start_min >= 0 AND end_min <= 1440 AND end_min > start_min', name=op.f('ck_timetable_blocks_range')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_timetable_blocks_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_timetable_blocks'))
    )
    op.create_index(op.f('ix_timetable_blocks_day'), 'timetable_blocks', ['day'], unique=False)
    op.create_index(op.f('ix_timetable_blocks_user_id'), 'timetable_blocks', ['user_id'], unique=False)
    op.create_table('weekly_reviews',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('week_start', sa.Date(), nullable=False),
    sa.Column('good', sa.Text(), nullable=False),
    sa.Column('hard', sa.Text(), nullable=False),
    sa.Column('next_plan', sa.Text(), nullable=False),
    sa.Column('is_public', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_weekly_reviews_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_weekly_reviews')),
    sa.UniqueConstraint('user_id', 'week_start', name='uq_weekly_review')
    )
    op.create_index(op.f('ix_weekly_reviews_user_id'), 'weekly_reviews', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_weekly_reviews_user_id'), table_name='weekly_reviews')
    op.drop_table('weekly_reviews')
    op.drop_index(op.f('ix_timetable_blocks_user_id'), table_name='timetable_blocks')
    op.drop_index(op.f('ix_timetable_blocks_day'), table_name='timetable_blocks')
    op.drop_table('timetable_blocks')
