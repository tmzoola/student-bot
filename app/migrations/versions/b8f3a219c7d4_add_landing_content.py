"""add_landing_content

Revision ID: b8f3a219c7d4
Revises: f2a9c31d7b64
Create Date: 2026-07-07 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8f3a219c7d4'
down_revision: Union[str, Sequence[str], None] = 'f2a9c31d7b64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'landing_content',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('badge_text', sa.String(length=200), nullable=False),
        sa.Column('hero_title_before', sa.String(length=200), nullable=False),
        sa.Column('hero_title_highlight', sa.String(length=100), nullable=False),
        sa.Column('hero_title_after', sa.String(length=200), nullable=False),
        sa.Column('hero_subtitle', sa.Text(), nullable=False),
        sa.Column('primary_btn_label', sa.String(length=100), nullable=False),
        sa.Column('secondary_btn_label', sa.String(length=100), nullable=False),
        sa.Column('daily_title', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_landing_content_deleted_at'), 'landing_content', ['deleted_at'], unique=False)

    op.execute("""
        INSERT INTO landing_content (
            badge_text, hero_title_before, hero_title_highlight, hero_title_after,
            hero_subtitle, primary_btn_label, secondary_btn_label, daily_title
        ) VALUES (
            'Har kuni yangi savollar · bepul',
            'Har kuni oz-ozdan,',
            'test',
            'bilan o''sing',
            'Muslima Darmonova — pedagoglar uchun tayyorgarlik platformasi: mavzulashtirilgan testlar, kunlik challenge, xatolar tahlili va umumiy reyting. Hammasi Telegram ichida.',
            'Boshlash',
            'Qanday ishlaydi?',
            'Bugungi kunlik test'
        );
    """)


def downgrade() -> None:
    op.drop_index(op.f('ix_landing_content_deleted_at'), table_name='landing_content')
    op.drop_table('landing_content')
