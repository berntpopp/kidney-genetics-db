"""fix evidence unique constraint to gene and source only

Revision ID: 1e0dd188d993
Revises: 001_initial_complete
Create Date: 2025-08-18 06:46:11.743301

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1e0dd188d993'
down_revision: str | Sequence[str] | None = '001_initial_complete'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    """
    Fix the evidence unique constraint to enforce ONE evidence record per source per gene.
    This involves:
    1. Dropping the old constraint that included source_detail
    2. Merging duplicate evidence records (keeping the most recent)
    3. Creating new constraint with just (gene_id, source_name)
    """

    # First, merge duplicate evidence records
    # For each gene+source combination, keep only the most recent evidence
    op.execute("""
        -- Create a temporary table with the evidence records to keep
        CREATE TEMP TABLE evidence_to_keep AS
        SELECT DISTINCT ON (gene_id, source_name)
            id,
            gene_id,
            source_name,
            source_detail,
            evidence_data,
            evidence_date,
            created_at,
            updated_at
        FROM gene_evidence
        ORDER BY gene_id, source_name, evidence_date DESC, updated_at DESC, id DESC;

        -- Delete all evidence records not in the keep list
        DELETE FROM gene_evidence
        WHERE id NOT IN (SELECT id FROM evidence_to_keep);

        -- Drop the temporary table
        DROP TABLE evidence_to_keep;
    """)

    # Drop the old unique constraint
    op.drop_constraint('gene_evidence_source_idx', 'gene_evidence', type_='unique')

    # Create the new unique constraint with just gene_id and source_name
    op.create_unique_constraint(
        'gene_evidence_source_idx',
        'gene_evidence',
        ['gene_id', 'source_name']
    )

    print("✅ Fixed evidence constraint - removed duplicates and enforced one evidence per source per gene")

def downgrade() -> None:
    """
    Revert to the old constraint that included source_detail.
    Note: This won't restore the deleted duplicate records.
    """

    # Drop the new constraint
    op.drop_constraint('gene_evidence_source_idx', 'gene_evidence', type_='unique')

    # Recreate the old constraint with source_detail
    op.create_unique_constraint(
        'gene_evidence_source_idx',
        'gene_evidence',
        ['gene_id', 'source_name', 'source_detail']
    )
