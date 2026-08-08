"""add shop (shop_settings, shop_books, book_orders)

Revision ID: h5f2e04c1b89
Revises: g4d1e95f0a23
Create Date: 2026-07-13 11:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h5f2e04c1b89"
down_revision: Union[str, Sequence[str], None] = "g4d1e95f0a23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shop_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("card_number", sa.String(32), nullable=True),
        sa.Column("card_holder", sa.String(255), nullable=True),
        sa.Column("admin_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("admin_username", sa.String(128), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    # Seed one settings row for the admin to fill in.
    op.execute("INSERT INTO shop_settings (card_number, card_holder) VALUES (NULL, NULL)")

    op.create_table(
        "shop_books",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cover_image_url", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "book_orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "confirmed", "processing", "shipped",
                    name="order_status_enum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("delivery_name", sa.String(255), nullable=True),
        sa.Column("delivery_phone", sa.String(32), nullable=True),
        sa.Column("delivery_address", sa.Text(), nullable=True),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["telegram_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["book_id"], ["shop_books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_book_orders_user_id", "book_orders", ["user_id"])
    op.create_index("ix_book_orders_book_id", "book_orders", ["book_id"])


def downgrade() -> None:
    op.drop_index("ix_book_orders_book_id", table_name="book_orders")
    op.drop_index("ix_book_orders_user_id", table_name="book_orders")
    op.drop_table("book_orders")
    op.execute("DROP TYPE IF EXISTS order_status_enum")
    op.drop_table("shop_books")
    op.drop_table("shop_settings")
