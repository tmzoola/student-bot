"""add_phone_to_users

Revision ID: b7a1e2c9d312
Revises: a93d80a9d75d
Create Date: 2026-07-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7a1e2c9d312'
down_revision: Union[str, Sequence[str], None] = 'c4f8a21d9b3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('telegram_users', sa.Column('phone', sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column('telegram_users', 'phone')
