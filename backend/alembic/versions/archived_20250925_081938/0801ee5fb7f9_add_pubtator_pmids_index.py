"""Add GIN index for PubTator PMIDs lookup optimization

Revision ID: 0801ee5fb7f9
Revises: 98531cf3dc79
Create Date: 2025-08-31 16:52:01.331209

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0801ee5fb7f9'
down_revision: str | Sequence[str] | None = '98531cf3dc79'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add GIN index for fast PMID lookups in PubTator evidence."""
    # Add GIN index for fast PMID lookups in PubTator evidence
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gene_evidence_pubtator_pmids
        ON gene_evidence USING GIN ((evidence_data->'pmids'))
        WHERE source_name = 'PubTator'
    """)


def downgrade() -> None:
    """Remove the GIN index."""
    # Remove the index
    op.execute("DROP INDEX IF EXISTS idx_gene_evidence_pubtator_pmids")
