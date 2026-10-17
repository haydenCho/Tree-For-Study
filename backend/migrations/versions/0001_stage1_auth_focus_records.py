"""1단계 스키마: 회원·초대·토큰 세션·감사 기록, 집중 세션·개인 숲·나무, 일일 기록·목표.

invites.created_by → users.id 외래 키는 순환 참조라 두 테이블 생성 후 따로 추가한다.

Revision ID: 0001
Revises: 
Create Date: 2026-10-17 20:34:46.386084
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('invites',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('label', sa.String(length=60), nullable=False),
    sa.Column('max_uses', sa.Integer(), nullable=False),
    sa.Column('use_count', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_invites')),
    sa.UniqueConstraint('code_hash', name=op.f('uq_invites_code_hash'))
    )
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email_normalized', sa.String(length=254), nullable=False),
    sa.Column('real_name', sa.String(length=40), nullable=False),
    sa.Column('display_name', sa.String(length=20), nullable=False),
    sa.Column('bio', sa.String(length=160), nullable=False),
    sa.Column('avatar_emoji', sa.String(length=64), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('default_focus_minutes', sa.Integer(), nullable=False),
    sa.Column('default_rest_minutes', sa.Integer(), nullable=False),
    sa.Column('invite_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("role IN ('member', 'operator')", name=op.f('ck_users_role')),
    sa.CheckConstraint("status IN ('pending', 'active', 'rejected', 'disabled')", name=op.f('ck_users_status')),
    sa.ForeignKeyConstraint(['invite_id'], ['invites.id'], name=op.f('fk_users_invite_id_invites')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email_normalized', name=op.f('uq_users_email_normalized'))
    )
    op.create_foreign_key(op.f('fk_invites_created_by_users'), 'invites', 'users', ['created_by'], ['id'])
    op.create_table('audit_events',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('actor_id', sa.Uuid(), nullable=True),
    sa.Column('action', sa.String(length=60), nullable=False),
    sa.Column('target', sa.String(length=120), nullable=False),
    sa.Column('reason', sa.String(length=300), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], name=op.f('fk_audit_events_actor_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_events'))
    )
    op.create_table('auth_token_sessions',
    sa.Column('sid', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('family_id', sa.Uuid(), nullable=False),
    sa.Column('refresh_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_auth_token_sessions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('sid', name=op.f('pk_auth_token_sessions')),
    sa.UniqueConstraint('refresh_hash', name=op.f('uq_auth_token_sessions_refresh_hash'))
    )
    op.create_index(op.f('ix_auth_token_sessions_family_id'), 'auth_token_sessions', ['family_id'], unique=False)
    op.create_index(op.f('ix_auth_token_sessions_user_id'), 'auth_token_sessions', ['user_id'], unique=False)
    op.create_table('daily_entries',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('entry_date', sa.Date(), nullable=False),
    sa.Column('plan_text', sa.Text(), nullable=False),
    sa.Column('record_text', sa.Text(), nullable=False),
    sa.Column('is_public', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_daily_entries_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_daily_entries')),
    sa.UniqueConstraint('user_id', 'entry_date', name='uq_daily_entry')
    )
    op.create_index(op.f('ix_daily_entries_user_id'), 'daily_entries', ['user_id'], unique=False)
    op.create_table('goals',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('goal_date', sa.Date(), nullable=False),
    sa.Column('title', sa.String(length=120), nullable=False),
    sa.Column('done', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('carried_from_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['carried_from_id'], ['goals.id'], name=op.f('fk_goals_carried_from_id_goals'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_goals_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_goals')),
    sa.UniqueConstraint('carried_from_id', 'goal_date', name='uq_goal_carry_target')
    )
    op.create_index(op.f('ix_goals_goal_date'), 'goals', ['goal_date'], unique=False)
    op.create_index(op.f('ix_goals_user_id'), 'goals', ['user_id'], unique=False)
    op.create_table('personal_zones',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('zone_index', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_personal_zones_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_personal_zones')),
    sa.UniqueConstraint('user_id', 'zone_index', name='uq_personal_zone')
    )
    op.create_index(op.f('ix_personal_zones_user_id'), 'personal_zones', ['user_id'], unique=False)
    op.create_table('focus_sessions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('request_id', sa.String(length=64), nullable=False),
    sa.Column('zone_id', sa.Uuid(), nullable=False),
    sa.Column('species', sa.String(length=16), nullable=False),
    sa.Column('size', sa.String(length=8), nullable=False),
    sa.Column('tree_count', sa.SmallInteger(), nullable=False),
    sa.Column('target_seconds', sa.Integer(), nullable=False),
    sa.Column('rest_seconds', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('library_at_start', sa.Boolean(), nullable=False),
    sa.Column('network_rule_version', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('accumulated_seconds', sa.Integer(), nullable=False),
    sa.Column('current_interval_started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('target_end_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('credited_seconds', sa.Integer(), nullable=False),
    sa.Column('observed_seconds', sa.Integer(), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('abandoned_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rest_started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rest_ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.CheckConstraint("size IN ('small','large')", name=op.f('ck_focus_sessions_size')),
    sa.CheckConstraint("status IN ('focusing', 'paused', 'completed', 'abandoned')", name=op.f('ck_focus_sessions_status')),
    sa.CheckConstraint('target_seconds BETWEEN 1200 AND 10800', name=op.f('ck_focus_sessions_target')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_focus_sessions_user_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['zone_id'], ['personal_zones.id'], name=op.f('fk_focus_sessions_zone_id_personal_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_focus_sessions')),
    sa.UniqueConstraint('user_id', 'request_id', name='uq_focus_request')
    )
    op.create_index('ix_focus_due', 'focus_sessions', ['status', 'target_end_at'], unique=False)
    op.create_index(op.f('ix_focus_sessions_user_id'), 'focus_sessions', ['user_id'], unique=False)
    op.create_index('uq_focus_one_active', 'focus_sessions', ['user_id'], unique=True, postgresql_where=sa.text("status IN ('focusing','paused')"))
    op.create_table('focus_intervals',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['focus_sessions.id'], name=op.f('fk_focus_intervals_session_id_focus_sessions'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_focus_intervals'))
    )
    op.create_index(op.f('ix_focus_intervals_session_id'), 'focus_intervals', ['session_id'], unique=False)
    op.create_table('session_plots',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('zone_id', sa.Uuid(), nullable=False),
    sa.Column('row', sa.SmallInteger(), nullable=False),
    sa.Column('col', sa.SmallInteger(), nullable=False),
    sa.Column('ordinal', sa.SmallInteger(), nullable=False),
    sa.CheckConstraint('row BETWEEN 0 AND 5 AND col BETWEEN 0 AND 5', name=op.f('ck_session_plots_cell_range')),
    sa.ForeignKeyConstraint(['session_id'], ['focus_sessions.id'], name=op.f('fk_session_plots_session_id_focus_sessions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_session_plots_user_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['zone_id'], ['personal_zones.id'], name=op.f('fk_session_plots_zone_id_personal_zones')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_session_plots')),
    sa.UniqueConstraint('session_id', 'ordinal', name='uq_plot_ordinal'),
    sa.UniqueConstraint('zone_id', 'row', 'col', name='uq_plot_cell')
    )
    op.create_index(op.f('ix_session_plots_session_id'), 'session_plots', ['session_id'], unique=False)
    op.create_index(op.f('ix_session_plots_user_id'), 'session_plots', ['user_id'], unique=False)
    op.create_table('trees',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('plot_id', sa.Uuid(), nullable=False),
    sa.Column('ordinal', sa.SmallInteger(), nullable=False),
    sa.Column('species', sa.String(length=16), nullable=False),
    sa.Column('size', sa.String(length=8), nullable=False),
    sa.Column('state', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("state IN ('normal', 'library', 'wilted')", name=op.f('ck_trees_state')),
    sa.ForeignKeyConstraint(['plot_id'], ['session_plots.id'], name=op.f('fk_trees_plot_id_session_plots'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['session_id'], ['focus_sessions.id'], name=op.f('fk_trees_session_id_focus_sessions'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_trees_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_trees')),
    sa.UniqueConstraint('plot_id', name='uq_tree_plot'),
    sa.UniqueConstraint('session_id', 'ordinal', name='uq_tree_session_ordinal')
    )
    op.create_index(op.f('ix_trees_session_id'), 'trees', ['session_id'], unique=False)
    op.create_index(op.f('ix_trees_user_id'), 'trees', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_trees_user_id'), table_name='trees')
    op.drop_index(op.f('ix_trees_session_id'), table_name='trees')
    op.drop_table('trees')
    op.drop_index(op.f('ix_session_plots_user_id'), table_name='session_plots')
    op.drop_index(op.f('ix_session_plots_session_id'), table_name='session_plots')
    op.drop_table('session_plots')
    op.drop_index(op.f('ix_focus_intervals_session_id'), table_name='focus_intervals')
    op.drop_table('focus_intervals')
    op.drop_index('uq_focus_one_active', table_name='focus_sessions', postgresql_where=sa.text("status IN ('focusing','paused')"))
    op.drop_index(op.f('ix_focus_sessions_user_id'), table_name='focus_sessions')
    op.drop_index('ix_focus_due', table_name='focus_sessions')
    op.drop_table('focus_sessions')
    op.drop_index(op.f('ix_personal_zones_user_id'), table_name='personal_zones')
    op.drop_table('personal_zones')
    op.drop_index(op.f('ix_goals_user_id'), table_name='goals')
    op.drop_index(op.f('ix_goals_goal_date'), table_name='goals')
    op.drop_table('goals')
    op.drop_index(op.f('ix_daily_entries_user_id'), table_name='daily_entries')
    op.drop_table('daily_entries')
    op.drop_index(op.f('ix_auth_token_sessions_user_id'), table_name='auth_token_sessions')
    op.drop_index(op.f('ix_auth_token_sessions_family_id'), table_name='auth_token_sessions')
    op.drop_table('auth_token_sessions')
    op.drop_table('audit_events')
    op.drop_constraint(op.f('fk_invites_created_by_users'), 'invites', type_='foreignkey')
    op.drop_table('users')
    op.drop_table('invites')
