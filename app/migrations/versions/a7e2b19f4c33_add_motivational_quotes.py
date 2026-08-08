"""add_motivational_quotes

Revision ID: a7e2b19f4c33
Revises: d4c8ef91a7b2
Create Date: 2026-07-07 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7e2b19f4c33'
down_revision: Union[str, Sequence[str], None] = 'd4c8ef91a7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'motivational_quotes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("TIMEZONE('Asia/Tashkent', now())"), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_motivational_quotes_deleted_at'), 'motivational_quotes', ['deleted_at'], unique=False)

    # Seed a few starter quotes
    op.execute("""
        INSERT INTO motivational_quotes (text, is_active) VALUES
        ('Bugun ham o''zingizga ishoning. Mashqda qiyin bo''lsa, jangda oson bo''ladi.', true),
        ('Natija — bu mehnatingiz mahsuli. Har bir savol sizni yaqinlashtiradi.', true),
        ('Kichik qadamlar katta yutuqlarga olib boradi. Bir kun ham tashlab qo''ymang.', true),
        ('Bilimingiz — sizning eng katta boyligingiz. Uni har kuni orttiring.', true),
        ('Xato qilish — o''rganishning bir qismi. Muhimi — davom eting.', true),
        ('Bugun qiyin bo''lsa, ertaga oson bo''ladi. Sabr va mehnat — kalitingiz.', true),
        ('Har bir yechilgan test — kelajagingizga qo''yilgan g''isht.', true);
    """)


def downgrade() -> None:
    op.drop_index(op.f('ix_motivational_quotes_deleted_at'), table_name='motivational_quotes')
    op.drop_table('motivational_quotes')
