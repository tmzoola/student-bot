"""bosqich 2 — deadline eslatmalari

Revision ID: 3a7f91b2c04e
Revises: 24a1237ca0fc
Create Date: 2026-08-11 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "3a7f91b2c04e"
down_revision: Union[str, None] = "24a1237ca0fc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deadlines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deadline_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("faculty_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("createdAt", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculties.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deadlines_faculty_id", "deadlines", ["faculty_id"])

    op.create_table(
        "deadline_sent",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("deadline_id", sa.Integer(), nullable=False),
        sa.Column("student_profile_id", sa.Integer(), nullable=False),
        sa.Column("remind_type", sa.String(10), nullable=False),
        sa.Column("createdAt", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["deadline_id"], ["deadlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_profile_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deadline_id", "student_profile_id", "remind_type", name="uq_deadline_sent"),
    )
    op.create_index("ix_deadline_sent_deadline_id", "deadline_sent", ["deadline_id"])
    op.create_index("ix_deadline_sent_student_profile_id", "deadline_sent", ["student_profile_id"])

    op.create_table(
        "personal_deadlines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("student_profile_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("deadline_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("reminded_24h", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("reminded_2h", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("createdAt", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updatedAt", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_profile_id"], ["student_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_personal_deadlines_student_profile_id", "personal_deadlines", ["student_profile_id"])


def downgrade() -> None:
    op.drop_table("personal_deadlines")
    op.drop_table("deadline_sent")
    op.drop_table("deadlines")
