"""add referral rewards (reward_tiers, user_rewards)

Revision ID: j7b4c29e5d16
Revises: i6a3b18d2c05
Create Date: 2026-07-24 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j7b4c29e5d16"
down_revision: Union[str, Sequence[str], None] = "i6a3b18d2c05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reward_tiers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("required_invites", sa.Integer(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column("image_url", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "required_invites", name="uq_reward_tiers_required_invites"
        ),
    )
    op.create_index(
        "ix_reward_tiers_required_invites",
        "reward_tiers",
        ["required_invites"],
    )
    op.create_index(
        "ix_reward_tiers_deleted_at", "reward_tiers", ["deleted_at"]
    )

    op.create_table(
        "user_rewards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reward_tier_id", sa.Integer(), nullable=False),
        sa.Column(
            "earned_at", sa.TIMESTAMP(timezone=True), nullable=False
        ),
        sa.Column(
            "claimed_at", sa.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("note", sa.Text(), nullable=True),
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
            ["user_id"], ["telegram_users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reward_tier_id"], ["reward_tiers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "reward_tier_id", name="uq_user_rewards_user_tier"
        ),
    )
    op.create_index("ix_user_rewards_user_id", "user_rewards", ["user_id"])
    op.create_index(
        "ix_user_rewards_reward_tier_id", "user_rewards", ["reward_tier_id"]
    )
    op.create_index(
        "ix_user_rewards_deleted_at", "user_rewards", ["deleted_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_user_rewards_deleted_at", table_name="user_rewards")
    op.drop_index(
        "ix_user_rewards_reward_tier_id", table_name="user_rewards"
    )
    op.drop_index("ix_user_rewards_user_id", table_name="user_rewards")
    op.drop_table("user_rewards")

    op.drop_index("ix_reward_tiers_deleted_at", table_name="reward_tiers")
    op.drop_index(
        "ix_reward_tiers_required_invites", table_name="reward_tiers"
    )
    op.drop_table("reward_tiers")
