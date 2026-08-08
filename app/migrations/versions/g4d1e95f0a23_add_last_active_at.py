"""add last_active_at to telegram_users

Revision ID: g4d1e95f0a23
Revises: f2a9c31d7b64
Create Date: 2026-07-13 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g4d1e95f0a23"
down_revision: Union[str, Sequence[str], None] = "b8f3a219c7d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "telegram_users",
        sa.Column("last_active_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_telegram_users_last_active_at", "telegram_users", ["last_active_at"])


def downgrade() -> None:
    op.drop_index("ix_telegram_users_last_active_at", table_name="telegram_users")
    op.drop_column("telegram_users", "last_active_at")
