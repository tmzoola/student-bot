"""add invite_join joined_username and joined_full_name

Revision ID: l9d6e4bf8f32
Revises: k8c5d3af7e21
Create Date: 2026-07-24 13:00:00.000000

Admin panel "Referral: qo'shilishlar" ro'yxatida qo'shilgan foydalanuvchini
telegram_id'dan tashqari username va ism-familiya bo'yicha ham identifikatsiya
qilish uchun ikkita nullable ustun qo'shiladi. Mavjud yozuvlar ta'sirlanmaydi.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "l9d6e4bf8f32"
down_revision: Union[str, Sequence[str], None] = "k8c5d3af7e21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invite_joins",
        sa.Column("joined_username", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "invite_joins",
        sa.Column("joined_full_name", sa.String(length=256), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invite_joins", "joined_full_name")
    op.drop_column("invite_joins", "joined_username")
