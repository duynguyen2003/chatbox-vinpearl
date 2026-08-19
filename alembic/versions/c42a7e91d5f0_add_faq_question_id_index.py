"""add FAQ question/id index

Revision ID: c42a7e91d5f0
Revises: b71d4c9e20fa
Create Date: 2026-08-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c42a7e91d5f0"
down_revision: str | Sequence[str] | None = "b71d4c9e20fa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_faq_question_id",
        "faq",
        ["question", "id"],
        unique=False,
        schema="core",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_faq_question_id",
        table_name="faq",
        schema="core",
    )
