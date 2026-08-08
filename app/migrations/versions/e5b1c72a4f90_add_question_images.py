"""add_question_images

Revision ID: e5b1c72a4f90
Revises: a7e2b19f4c33
Create Date: 2026-07-07 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5b1c72a4f90'
down_revision: Union[str, Sequence[str], None] = 'a7e2b19f4c33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Questions: image support + optional text
    op.add_column('questions', sa.Column('image_url', sa.String(length=512), nullable=True))
    op.alter_column('questions', 'text', existing_type=sa.Text(), nullable=True)

    # Contest questions: same
    op.add_column('contest_questions', sa.Column('image_url', sa.String(length=512), nullable=True))
    op.alter_column('contest_questions', 'text', existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.alter_column('contest_questions', 'text', existing_type=sa.Text(), nullable=False)
    op.drop_column('contest_questions', 'image_url')

    op.alter_column('questions', 'text', existing_type=sa.Text(), nullable=False)
    op.drop_column('questions', 'image_url')
