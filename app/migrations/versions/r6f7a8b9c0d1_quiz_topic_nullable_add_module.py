"""quiz.topic_id nullable + quiz.module_id (mavzu bosqichini o'tkazib yuborish uchun)

Revision ID: r6f7a8b9c0d1
Revises: q5e6f8a9b0c1
Create Date: 2026-07-28 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "r6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "q5e6f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. quizzes.topic_id — nullable
    op.alter_column(
        "quizzes",
        "topic_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    # Eski ondelete=CASCADE ni ondelete=SET NULL bilan almashtiramiz
    op.drop_constraint("quizzes_topic_id_fkey", "quizzes", type_="foreignkey")
    op.create_foreign_key(
        "quizzes_topic_id_fkey",
        "quizzes",
        "topics",
        ["topic_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 2. quizzes.module_id — yangi nullable FK
    op.add_column(
        "quizzes",
        sa.Column("module_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_quizzes_module_id", "quizzes", ["module_id"])
    op.create_foreign_key(
        "quizzes_module_id_fkey",
        "quizzes",
        "modules",
        ["module_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3. Backfill: mavjud quizlarga topic orqali module_id ni to'ldiramiz
    op.execute(
        "UPDATE quizzes q SET module_id = t.module_id "
        "FROM topics t WHERE q.topic_id = t.id AND q.module_id IS NULL"
    )


def downgrade() -> None:
    op.drop_constraint("quizzes_module_id_fkey", "quizzes", type_="foreignkey")
    op.drop_index("ix_quizzes_module_id", table_name="quizzes")
    op.drop_column("quizzes", "module_id")

    op.drop_constraint("quizzes_topic_id_fkey", "quizzes", type_="foreignkey")
    op.execute("UPDATE quizzes SET topic_id = 0 WHERE topic_id IS NULL")
    op.alter_column(
        "quizzes",
        "topic_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.create_foreign_key(
        "quizzes_topic_id_fkey",
        "quizzes",
        "topics",
        ["topic_id"],
        ["id"],
        ondelete="CASCADE",
    )
