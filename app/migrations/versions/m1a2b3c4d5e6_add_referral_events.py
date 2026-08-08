"""add referral events (referral_events, referral_event_participants) + tracked_chats.invite_url

Revision ID: m1a2b3c4d5e6
Revises: l9d6e4bf8f32
Create Date: 2026-07-24 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "m1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "l9d6e4bf8f32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tracked_chats",
        sa.Column("invite_url", sa.String(255), nullable=True),
    )

    op.create_table(
        "referral_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("announcement_text", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("success_text", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ends_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
    )
    op.create_index(
        "ix_referral_events_deleted_at", "referral_events", ["deleted_at"]
    )

    op.create_table(
        "referral_event_participants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
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
            ["user_id"], ["telegram_users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id", "user_id", name="uq_event_participants_event_user"
        ),
        sa.UniqueConstraint(
            "event_id", "number", name="uq_event_participants_event_number"
        ),
    )
    op.create_index(
        "ix_referral_event_participants_event_id",
        "referral_event_participants",
        ["event_id"],
    )
    op.create_index(
        "ix_referral_event_participants_user_id",
        "referral_event_participants",
        ["user_id"],
    )
    op.create_index(
        "ix_referral_event_participants_deleted_at",
        "referral_event_participants",
        ["deleted_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_referral_event_participants_deleted_at",
        table_name="referral_event_participants",
    )
    op.drop_index(
        "ix_referral_event_participants_user_id",
        table_name="referral_event_participants",
    )
    op.drop_index(
        "ix_referral_event_participants_event_id",
        table_name="referral_event_participants",
    )
    op.drop_table("referral_event_participants")

    op.drop_index("ix_referral_events_deleted_at", table_name="referral_events")
    op.drop_table("referral_events")

    op.drop_column("tracked_chats", "invite_url")
