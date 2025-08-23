"""fix_unique_constraint_add_source_detail

Revision ID: a3f40460739f
Revises: d8e9f1a2b3c4
Create Date: 2025-08-22 16:40:25.108984

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a3f40460739f'
down_revision: str | Sequence[str] | None = 'd8e9f1a2b3c4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Fix unique constraint to include source_detail for multi-provider aggregation."""
    # Drop existing constraint
    op.drop_constraint('gene_evidence_source_idx', 'gene_evidence', type_='unique')

    # Create new constraint with source_detail included
    op.create_unique_constraint(
        'gene_evidence_source_idx',
        'gene_evidence',
        ['gene_id', 'source_name', 'source_detail']
    )


def downgrade() -> None:
    """Revert unique constraint to exclude source_detail."""
    # Drop new constraint
    op.drop_constraint('gene_evidence_source_idx', 'gene_evidence', type_='unique')

    # Create old constraint without source_detail
    op.create_unique_constraint(
        'gene_evidence_source_idx',
        'gene_evidence',
        ['gene_id', 'source_name']
    )
