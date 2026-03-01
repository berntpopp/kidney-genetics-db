"""add functional index on upper approved_symbol

Adds a functional index on UPPER(approved_symbol) for the genes table
to accelerate case-insensitive gene symbol lookups used throughout
the annotation pipeline.

Revision ID: a1b2c3d4e5f6
Revises: 21d650ef9500
Create Date: 2026-03-01 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "21d650ef9500"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add functional index on UPPER(approved_symbol) for case-insensitive lookups."""
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_gene_symbol_upper "
        "ON genes (UPPER(approved_symbol))"
    )


def downgrade() -> None:
    """Remove functional index."""
    op.execute("DROP INDEX IF EXISTS idx_gene_symbol_upper")
