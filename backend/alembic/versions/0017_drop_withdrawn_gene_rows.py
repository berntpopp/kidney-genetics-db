"""Drop the ACMG and IV gene rows (withdrawn HGNC entries from panel scraping)

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-30

Lab pages contain the words "ACMG" and "IV"; the old HGNC free-text lookup
resolved them to withdrawn entries (HGNC:116, HGNC:6185) and created genes.
Since 0.20.0 only approved symbols resolve and the re-upload removed their
evidence, leaving empty rows. Only these exact rows go, and only while they
have no evidence or curated associations; elsewhere it is a no-op.
"""

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

TARGET = """
    SELECT id FROM genes g
    WHERE (approved_symbol, hgnc_id) IN (('ACMG', 'HGNC:116'), ('IV', 'HGNC:6185'))
        AND NOT EXISTS (SELECT 1 FROM gene_evidence e WHERE e.gene_id = g.id)
        AND NOT EXISTS (SELECT 1 FROM gene_disease_associations a WHERE a.gene_id = g.id)
"""


def upgrade() -> None:
    # gene_annotations cascade; these two tables reference genes without ON DELETE.
    op.execute(f"DELETE FROM gene_curations WHERE gene_id IN ({TARGET})")
    op.execute(f"DELETE FROM annotation_history WHERE gene_id IN ({TARGET})")
    op.execute(f"DELETE FROM genes WHERE id IN ({TARGET})")


def downgrade() -> None:
    # No-op: recreating rows for withdrawn symbols would reintroduce the bug.
    pass
