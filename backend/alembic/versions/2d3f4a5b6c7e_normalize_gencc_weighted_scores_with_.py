"""Normalize GenCC weighted scores with percentile ranking

Revision ID: 2d3f4a5b6c7e
Revises: 1c0a4ff21798
Create Date: 2025-08-18 08:15:00.000000

The weighted GenCC scoring system produces scores in a narrow range (0.28-0.85)
which doesn't utilize the full 0-1 scale. This migration adds percentile
normalization to spread GenCC scores across the full range, making them
comparable to other evidence sources.

This ensures that the best GenCC genes (like DPAGT1 with 2x Definitive) 
score 1.0, and scores are distributed properly across the full range.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2d3f4a5b6c7e'
down_revision: Union[str, Sequence[str], None] = '1c0a4ff21798'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add percentile normalization to GenCC weighted scores."""
    
    # Drop dependent views first (in reverse dependency order)
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_normalized_scores CASCADE")
    
    # Create new view that applies percentile normalization to GenCC scores
    op.execute("""
        CREATE OR REPLACE VIEW evidence_normalized_scores AS
        WITH gencc_percentiles AS (
            SELECT
                evidence_id,
                gene_id,
                approved_symbol,
                source_name,
                classification_weight,
                -- Apply percentile ranking to spread scores across 0-1 range
                PERCENT_RANK() OVER (
                    ORDER BY classification_weight
                ) as percentile_score
            FROM evidence_classification_weights
            WHERE source_name = 'GenCC'
        )
        -- Count-based sources (percentile normalization)
        SELECT
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            percentile_score as normalized_score
        FROM evidence_count_percentiles
        
        UNION ALL
        
        -- ClinGen (direct weight mapping, already 0-1 range)
        SELECT
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            classification_weight as normalized_score
        FROM evidence_classification_weights
        WHERE source_name = 'ClinGen'
        
        UNION ALL
        
        -- GenCC (percentile normalization of weighted scores)
        SELECT
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            percentile_score as normalized_score
        FROM gencc_percentiles
    """)
    
    # Recreate gene_scores (unchanged, but needed for dependencies)
    op.execute("""
        CREATE OR REPLACE VIEW gene_scores AS
        WITH active_sources AS (
            SELECT COUNT(DISTINCT source_name) as total_count
            FROM gene_evidence
        ),
        gene_source_scores AS (
            SELECT
                g.id as gene_id,
                g.approved_symbol,
                g.hgnc_id,
                COUNT(DISTINCT ens.source_name) as source_count,
                COUNT(ens.*) as evidence_count,
                COALESCE(SUM(ens.normalized_score), 0) as raw_score,
                jsonb_object_agg(
                    ens.source_name,
                    ROUND(ens.normalized_score::numeric, 3)
                ) FILTER (WHERE ens.source_name IS NOT NULL) as source_scores
            FROM genes g
            LEFT JOIN evidence_normalized_scores ens ON g.id = ens.gene_id
            GROUP BY g.id, g.approved_symbol, g.hgnc_id
        )
        SELECT
            gss.gene_id,
            gss.approved_symbol,
            gss.hgnc_id,
            gss.source_count,
            gss.evidence_count,
            gss.raw_score,
            -- Divide by total active sources in system, not evidence count
            CASE
                WHEN ac.total_count > 0 THEN
                    ROUND((gss.raw_score / ac.total_count * 100)::numeric, 2)
                ELSE 0
            END as percentage_score,
            ac.total_count as total_active_sources,
            COALESCE(gss.source_scores, '{}'::jsonb) as source_scores
        FROM gene_source_scores gss
        CROSS JOIN active_sources ac
        ORDER BY percentage_score DESC NULLS LAST, gss.approved_symbol
    """)


def downgrade() -> None:
    """Revert to non-normalized GenCC scores."""
    
    # Drop dependent views first
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_normalized_scores CASCADE")
    
    # Recreate without percentile normalization for GenCC
    op.execute("""
        CREATE OR REPLACE VIEW evidence_normalized_scores AS
        -- Count-based sources (percentile normalization)
        SELECT
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            percentile_score as normalized_score
        FROM evidence_count_percentiles
        
        UNION ALL
        
        -- Classification-based sources (weight mapping with new GenCC weights)
        SELECT
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            classification_weight as normalized_score
        FROM evidence_classification_weights
    """)
    
    # Recreate gene_scores
    op.execute("""
        CREATE OR REPLACE VIEW gene_scores AS
        WITH active_sources AS (
            SELECT COUNT(DISTINCT source_name) as total_count
            FROM gene_evidence
        ),
        gene_source_scores AS (
            SELECT
                g.id as gene_id,
                g.approved_symbol,
                g.hgnc_id,
                COUNT(DISTINCT ens.source_name) as source_count,
                COUNT(ens.*) as evidence_count,
                COALESCE(SUM(ens.normalized_score), 0) as raw_score,
                jsonb_object_agg(
                    ens.source_name,
                    ROUND(ens.normalized_score::numeric, 3)
                ) FILTER (WHERE ens.source_name IS NOT NULL) as source_scores
            FROM genes g
            LEFT JOIN evidence_normalized_scores ens ON g.id = ens.gene_id
            GROUP BY g.id, g.approved_symbol, g.hgnc_id
        )
        SELECT
            gss.gene_id,
            gss.approved_symbol,
            gss.hgnc_id,
            gss.source_count,
            gss.evidence_count,
            gss.raw_score,
            -- Divide by total active sources in system, not evidence count
            CASE
                WHEN ac.total_count > 0 THEN
                    ROUND((gss.raw_score / ac.total_count * 100)::numeric, 2)
                ELSE 0
            END as percentage_score,
            ac.total_count as total_active_sources,
            COALESCE(gss.source_scores, '{}'::jsonb) as source_scores
        FROM gene_source_scores gss
        CROSS JOIN active_sources ac
        ORDER BY percentage_score DESC NULLS LAST, gss.approved_symbol
    """)