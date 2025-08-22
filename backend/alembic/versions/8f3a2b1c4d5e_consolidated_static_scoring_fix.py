"""consolidated_static_scoring_fix

Revision ID: 8f3a2b1c4d5e
Revises: d590ddf8b389
Create Date: 2025-08-22

This migration consolidates all static scoring fixes into a single canonical version.
Uses the correct internal naming pattern (static_{source_id}) for database storage
while maintaining display names for user-facing presentation.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8f3a2b1c4d5e'
down_revision: str | None = 'd590ddf8b389'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Implement consolidated static scoring with proper internal naming"""
    
    # First, update any existing evidence to use the correct internal naming pattern
    # This handles evidence that might have been created with old patterns
    op.execute("""
        UPDATE gene_evidence ge
        SET source_name = 'static_' || ss.id
        FROM static_sources ss
        WHERE (
            ge.source_name = ss.display_name
            OR ge.source_name = ss.source_name
            OR ge.source_name = 'ingested_' || ss.id::text
        )
        AND ss.is_active = true;
    """)
    
    # Drop existing views to recreate them properly
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS combined_evidence_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS static_evidence_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS static_evidence_counts CASCADE")
    
    # Create static evidence counts view - uses internal naming pattern
    op.execute("""
        CREATE VIEW static_evidence_counts AS
        SELECT 
            ge.id as evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            ss.id as source_id,
            ss.display_name as source_display_name,
            CASE
                WHEN ss.scoring_metadata->>'field' IS NOT NULL 
                     AND ge.evidence_data ? (ss.scoring_metadata->>'field') THEN
                    jsonb_array_length(ge.evidence_data -> (ss.scoring_metadata->>'field'))
                ELSE 1
            END as source_count
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        JOIN static_sources ss ON ge.source_name = 'static_' || ss.id::text
        WHERE ss.is_active = true;
    """)
    
    # Create static evidence scores view - uses internal naming pattern
    op.execute("""
        CREATE VIEW static_evidence_scores AS
        SELECT
            ge.id AS evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            ss.display_name as source_display_name,
            CASE
                -- Count-based scoring (e.g., number of panels)
                WHEN ss.scoring_metadata->>'type' = 'count' THEN
                    CASE
                        WHEN ss.scoring_metadata->>'field' IS NOT NULL 
                             AND ge.evidence_data ? (ss.scoring_metadata->>'field') THEN
                            LEAST(
                                jsonb_array_length(ge.evidence_data -> (ss.scoring_metadata->>'field'))::float 
                                / 10.0 * COALESCE((ss.scoring_metadata->>'weight')::numeric, 0.5),
                                1.0
                            )
                        ELSE COALESCE((ss.scoring_metadata->>'weight')::numeric, 0.5)
                    END
                
                -- Classification-based scoring (e.g., confidence levels)
                WHEN ss.scoring_metadata->>'type' = 'classification' 
                     AND ss.scoring_metadata->>'field' IS NOT NULL THEN
                    COALESCE(
                        (ss.scoring_metadata->'weight_map' ->> 
                            (ge.evidence_data->>(ss.scoring_metadata->>'field'))
                        )::numeric,
                        0.3
                    )
                
                -- Fixed scoring
                WHEN ss.scoring_metadata->>'type' = 'fixed' THEN
                    COALESCE((ss.scoring_metadata->>'score')::numeric, 0.5)
                    
                ELSE 0.5
            END AS normalized_score
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        JOIN static_sources ss ON ge.source_name = 'static_' || ss.id::text
        WHERE ss.is_active = true;
    """)
    
    # Create combined evidence scores view - merges pipeline and static sources
    op.execute("""
        CREATE VIEW combined_evidence_scores AS
        -- Pipeline sources (existing scoring)
        SELECT 
            ens.evidence_id,
            ens.gene_id,
            ens.approved_symbol,
            ens.source_name,
            ens.source_name as display_name,
            ens.normalized_score,
            'pipeline' as source_type
        FROM evidence_normalized_scores ens
        WHERE ens.source_name NOT LIKE 'static_%'
        
        UNION ALL
        
        -- Static sources (with display names)
        SELECT 
            ses.evidence_id,
            ses.gene_id,
            ses.approved_symbol,
            ses.source_name,
            ses.source_display_name as display_name,
            ses.normalized_score,
            'static' as source_type
        FROM static_evidence_scores ses;
    """)
    
    # Recreate gene_scores view with proper aggregation
    op.execute("""
        CREATE VIEW gene_scores AS
        WITH active_sources AS (
            -- Count unique sources (both pipeline and static)
            SELECT COUNT(DISTINCT source_name) as total_count
            FROM combined_evidence_scores
        ),
        gene_source_scores AS (
            SELECT
                g.id as gene_id,
                g.approved_symbol,
                g.hgnc_id,
                -- Count unique sources contributing to this gene
                COUNT(DISTINCT ces.source_name) as source_count,
                -- Count all evidence records
                COUNT(ces.evidence_id) as evidence_count,
                -- Sum all normalized scores
                COALESCE(SUM(ces.normalized_score), 0) as raw_score,
                -- Aggregate source scores with display names
                jsonb_object_agg(
                    ces.display_name,
                    ROUND(ces.normalized_score::numeric, 3)
                ) FILTER (WHERE ces.source_name IS NOT NULL) as source_scores
            FROM genes g
            LEFT JOIN combined_evidence_scores ces ON g.id = ces.gene_id
            GROUP BY g.id, g.approved_symbol, g.hgnc_id
        )
        SELECT
            gss.gene_id,
            gss.approved_symbol,
            gss.hgnc_id,
            gss.source_count,
            gss.evidence_count,
            gss.raw_score,
            -- Calculate percentage score based on total active sources
            CASE
                WHEN ac.total_count > 0 THEN
                    ROUND(((gss.raw_score / ac.total_count::float) * 100)::numeric, 2)
                ELSE 0
            END as percentage_score,
            ac.total_count as total_active_sources,
            gss.source_scores
        FROM gene_source_scores gss
        CROSS JOIN active_sources ac
        ORDER BY gss.approved_symbol;
    """)
    
    print("✅ Consolidated static scoring implemented with internal naming (static_{id})")


def downgrade() -> None:
    """Revert to previous state"""
    
    # Drop consolidated views
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS combined_evidence_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS static_evidence_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS static_evidence_counts CASCADE")
    
    # Recreate original views with the old ingested_ pattern
    op.execute("""
        CREATE VIEW static_evidence_counts AS
        SELECT 
            ge.id as evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            ss.id as source_id,
            CASE
                WHEN ss.scoring_metadata->>'field' IS NOT NULL 
                     AND ge.evidence_data ? (ss.scoring_metadata->>'field') THEN
                    jsonb_array_length(ge.evidence_data -> (ss.scoring_metadata->>'field'))
                ELSE 1
            END as source_count
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        JOIN static_sources ss ON ge.source_name = 'ingested_' || ss.id::text
        WHERE ss.is_active = true;
    """)
    
    op.execute("""
        CREATE VIEW static_evidence_scores AS
        SELECT
            ge.id AS evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            ss.display_name as source_display_name,
            CASE
                WHEN ss.scoring_metadata->>'type' = 'count' THEN
                    CASE
                        WHEN ss.scoring_metadata->>'field' IS NOT NULL 
                             AND ge.evidence_data ? (ss.scoring_metadata->>'field') THEN
                            LEAST(
                                jsonb_array_length(ge.evidence_data -> (ss.scoring_metadata->>'field'))::float 
                                / 10.0 * COALESCE((ss.scoring_metadata->>'weight')::numeric, 0.5),
                                1.0
                            )
                        ELSE COALESCE((ss.scoring_metadata->>'weight')::numeric, 0.5)
                    END
                WHEN ss.scoring_metadata->>'type' = 'classification' 
                     AND ss.scoring_metadata->>'field' IS NOT NULL THEN
                    COALESCE(
                        (ss.scoring_metadata->'weight_map' ->> 
                            (ge.evidence_data->>(ss.scoring_metadata->>'field'))
                        )::numeric,
                        0.3
                    )
                WHEN ss.scoring_metadata->>'type' = 'fixed' THEN
                    COALESCE((ss.scoring_metadata->>'score')::numeric, 0.5)
                ELSE 0.5
            END AS normalized_score
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        JOIN static_sources ss ON ge.source_name = 'ingested_' || ss.id::text
        WHERE ss.is_active = true;
    """)
    
    op.execute("""
        CREATE VIEW combined_evidence_scores AS
        SELECT 
            ens.evidence_id,
            ens.gene_id,
            ens.approved_symbol,
            ens.source_name,
            ens.source_name as display_name,
            ens.normalized_score,
            'pipeline' as source_type
        FROM evidence_normalized_scores ens
        
        UNION ALL
        
        SELECT 
            ses.evidence_id,
            ses.gene_id,
            ses.approved_symbol,
            ses.source_name,
            ses.source_display_name as display_name,
            ses.normalized_score,
            'static' as source_type
        FROM static_evidence_scores ses;
    """)
    
    # Revert evidence names
    op.execute("""
        UPDATE gene_evidence ge
        SET source_name = 'ingested_' || ss.id::text
        FROM static_sources ss
        WHERE ge.source_name = 'static_' || ss.id::text;
    """)