"""Create scoring views for hybrid sources

Revision ID: 005_create_scoring_views
Revises: 004_remove_static_tables
Create Date: 2025-08-23 11:35:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '005_create_scoring_views'
down_revision: str | None = '004_remove_static_tables'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create scoring views including support for hybrid sources."""

    # Create gene_scores view with percentile normalization
    op.execute("""
        CREATE OR REPLACE VIEW gene_scores AS
        WITH score_components AS (
            SELECT 
                g.id,
                g.approved_symbol,
                COALESCE(COUNT(DISTINCT ge.source_name), 0) as source_count,
                -- Evidence scores by source
                COALESCE(MAX(CASE WHEN ge.source_name = 'PanelApp' THEN ge.evidence_score END), 0) as panelapp_score,
                COALESCE(MAX(CASE WHEN ge.source_name = 'ClinGen' THEN ge.evidence_score END), 0) as clingen_score,
                COALESCE(MAX(CASE WHEN ge.source_name = 'GenCC' THEN ge.evidence_score END), 0) as gencc_score,
                COALESCE(MAX(CASE WHEN ge.source_name = 'HPO' THEN ge.evidence_score END), 0) as hpo_score,
                COALESCE(MAX(CASE WHEN ge.source_name = 'PubTator' THEN ge.evidence_score END), 0) as pubtator_score,
                COALESCE(MAX(CASE WHEN ge.source_name = 'Literature' THEN ge.evidence_score END), 0) as literature_score,
                COALESCE(MAX(CASE WHEN ge.source_name = 'DiagnosticPanels' THEN ge.evidence_score END), 0) as diagnostic_score
            FROM genes g
            LEFT JOIN gene_evidence ge ON g.id = ge.gene_id
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
                ) * 100 / 100)::numeric,  -- Normalize to 0-100 scale
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
                ) * 100 / 100)::numeric,
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

    print("✓ Created gene_scores view with percentile normalization")

    # Create gene_evidence_summary view
    op.execute("""
        CREATE OR REPLACE VIEW gene_evidence_summary AS
        SELECT 
            g.id as gene_id,
            g.approved_symbol,
            g.hgnc_id,
            -- Source presence flags
            MAX(CASE WHEN ge.source_name = 'PanelApp' THEN 1 ELSE 0 END)::boolean as has_panelapp,
            MAX(CASE WHEN ge.source_name = 'ClinGen' THEN 1 ELSE 0 END)::boolean as has_clingen,
            MAX(CASE WHEN ge.source_name = 'GenCC' THEN 1 ELSE 0 END)::boolean as has_gencc,
            MAX(CASE WHEN ge.source_name = 'HPO' THEN 1 ELSE 0 END)::boolean as has_hpo,
            MAX(CASE WHEN ge.source_name = 'PubTator' THEN 1 ELSE 0 END)::boolean as has_pubtator,
            MAX(CASE WHEN ge.source_name = 'Literature' THEN 1 ELSE 0 END)::boolean as has_literature,
            MAX(CASE WHEN ge.source_name = 'DiagnosticPanels' THEN 1 ELSE 0 END)::boolean as has_diagnostic,
            -- Evidence counts
            COUNT(DISTINCT ge.source_name) as total_sources,
            COUNT(ge.id) as total_evidence_records,
            -- Latest update
            MAX(ge.updated_at) as last_evidence_update
        FROM genes g
        LEFT JOIN gene_evidence ge ON g.id = ge.gene_id
        GROUP BY g.id, g.approved_symbol, g.hgnc_id
    """)

    print("✓ Created gene_evidence_summary view")

    # Update evidence_source_active view to include hybrid sources
    op.execute("""
        CREATE OR REPLACE VIEW evidence_source_active AS
        SELECT DISTINCT source_name, true as is_active
        FROM gene_evidence
        WHERE source_name IN (
            'PanelApp', 'ClinGen', 'GenCC', 'HPO', 'PubTator', 
            'Literature', 'DiagnosticPanels'
        )
    """)

    print("✓ Updated evidence_source_active view")

    print("✓ All scoring views created successfully")


def downgrade() -> None:
    """Drop scoring views."""

    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS gene_evidence_summary CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_source_active CASCADE")

    print("✓ Scoring views dropped")
