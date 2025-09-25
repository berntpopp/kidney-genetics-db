"""add string ppi percentiles view

Revision ID: 86bdb75bc293
Revises: fix_gene_staging_cols
Create Date: 2025-09-21 15:12:01.832277

This migration adds a view for calculating global percentiles for STRING PPI scores.
The view uses PostgreSQL's PERCENT_RANK() window function for efficient calculation.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86bdb75bc293'
down_revision: Union[str, Sequence[str], None] = 'fix_gene_staging_cols'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the STRING PPI percentiles view."""
    # Create the view using standard SQL
    op.execute("""
        CREATE OR REPLACE VIEW string_ppi_percentiles AS
        SELECT
            ga.gene_id,
            g.approved_symbol,
            CAST(ga.annotations->'ppi_score' AS FLOAT) as ppi_score,
            PERCENT_RANK() OVER (
                ORDER BY CAST(ga.annotations->'ppi_score' AS FLOAT)
            ) AS percentile_rank
        FROM gene_annotations ga
        JOIN genes g ON g.id = ga.gene_id
        WHERE ga.annotations ? 'ppi_score'
          AND ga.annotations->>'ppi_score' IS NOT NULL
          AND ga.annotations->>'ppi_score' != 'null'
          AND CAST(ga.annotations->>'ppi_score' AS FLOAT) > 0
    """)

    # Create an index on gene_annotations for better performance
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_gene_annotations_ppi_score
        ON gene_annotations ((annotations->'ppi_score'))
        WHERE annotations ? 'ppi_score'
    """)


def downgrade() -> None:
    """Drop the STRING PPI percentiles view and index."""
    # Drop the index
    op.execute("DROP INDEX IF EXISTS ix_gene_annotations_ppi_score")

    # Drop the view
    op.execute("DROP VIEW IF EXISTS string_ppi_percentiles")
