"""add missing indexes for cache and evidence tables

Revision ID: 0834f2555442
Revises: 2c3fbf63d000
Create Date: 2026-03-13 22:45:55.643498

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '0834f2555442'
down_revision: Union[str, Sequence[str], None] = '2c3fbf63d000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use raw SQL with IF NOT EXISTS to handle indexes that may already exist
    op.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_cache_entries_key_expires "
            "ON cache_entries (cache_key, expires_at)"
        )
    )
    op.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_gene_evidence_gene_source "
            "ON gene_evidence (gene_id, source_name)"
        )
    )
    op.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_cache_entries_namespace "
            "ON cache_entries (namespace)"
        )
    )


def downgrade() -> None:
    op.drop_index("idx_cache_entries_namespace", table_name="cache_entries")
    op.drop_index("idx_gene_evidence_gene_source", table_name="gene_evidence")
    op.drop_index("idx_cache_entries_key_expires", table_name="cache_entries")
