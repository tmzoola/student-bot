"""add referral_events.share_text (separate "Ulashish matni")

Revision ID: p4d5e6f8a9b0
Revises: o3c4d5e6f8a9
Create Date: 2026-07-27 13:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "p4d5e6f8a9b0"
down_revision: Union[str, Sequence[str], None] = "o3c4d5e6f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "referral_events",
        sa.Column("share_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("referral_events", "share_text")
