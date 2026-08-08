"""add_contests

Revision ID: d4c8ef91a7b2
Revises: b7a1e2c9d312
Create Date: 2026-07-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd4c8ef91a7b2'
down_revision: Union[str, Sequence[str], None] = 'b7a1e2c9d312'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'contests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('prize', sa.String(length=255), nullable=True),
        sa.Column('start_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('end_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('time_limit_seconds', sa.Integer(), nullable=False, server_default='3000'),
        sa.Column('question_count', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_contests_deleted_at'), 'contests', ['deleted_at'], unique=False)

    op.create_table(
        'contest_questions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('contest_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('option_a', sa.String(length=512), nullable=False),
        sa.Column('option_b', sa.String(length=512), nullable=False),
        sa.Column('option_c', sa.String(length=512), nullable=False),
        sa.Column('option_d', sa.String(length=512), nullable=False),
        sa.Column(
            'correct_option',
            postgresql.ENUM('A', 'B', 'C', 'D', name='correct_option_enum', create_type=False),
            nullable=False,
        ),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['contest_id'], ['contests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_contest_questions_deleted_at'), 'contest_questions', ['deleted_at'], unique=False)

    op.create_table(
        'contest_attempts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('contest_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('time_taken_seconds', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('answers', sa.JSON(), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['telegram_users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contest_id'], ['contests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'contest_id', name='uq_contest_attempt_user'),
    )
    op.create_index(op.f('ix_contest_attempts_deleted_at'), 'contest_attempts', ['deleted_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_contest_attempts_deleted_at'), table_name='contest_attempts')
    op.drop_table('contest_attempts')
    op.drop_index(op.f('ix_contest_questions_deleted_at'), table_name='contest_questions')
    op.drop_table('contest_questions')
    op.drop_index(op.f('ix_contests_deleted_at'), table_name='contests')
    op.drop_table('contests')
