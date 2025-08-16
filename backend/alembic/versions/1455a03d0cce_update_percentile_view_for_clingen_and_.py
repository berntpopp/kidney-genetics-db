"""update percentile view for clingen and gencc

Revision ID: 1455a03d0cce
Revises: 5024f3c7fab3
Create Date: 2025-08-16 15:50:32.455439

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1455a03d0cce'
down_revision: str | Sequence[str] | None = '5024f3c7fab3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Update gene_evidence_with_percentiles view to include ClinGen and GenCC scoring"""

    # Update the view to include ClinGen and GenCC
    op.execute("""
        CREATE OR REPLACE VIEW gene_evidence_with_percentiles AS
        WITH source_counts AS (
            -- Extract counts from JSONB based on source type
            SELECT
                ge.id,
                ge.gene_id,
                ge.source_name,
                ge.source_detail,
                ge.evidence_data,
                ge.evidence_date,
                ge.created_at,
                ge.updated_at,
                CASE
                    WHEN ge.source_name = 'PanelApp' THEN
                        jsonb_array_length(COALESCE(ge.evidence_data->'panels', '[]'::jsonb))
                    WHEN ge.source_name = 'PubTator' THEN
                        COALESCE((ge.evidence_data->>'publication_count')::int,
                                jsonb_array_length(COALESCE(ge.evidence_data->'pmids', '[]'::jsonb)))
                    WHEN ge.source_name = 'HPO' THEN
                        jsonb_array_length(COALESCE(ge.evidence_data->'phenotypes', '[]'::jsonb)) +
                        jsonb_array_length(COALESCE(ge.evidence_data->'disease_associations', '[]'::jsonb))
                    WHEN ge.source_name = 'Literature' THEN
                        jsonb_array_length(COALESCE(ge.evidence_data->'references', '[]'::jsonb))
                    WHEN ge.source_name = 'ClinGen' THEN
                        COALESCE((ge.evidence_data->>'validity_count')::int,
                                jsonb_array_length(COALESCE(ge.evidence_data->'validities', '[]'::jsonb)))
                    WHEN ge.source_name = 'GenCC' THEN
                        COALESCE((ge.evidence_data->>'submission_count')::int,
                                jsonb_array_length(COALESCE(ge.evidence_data->'submissions', '[]'::jsonb)))
                    ELSE
                        jsonb_array_length(COALESCE(ge.evidence_data->'items', '[]'::jsonb))
                END AS source_count
            FROM gene_evidence ge
        )
        SELECT
            sc.*,
            -- Calculate percentile using PERCENT_RANK() which matches R's rank(ties.method="average")/n()
            PERCENT_RANK() OVER (
                PARTITION BY sc.source_name
                ORDER BY sc.source_count
            ) AS source_count_percentile
        FROM source_counts sc;
    """)

    # Refresh the materialized view if it exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_matviews WHERE matviewname = 'gene_scores_cached') THEN
                REFRESH MATERIALIZED VIEW gene_scores_cached;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Restore the original view without ClinGen/GenCC support"""

    # Restore original view
    op.execute("""
        CREATE OR REPLACE VIEW gene_evidence_with_percentiles AS
        WITH source_counts AS (
            -- Extract counts from JSONB based on source type
            SELECT
                ge.id,
                ge.gene_id,
                ge.source_name,
                ge.source_detail,
                ge.evidence_data,
                ge.evidence_date,
                ge.created_at,
                ge.updated_at,
                CASE
                    WHEN ge.source_name = 'PanelApp' THEN
                        jsonb_array_length(COALESCE(ge.evidence_data->'panels', '[]'::jsonb))
                    WHEN ge.source_name = 'PubTator' THEN
                        COALESCE((ge.evidence_data->>'publication_count')::int,
                                jsonb_array_length(COALESCE(ge.evidence_data->'pmids', '[]'::jsonb)))
                    WHEN ge.source_name = 'HPO' THEN
                        jsonb_array_length(COALESCE(ge.evidence_data->'phenotypes', '[]'::jsonb)) +
                        jsonb_array_length(COALESCE(ge.evidence_data->'disease_associations', '[]'::jsonb))
                    WHEN ge.source_name = 'Literature' THEN
                        jsonb_array_length(COALESCE(ge.evidence_data->'references', '[]'::jsonb))
                    ELSE
                        jsonb_array_length(COALESCE(ge.evidence_data->'items', '[]'::jsonb))
                END AS source_count
            FROM gene_evidence ge
        )
        SELECT
            sc.*,
            -- Calculate percentile using PERCENT_RANK() which matches R's rank(ties.method="average")/n()
            PERCENT_RANK() OVER (
                PARTITION BY sc.source_name
                ORDER BY sc.source_count
            ) AS source_count_percentile
        FROM source_counts sc;
    """)

    # Refresh the materialized view if it exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_matviews WHERE matviewname = 'gene_scores_cached') THEN
                REFRESH MATERIALIZED VIEW gene_scores_cached;
            END IF;
        END $$;
    """)
