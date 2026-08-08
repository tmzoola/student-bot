"""add referral tables (tracked_chats, invite_links, invite_joins)

Revision ID: i6a3b18d2c05
Revises: h5f2e04c1b89
Create Date: 2026-07-23 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i6a3b18d2c05"
down_revision: Union[str, Sequence[str], None] = "h5f2e04c1b89"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tracked_chats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("username", sa.String(128), nullable=True),
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
        sa.UniqueConstraint("chat_id", name="uq_tracked_chats_chat_id"),
    )
    op.create_index("ix_tracked_chats_chat_id", "tracked_chats", ["chat_id"])
    op.create_index(
        "ix_tracked_chats_deleted_at", "tracked_chats", ["deleted_at"]
    )

    op.create_table(
        "invite_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tracked_chat_id", sa.Integer(), nullable=False),
        sa.Column("invite_link", sa.Text(), nullable=False),
        sa.Column("telegram_link_name", sa.String(64), nullable=False),
        sa.Column("join_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
            ["tracked_chat_id"], ["tracked_chats.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "tracked_chat_id", name="uq_invite_links_user_chat"
        ),
    )
    op.create_index("ix_invite_links_user_id", "invite_links", ["user_id"])
    op.create_index(
        "ix_invite_links_tracked_chat_id", "invite_links", ["tracked_chat_id"]
    )
    op.create_index(
        "ix_invite_links_deleted_at", "invite_links", ["deleted_at"]
    )

    op.create_table(
        "invite_joins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("invite_link_id", sa.Integer(), nullable=False),
        sa.Column("joined_user_tg_id", sa.BigInteger(), nullable=False),
        sa.Column("left_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_counted", sa.Boolean(), nullable=False, server_default="true"),
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
            ["invite_link_id"], ["invite_links.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "invite_link_id",
            "joined_user_tg_id",
            name="uq_invite_joins_link_user",
        ),
    )
    op.create_index(
        "ix_invite_joins_invite_link_id", "invite_joins", ["invite_link_id"]
    )
    op.create_index(
        "ix_invite_joins_joined_user_tg_id",
        "invite_joins",
        ["joined_user_tg_id"],
    )
    op.create_index(
        "ix_invite_joins_deleted_at", "invite_joins", ["deleted_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_invite_joins_deleted_at", table_name="invite_joins")
    op.drop_index(
        "ix_invite_joins_joined_user_tg_id", table_name="invite_joins"
    )
    op.drop_index(
        "ix_invite_joins_invite_link_id", table_name="invite_joins"
    )
    op.drop_table("invite_joins")

    op.drop_index("ix_invite_links_deleted_at", table_name="invite_links")
    op.drop_index(
        "ix_invite_links_tracked_chat_id", table_name="invite_links"
    )
    op.drop_index("ix_invite_links_user_id", table_name="invite_links")
    op.drop_table("invite_links")

    op.drop_index("ix_tracked_chats_deleted_at", table_name="tracked_chats")
    op.drop_index("ix_tracked_chats_chat_id", table_name="tracked_chats")
    op.drop_table("tracked_chats")
