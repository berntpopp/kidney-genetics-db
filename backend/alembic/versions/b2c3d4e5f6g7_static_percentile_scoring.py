"""Use percentile-based scoring for static sources

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-08-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create view for static source counts (similar to evidence_source_counts)
    op.execute("""
        CREATE OR REPLACE VIEW static_evidence_counts AS
        SELECT 
            ge.id as evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            ss.display_name as source_display_name,
            ss.id as source_id,
            ss.scoring_metadata,
            CASE 
                WHEN ss.scoring_metadata->>'type' = 'count' 
                AND ss.scoring_metadata->>'field' IS NOT NULL 
                AND ge.evidence_data ? (ss.scoring_metadata->>'field') THEN
                    jsonb_array_length(ge.evidence_data->(ss.scoring_metadata->>'field'))
                WHEN ss.scoring_metadata->>'type' = 'classification' THEN
                    -- Map classification to numeric value for ranking
                    CASE ge.evidence_data->>(ss.scoring_metadata->>'field')
                        WHEN 'high' THEN 3
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 1
                        ELSE 0
                    END
                ELSE 1  -- Fixed scoring gets same rank
            END as source_count
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        JOIN static_sources ss ON ge.source_name = 'static_' || ss.id::text
        WHERE ss.is_active = true
    """)
    
    # Drop and recreate static_evidence_scores with percentile-based scoring
    op.execute("DROP VIEW IF EXISTS static_evidence_scores CASCADE")
    
    op.execute("""
        CREATE VIEW static_evidence_scores AS
        WITH percentiles AS (
            SELECT 
                evidence_id,
                gene_id,
                approved_symbol,
                source_name,
                source_display_name,
                source_id,
                scoring_metadata,
                source_count,
                -- Calculate percentile rank within each source
                PERCENT_RANK() OVER (
                    PARTITION BY source_id 
                    ORDER BY source_count
                ) as percentile_rank
            FROM static_evidence_counts
            WHERE source_count > 0
        )
        SELECT 
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            source_display_name,
            CASE 
                WHEN scoring_metadata->>'type' = 'fixed' THEN
                    -- Fixed scoring ignores percentile
                    COALESCE((scoring_metadata->>'score')::float, 0.5)
                WHEN scoring_metadata->>'type' = 'classification' THEN
                    -- Classification uses weight map directly
                    COALESCE(
                        ((scoring_metadata->'weight_map')->>(
                            SELECT evidence_data->>(scoring_metadata->>'field')
                            FROM gene_evidence 
                            WHERE id = percentiles.evidence_id
                        ))::float,
                        0.3
                    )
                ELSE
                    -- Count-based uses percentile with weight
                    percentile_rank * COALESCE((scoring_metadata->>'weight')::float, 1.0)
            END as normalized_score
        FROM percentiles
    """)
    
    # Recreate dependent views
    op.execute("DROP VIEW IF EXISTS combined_evidence_scores CASCADE")
    op.execute("""
        CREATE VIEW combined_evidence_scores AS
        SELECT 
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            source_name as display_name,
            normalized_score,
            'pipeline' as source_type
        FROM evidence_normalized_scores
        
        UNION ALL
        
        SELECT 
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            source_display_name as display_name,
            normalized_score,
            'static' as source_type
        FROM static_evidence_scores
    """)
    
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("""
        CREATE VIEW gene_scores AS
        WITH source_counts AS (
            SELECT 
                gene_id,
                COUNT(DISTINCT source_name) as source_count,
                COUNT(*) as evidence_count,
                SUM(normalized_score) as raw_score,
                jsonb_object_agg(
                    COALESCE(display_name, source_name),
                    ROUND(normalized_score::numeric, 3)
                ) as source_scores
            FROM combined_evidence_scores
            GROUP BY gene_id
        ),
        total_sources AS (
            SELECT COUNT(DISTINCT name) as total
            FROM (
                SELECT DISTINCT source_name as name FROM evidence_normalized_scores
                UNION
                SELECT DISTINCT source_name as name FROM static_evidence_scores
            ) all_sources
        )
        SELECT 
            sc.gene_id,
            g.approved_symbol,
            g.hgnc_id,
            sc.source_count,
            sc.evidence_count,
            sc.raw_score,
            ROUND((sc.raw_score / ts.total * 100)::numeric, 2) as percentage_score,
            ts.total as total_active_sources,
            sc.source_scores
        FROM source_counts sc
        CROSS JOIN total_sources ts
        JOIN genes g ON sc.gene_id = g.id
    """)


def downgrade() -> None:
    # Revert to ratio-based scoring
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS combined_evidence_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS static_evidence_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS static_evidence_counts CASCADE")
    
    # Recreate with dynamic max calculation
    op.execute("""
        CREATE VIEW static_evidence_scores AS
        WITH max_panel_counts AS (
            SELECT 
                ss.id as source_id,
                MAX(jsonb_array_length(ge.evidence_data->'panels')) as max_panels
            FROM gene_evidence ge
            JOIN static_sources ss ON ge.source_name = 'static_' || ss.id::text
            WHERE ss.is_active = true
            AND ge.evidence_data ? 'panels'
            GROUP BY ss.id
        )
        SELECT 
            ge.id as evidence_id,
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
                                jsonb_array_length(ge.evidence_data->(ss.scoring_metadata->>'field'))::float / 
                                GREATEST(mpc.max_panels::float, 1.0) * 
                                COALESCE((ss.scoring_metadata->>'weight')::float, 0.5),
                                1.0
                            )
                        ELSE 
                            COALESCE((ss.scoring_metadata->>'weight')::float, 0.5)
                    END
                WHEN ss.scoring_metadata->>'type' = 'classification' 
                AND ss.scoring_metadata->>'field' IS NOT NULL THEN
                    COALESCE(
                        ((ss.scoring_metadata->'weight_map')->>(ge.evidence_data->>(ss.scoring_metadata->>'field')))::float,
                        0.3
                    )
                WHEN ss.scoring_metadata->>'type' = 'fixed' THEN
                    COALESCE((ss.scoring_metadata->>'score')::float, 0.5)
                ELSE 0.5
            END as normalized_score
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        JOIN static_sources ss ON ge.source_name = 'static_' || ss.id::text
        LEFT JOIN max_panel_counts mpc ON mpc.source_id = ss.id
        WHERE ss.is_active = true
    """)
    
    # Recreate dependent views
    op.execute("""
        CREATE VIEW combined_evidence_scores AS
        SELECT 
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            source_name as display_name,
            normalized_score,
            'pipeline' as source_type
        FROM evidence_normalized_scores
        
        UNION ALL
        
        SELECT 
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            source_display_name as display_name,
            normalized_score,
            'static' as source_type
        FROM static_evidence_scores
    """)
    
    op.execute("""
        CREATE VIEW gene_scores AS
        WITH source_counts AS (
            SELECT 
                gene_id,
                COUNT(DISTINCT source_name) as source_count,
                COUNT(*) as evidence_count,
                SUM(normalized_score) as raw_score,
                jsonb_object_agg(
                    COALESCE(display_name, source_name),
                    ROUND(normalized_score::numeric, 3)
                ) as source_scores
            FROM combined_evidence_scores
            GROUP BY gene_id
        ),
        total_sources AS (
            SELECT COUNT(DISTINCT name) as total
            FROM (
                SELECT DISTINCT source_name as name FROM evidence_normalized_scores
                UNION
                SELECT DISTINCT source_name as name FROM static_evidence_scores
            ) all_sources
        )
        SELECT 
            sc.gene_id,
            g.approved_symbol,
            g.hgnc_id,
            sc.source_count,
            sc.evidence_count,
            sc.raw_score,
            ROUND((sc.raw_score / ts.total * 100)::numeric, 2) as percentage_score,
            ts.total as total_active_sources,
            sc.source_scores
        FROM source_counts sc
        CROSS JOIN total_sources ts
        JOIN genes g ON sc.gene_id = g.id
    """)