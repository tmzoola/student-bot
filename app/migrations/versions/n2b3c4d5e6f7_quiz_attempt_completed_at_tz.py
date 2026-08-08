"""quiz_attempts.completed_at -> TIMESTAMP WITH TIME ZONE (existing values treated as UTC)

Revision ID: n2b3c4d5e6f7
Revises: m1a2b3c4d5e6
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "m1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "quiz_attempts",
        "completed_at",
        existing_type=sa.DateTime(),
        type_=sa.TIMESTAMP(timezone=True),
        existing_nullable=True,
        postgresql_using="completed_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    op.alter_column(
        "quiz_attempts",
        "completed_at",
        existing_type=sa.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        postgresql_using="completed_at AT TIME ZONE 'UTC'",
    )
