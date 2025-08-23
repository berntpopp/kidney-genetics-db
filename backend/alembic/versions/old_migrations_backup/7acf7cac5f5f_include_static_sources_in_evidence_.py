"""include_static_sources_in_evidence_scoring

Revision ID: 7acf7cac5f5f
Revises: a3f40460739f
Create Date: 2025-08-22 17:01:13.165946

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7acf7cac5f5f'
down_revision: str | Sequence[str] | None = 'a3f40460739f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Include static sources in evidence scoring views."""

    # Drop and recreate evidence_source_counts to include static sources
    op.execute("DROP VIEW IF EXISTS evidence_source_counts CASCADE")
    op.execute("""
        CREATE VIEW evidence_source_counts AS
        SELECT
            ge.id AS evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            CASE ge.source_name
                WHEN 'PanelApp' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'panels'), 0)
                WHEN 'HPO' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'hpo_terms'), 0) + COALESCE(jsonb_array_length(ge.evidence_data -> 'diseases'), 0)
                WHEN 'PubTator' THEN COALESCE((ge.evidence_data->>'publication_count')::integer, jsonb_array_length(ge.evidence_data -> 'pmids'))
                WHEN 'Literature' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'references'), 0)
                ELSE
                    CASE
                        WHEN ge.source_name LIKE 'static_%' THEN
                            (SELECT COUNT(DISTINCT ge2.source_detail)
                             FROM gene_evidence ge2
                             WHERE ge2.gene_id = ge.gene_id
                             AND ge2.source_name = ge.source_name)
                        ELSE 0
                    END
            END AS source_count
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        WHERE ge.source_name = ANY(ARRAY['PanelApp', 'HPO', 'PubTator', 'Literature'])
            OR ge.source_name LIKE 'static_%'
    """)

    # Recreate dependent views
    op.execute("""
        CREATE VIEW evidence_count_percentiles AS
        SELECT
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            source_count,
            PERCENT_RANK() OVER (PARTITION BY source_name ORDER BY source_count) AS percentile_score
        FROM evidence_source_counts
        WHERE source_count > 0
    """)

    op.execute("""
        CREATE VIEW evidence_normalized_scores AS
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

    op.execute("""
        CREATE VIEW combined_evidence_scores AS
        -- Pipeline sources (excluding static sources)
        SELECT
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            source_name as display_name,
            normalized_score,
            'pipeline' as source_type
        FROM evidence_normalized_scores
        WHERE source_name NOT LIKE 'static_%'

        UNION ALL

        -- Static sources aggregated by source (not by provider)
        SELECT
            MIN(evidence_id) as evidence_id,  -- Take first evidence_id for the group
            gene_id,
            approved_symbol,
            source_name,
            MAX(source_display_name) as display_name,  -- Use display name from static_sources
            MAX(normalized_score) as normalized_score,  -- Take max score across providers
            'static' as source_type
        FROM static_evidence_scores
        GROUP BY gene_id, approved_symbol, source_name
    """)

    # Recreate gene_scores view
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
    """Revert evidence_source_counts to exclude static sources."""
    # Drop all dependent views
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS combined_evidence_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_count_percentiles CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_source_counts CASCADE")

    # Recreate original views without static sources
    op.execute("""
        CREATE VIEW evidence_source_counts AS
        SELECT
            ge.id AS evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            CASE ge.source_name
                WHEN 'PanelApp' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'panels'), 0)
                WHEN 'HPO' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'hpo_terms'), 0) + COALESCE(jsonb_array_length(ge.evidence_data -> 'diseases'), 0)
                WHEN 'PubTator' THEN COALESCE((ge.evidence_data->>'publication_count')::integer, jsonb_array_length(ge.evidence_data -> 'pmids'))
                WHEN 'Literature' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'references'), 0)
                ELSE 0
            END AS source_count
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        WHERE ge.source_name = ANY(ARRAY['PanelApp', 'HPO', 'PubTator', 'Literature'])
    """)

    # Recreate other views as they were
    op.execute("""
        CREATE VIEW evidence_count_percentiles AS
        SELECT
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            source_count,
            PERCENT_RANK() OVER (PARTITION BY source_name ORDER BY source_count) AS percentile_score
        FROM evidence_source_counts
        WHERE source_count > 0
    """)

    op.execute("""
        CREATE VIEW evidence_normalized_scores AS
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

    op.execute("""
        CREATE VIEW combined_evidence_scores AS
        SELECT
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            normalized_score
        FROM evidence_normalized_scores
    """)
