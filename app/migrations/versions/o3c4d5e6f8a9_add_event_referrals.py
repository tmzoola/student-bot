"""add event_referrals (bot deep-link referral counting)

Revision ID: o3c4d5e6f8a9
Revises: n2b3c4d5e6f7
Create Date: 2026-07-27 12:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "o3c4d5e6f8a9"
down_revision: Union[str, Sequence[str], None] = "n2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_referrals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("inviter_user_id", sa.Integer(), nullable=False),
        sa.Column("invited_tg_id", sa.BigInteger(), nullable=False),
        sa.Column("invited_user_id", sa.Integer(), nullable=True),
        sa.Column("counted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["event_id"], ["referral_events.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["inviter_user_id"], ["telegram_users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["invited_user_id"], ["telegram_users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id", "invited_tg_id", name="uq_event_referrals_event_invited"
        ),
    )
    op.create_index("ix_event_referrals_event_id", "event_referrals", ["event_id"])
    op.create_index(
        "ix_event_referrals_inviter_user_id", "event_referrals", ["inviter_user_id"]
    )
    op.create_index(
        "ix_event_referrals_invited_tg_id", "event_referrals", ["invited_tg_id"]
    )
    op.create_index(
        "ix_event_referrals_deleted_at", "event_referrals", ["deleted_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_event_referrals_deleted_at", table_name="event_referrals")
    op.drop_index("ix_event_referrals_invited_tg_id", table_name="event_referrals")
    op.drop_index(
        "ix_event_referrals_inviter_user_id", table_name="event_referrals"
    )
    op.drop_index("ix_event_referrals_event_id", table_name="event_referrals")
    op.drop_table("event_referrals")
