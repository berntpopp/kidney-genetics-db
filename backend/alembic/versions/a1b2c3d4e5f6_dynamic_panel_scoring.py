"""Dynamic panel scoring based on actual max panels

Revision ID: a1b2c3d4e5f6
Revises: 8f3a2b1c4d5e
Create Date: 2025-08-22 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '8f3a2b1c4d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop and recreate static_evidence_scores view with dynamic max calculation
    op.execute("DROP VIEW IF EXISTS static_evidence_scores CASCADE")
    
    op.execute("""
        CREATE VIEW static_evidence_scores AS
        WITH max_panel_counts AS (
            -- Calculate the maximum number of panels any gene appears in
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
                -- Count-based scoring (for diagnostic panels)
                WHEN ss.scoring_metadata->>'type' = 'count' THEN
                    CASE
                        WHEN ss.scoring_metadata->>'field' IS NOT NULL 
                        AND ge.evidence_data ? (ss.scoring_metadata->>'field') THEN
                            -- Use actual max panels as denominator
                            LEAST(
                                jsonb_array_length(ge.evidence_data->(ss.scoring_metadata->>'field'))::float / 
                                GREATEST(mpc.max_panels::float, 1.0) * 
                                COALESCE((ss.scoring_metadata->>'weight')::float, 0.5),
                                1.0
                            )
                        ELSE 
                            COALESCE((ss.scoring_metadata->>'weight')::float, 0.5)
                    END
                -- Classification-based scoring
                WHEN ss.scoring_metadata->>'type' = 'classification' 
                AND ss.scoring_metadata->>'field' IS NOT NULL THEN
                    COALESCE(
                        ((ss.scoring_metadata->'weight_map')->>(ge.evidence_data->>(ss.scoring_metadata->>'field')))::float,
                        0.3
                    )
                -- Fixed scoring
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
    # Revert to fixed denominator of 10
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS combined_evidence_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS static_evidence_scores CASCADE")
    
    op.execute("""
        CREATE VIEW static_evidence_scores AS
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
                                jsonb_array_length(ge.evidence_data->(ss.scoring_metadata->>'field'))::float / 10.0 * 
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