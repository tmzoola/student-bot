"""add_user_ban

Revision ID: f2a9c31d7b64
Revises: e5b1c72a4f90
Create Date: 2026-07-07 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2a9c31d7b64'
down_revision: Union[str, Sequence[str], None] = 'e5b1c72a4f90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'telegram_users',
        sa.Column('is_banned', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('telegram_users', 'is_banned')
