"""Fix evidence scoring formula - divide by total sources not evidence count

Revision ID: c6a336ffa682
Revises: eb908f8d6701
Create Date: 2025-08-16 17:57:52.350575

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6a336ffa682'
down_revision: Union[str, Sequence[str], None] = 'eb908f8d6701'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix evidence scoring formula to divide by total_active_sources instead of evidence_count.
    
    CORRECT FORMULA: (raw_score / total_active_sources) * 100
    WRONG FORMULA:   (raw_score / evidence_count) * 100
    
    This ensures genes with evidence from 1 source get proper normalization:
    - CYP24A1: 0.939 / 4 * 100 = 23.48% (not 93.91%)
    """
    
    # Drop and recreate the gene_scores view with correct formula
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE;")
    
    op.execute("""
    CREATE OR REPLACE VIEW gene_scores AS
    SELECT 
        g.id AS gene_id,
        g.approved_symbol,
        g.hgnc_id,
        COUNT(DISTINCT ens.source_name) AS source_count,
        COUNT(ens.*) AS evidence_count,
        -- Raw score: sum of normalized scores (0 to N where N = source count)
        COALESCE(SUM(ens.normalized_score), 0) AS raw_score,
        -- FIXED FORMULA: Percentage score = (sum of normalized scores / TOTAL_ACTIVE_SOURCES) * 100
        CASE 
            WHEN (SELECT COUNT(DISTINCT source_name) FROM gene_evidence) > 0 THEN
                ROUND((COALESCE(SUM(ens.normalized_score), 0) / 
                      (SELECT COUNT(DISTINCT source_name) FROM gene_evidence) * 100)::numeric, 2)
            ELSE 0
        END AS percentage_score,
        -- Total active sources in system
        (SELECT COUNT(DISTINCT source_name) FROM gene_evidence) AS total_active_sources,
        -- Source breakdown for debugging
        jsonb_object_agg(
            ens.source_name, 
            ens.normalized_score
        ) AS source_percentiles
    FROM genes g
    LEFT JOIN evidence_normalized_scores ens ON g.id = ens.gene_id
    GROUP BY g.id, g.approved_symbol, g.hgnc_id
    ORDER BY percentage_score DESC NULLS LAST, g.approved_symbol;
    """)


def downgrade() -> None:
    """Revert to the broken scoring formula (divide by evidence_count)."""
    
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE;")
    
    op.execute("""
    CREATE OR REPLACE VIEW gene_scores AS
    SELECT 
        g.id AS gene_id,
        g.approved_symbol,
        g.hgnc_id,
        COUNT(DISTINCT ens.source_name) AS source_count,
        COUNT(ens.*) AS evidence_count,
        COALESCE(SUM(ens.normalized_score), 0) AS raw_score,
        -- BROKEN FORMULA: divide by evidence_count instead of total_active_sources
        CASE 
            WHEN COUNT(ens.*) > 0 THEN
                ROUND((COALESCE(SUM(ens.normalized_score), 0) / COUNT(ens.*) * 100)::numeric, 2)
            ELSE 0
        END AS percentage_score,
        (SELECT COUNT(DISTINCT source_name) FROM gene_evidence) AS total_active_sources,
        jsonb_object_agg(ens.source_name, ens.normalized_score) AS source_percentiles
    FROM genes g
    LEFT JOIN evidence_normalized_scores ens ON g.id = ens.gene_id
    GROUP BY g.id, g.approved_symbol, g.hgnc_id
    ORDER BY percentage_score DESC NULLS LAST, g.approved_symbol;
    """)
