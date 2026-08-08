"""add invite_join anti-fraud fields (pending_until, reject_reason)

Revision ID: k8c5d3af7e21
Revises: j7b4c29e5d16
Create Date: 2026-07-24 12:00:00.000000

T-022 · Referral anti-fraud MVP. `pending_until` — grace period tugash
vaqti (NULL = yakuniy holatda). `reject_reason` — rad etilish sababi
(masalan `new_account`, `already_member`, `quick_leave`, `self_invite`).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k8c5d3af7e21"
down_revision: Union[str, Sequence[str], None] = "j7b4c29e5d16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invite_joins",
        sa.Column(
            "pending_until", sa.TIMESTAMP(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "invite_joins",
        sa.Column("reject_reason", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_invite_joins_pending_until",
        "invite_joins",
        ["pending_until"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_invite_joins_pending_until", table_name="invite_joins"
    )
    op.drop_column("invite_joins", "reject_reason")
    op.drop_column("invite_joins", "pending_until")
