"""add menu_settings (reply keyboard tugmalarini yoqish/o'chirish)

Revision ID: q5e6f8a9b0c1
Revises: p4d5e6f8a9b0
Create Date: 2026-07-28 09:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "q5e6f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "p4d5e6f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "menu_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("show_test", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("show_books", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("show_info", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("show_referral", sa.Boolean(), nullable=False, server_default="true"),
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
    # Singleton — bitta standart qator (hammasi yoqilgan).
    op.execute(
        "INSERT INTO menu_settings (show_test, show_books, show_info, show_referral) "
        "VALUES (true, true, true, true)"
    )


def downgrade() -> None:
    op.drop_table("menu_settings")
