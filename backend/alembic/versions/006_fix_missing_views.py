"""Fix missing views after static table removal

Revision ID: 006_fix_missing_views
Revises: 005_create_scoring_views
Create Date: 2025-08-23 11:55:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '006_fix_missing_views'
down_revision: str | None = '005_create_scoring_views'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create missing views without static table dependencies."""

    # Create evidence_count_percentiles view
    op.execute("""
        CREATE OR REPLACE VIEW evidence_count_percentiles AS
        SELECT 
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            source_count,
            PERCENT_RANK() OVER (
                PARTITION BY source_name 
                ORDER BY source_count
            ) as percentile_score
        FROM evidence_source_counts
    """)
    print("✓ Created evidence_count_percentiles view")

    # Create evidence_normalized_scores view
    op.execute("""
        CREATE OR REPLACE VIEW evidence_normalized_scores AS
        WITH gencc_percentiles AS (
            SELECT 
                evidence_id,
                gene_id,
                approved_symbol,
                source_name,
                classification_weight,
                PERCENT_RANK() OVER (ORDER BY classification_weight) AS percentile_score
            FROM evidence_classification_weights
            WHERE source_name = 'GenCC'
        )
        SELECT 
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            percentile_score AS normalized_score
        FROM evidence_count_percentiles
        UNION ALL
        SELECT 
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            classification_weight AS normalized_score
        FROM evidence_classification_weights
        WHERE source_name = 'ClinGen'
        UNION ALL
        SELECT 
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            percentile_score AS normalized_score
        FROM gencc_percentiles
    """)
    print("✓ Created evidence_normalized_scores view")

    # Create combined_evidence_scores view (simplified without static sources)
    op.execute("""
        CREATE OR REPLACE VIEW combined_evidence_scores AS
        SELECT 
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            source_name AS display_name,
            normalized_score,
            'pipeline'::text AS source_type
        FROM evidence_normalized_scores
    """)
    print("✓ Created combined_evidence_scores view")

    # Create evidence_summary_view
    op.execute("""
        CREATE OR REPLACE VIEW evidence_summary_view AS
        SELECT 
            ge.id,
            ge.gene_id,
            g.approved_symbol,
            g.hgnc_id,
            ge.source_name,
            ge.evidence_data,
            COALESCE(ces.normalized_score, 0::double precision) AS normalized_score,
            gc.curation_status,
            gc.classification,
            gc.updated_at AS last_curated
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        LEFT JOIN combined_evidence_scores ces ON ge.id = ces.evidence_id
        LEFT JOIN gene_curations gc ON g.id = gc.gene_id
    """)
    print("✓ Created evidence_summary_view")

    # Recreate gene_scores view to use simplified combined_evidence_scores
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("""
        CREATE OR REPLACE VIEW gene_scores AS
        WITH score_components AS (
            SELECT 
                g.id,
                g.approved_symbol,
                COALESCE(COUNT(DISTINCT ge.source_name), 0) as source_count,
                -- Evidence scores by source
                COALESCE(MAX(CASE WHEN ge.source_name = 'PanelApp' THEN COALESCE(ces.normalized_score, 0) END), 0) as panelapp_score,
                COALESCE(MAX(CASE WHEN ge.source_name = 'ClinGen' THEN COALESCE(ces.normalized_score, 0) END), 0) as clingen_score,
                COALESCE(MAX(CASE WHEN ge.source_name = 'GenCC' THEN COALESCE(ces.normalized_score, 0) END), 0) as gencc_score,
                COALESCE(MAX(CASE WHEN ge.source_name = 'HPO' THEN COALESCE(ces.normalized_score, 0) END), 0) as hpo_score,
                COALESCE(MAX(CASE WHEN ge.source_name = 'PubTator' THEN COALESCE(ces.normalized_score, 0) END), 0) as pubtator_score,
                COALESCE(MAX(CASE WHEN ge.source_name = 'Literature' THEN COALESCE(ces.normalized_score, 0) END), 0) as literature_score,
                COALESCE(MAX(CASE WHEN ge.source_name = 'DiagnosticPanels' THEN COALESCE(ces.normalized_score, 0) END), 0) as diagnostic_score
            FROM genes g
            LEFT JOIN gene_evidence ge ON g.id = ge.gene_id
            LEFT JOIN combined_evidence_scores ces ON ge.id = ces.evidence_id
            GROUP BY g.id, g.approved_symbol
        ),
        percentile_ranks AS (
            SELECT 
                id,
                approved_symbol,
                source_count,
                panelapp_score,
                clingen_score,
                gencc_score,
                hpo_score,
                pubtator_score,
                literature_score,
                diagnostic_score,
                -- Calculate percentile ranks for each score
                PERCENT_RANK() OVER (ORDER BY panelapp_score) as panelapp_percentile,
                PERCENT_RANK() OVER (ORDER BY clingen_score) as clingen_percentile,
                PERCENT_RANK() OVER (ORDER BY gencc_score) as gencc_percentile,
                PERCENT_RANK() OVER (ORDER BY hpo_score) as hpo_percentile,
                PERCENT_RANK() OVER (ORDER BY pubtator_score) as pubtator_percentile,
                PERCENT_RANK() OVER (ORDER BY literature_score) as literature_percentile,
                PERCENT_RANK() OVER (ORDER BY diagnostic_score) as diagnostic_percentile
            FROM score_components
        )
        SELECT 
            id as gene_id,
            approved_symbol,
            source_count,
            source_count as evidence_count,  -- For CRUD compatibility
            -- Raw scores
            panelapp_score,
            clingen_score,
            gencc_score,
            hpo_score,
            pubtator_score,
            literature_score,
            diagnostic_score,
            -- Percentile normalized scores (0-100 scale)
            ROUND((panelapp_percentile * 100)::numeric, 2) as panelapp_percentile_score,
            ROUND((clingen_percentile * 100)::numeric, 2) as clingen_percentile_score,
            ROUND((gencc_percentile * 100)::numeric, 2) as gencc_percentile_score,
            ROUND((hpo_percentile * 100)::numeric, 2) as hpo_percentile_score,
            ROUND((pubtator_percentile * 100)::numeric, 2) as pubtator_percentile_score,
            ROUND((literature_percentile * 100)::numeric, 2) as literature_percentile_score,
            ROUND((diagnostic_percentile * 100)::numeric, 2) as diagnostic_percentile_score,
            -- Weighted combined score (using percentiles)
            ROUND(
                ((panelapp_percentile * 25 +  -- Clinical panels (highest weight)
                 clingen_percentile * 20 +    -- Expert curation
                 gencc_percentile * 15 +      -- International consensus
                 diagnostic_percentile * 15 + -- Commercial panels
                 hpo_percentile * 10 +        -- Phenotype associations
                 pubtator_percentile * 10 +   -- Literature mining
                 literature_percentile * 5    -- Manual literature
                ) * 100 / 100)::numeric,
                2
            ) as combined_score,
            -- Additional columns for CRUD compatibility
            ROUND(
                ((panelapp_percentile * 25 +
                 clingen_percentile * 20 +
                 gencc_percentile * 15 +
                 diagnostic_percentile * 15 +
                 hpo_percentile * 10 +
                 pubtator_percentile * 10 +
                 literature_percentile * 5
                ))::numeric,
                2
            ) as raw_score,
            ROUND(
                ((panelapp_percentile * 25 +
                 clingen_percentile * 20 +
                 gencc_percentile * 15 +
                 diagnostic_percentile * 15 +
                 hpo_percentile * 10 +
                 pubtator_percentile * 10 +
                 literature_percentile * 5
                ) * 100 / 100)::numeric,
                2
            ) as percentage_score,
            7 as total_active_sources,  -- Count of active sources
            jsonb_build_object(
                'PanelApp', ROUND((panelapp_percentile * 100)::numeric, 2),
                'ClinGen', ROUND((clingen_percentile * 100)::numeric, 2),
                'GenCC', ROUND((gencc_percentile * 100)::numeric, 2),
                'HPO', ROUND((hpo_percentile * 100)::numeric, 2),
                'PubTator', ROUND((pubtator_percentile * 100)::numeric, 2),
                'Literature', ROUND((literature_percentile * 100)::numeric, 2),
                'DiagnosticPanels', ROUND((diagnostic_percentile * 100)::numeric, 2)
            ) as source_scores
        FROM percentile_ranks
    """)
    print("✓ Recreated gene_scores view with all dependencies")

    print("✓ All missing views created successfully")


def downgrade() -> None:
    """Drop the views."""

    op.execute("DROP VIEW IF EXISTS evidence_summary_view CASCADE")
    op.execute("DROP VIEW IF EXISTS combined_evidence_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_normalized_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_count_percentiles CASCADE")

    print("✓ Views dropped")
