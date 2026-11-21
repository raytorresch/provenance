"""add check constraint for chunk embedding dims

Revision ID: 9a8302d76e05
Revises: c276b487485d
Create Date: 2026-11-21 14:55:43.771190

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "9a8302d76e05"
down_revision: str | Sequence[str] | None = "c276b487485d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_chunk_embedding_dims",
        "chunk_embeddings",
        "vector_dims(embedding) = dimensions",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_chunk_embedding_dims", "chunk_embeddings", type_="check"
    )
