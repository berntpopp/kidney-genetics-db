"""Update views for hybrid sources

Revision ID: 003_update_views
Revises: 002_add_missing_gene_staging_columns
Create Date: 2025-08-23 10:20:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '003_update_views'
down_revision: str | None = '002_add_missing_columns'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Update views to handle new hybrid source names."""

    # Drop existing view
    op.execute("DROP VIEW IF EXISTS evidence_source_counts CASCADE")

    # Recreate with support for new source names
    op.execute("""
        CREATE OR REPLACE VIEW evidence_source_counts AS
        SELECT ge.id AS evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            CASE ge.source_name
                WHEN 'PanelApp' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'panels'), 0)::bigint
                WHEN 'HPO' THEN (COALESCE(jsonb_array_length(ge.evidence_data -> 'hpo_terms'), 0) + 
                                COALESCE(jsonb_array_length(ge.evidence_data -> 'diseases'), 0))::bigint
                WHEN 'PubTator' THEN COALESCE((ge.evidence_data ->> 'publication_count')::integer, 
                                             jsonb_array_length(ge.evidence_data -> 'pmids'))::bigint
                WHEN 'Literature' THEN COALESCE((ge.evidence_data ->> 'publication_count')::integer, 
                                              jsonb_array_length(ge.evidence_data -> 'references'))::bigint
                WHEN 'DiagnosticPanels' THEN COALESCE((ge.evidence_data ->> 'panel_count')::integer, 
                                                     jsonb_array_length(ge.evidence_data -> 'panels'))::bigint
                WHEN 'GenCC' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'classifications'), 0)::bigint
                WHEN 'ClinGen' THEN COALESCE((ge.evidence_data ->> 'assertion_count')::integer, 1)::bigint
                ELSE 0::bigint
            END AS source_count
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
    """)

    print("✓ Updated evidence_source_counts view for hybrid sources")


def downgrade() -> None:
    """Revert to previous view definition."""

    op.execute("DROP VIEW IF EXISTS evidence_source_counts CASCADE")

    # Recreate old view
    op.execute("""
        CREATE OR REPLACE VIEW evidence_source_counts AS
        SELECT ge.id AS evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            CASE ge.source_name
                WHEN 'PanelApp' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'panels'), 0)::bigint
                WHEN 'HPO' THEN (COALESCE(jsonb_array_length(ge.evidence_data -> 'hpo_terms'), 0) + 
                                COALESCE(jsonb_array_length(ge.evidence_data -> 'diseases'), 0))::bigint
                WHEN 'PubTator' THEN COALESCE((ge.evidence_data ->> 'publication_count')::integer, 
                                             jsonb_array_length(ge.evidence_data -> 'pmids'))::bigint
                WHEN 'Literature' THEN COALESCE(jsonb_array_length(ge.evidence_data -> 'references'), 0)::bigint
                ELSE
                    CASE
                        WHEN ge.source_name::text ~~ 'static_%'::text THEN (
                            SELECT count(DISTINCT ge2.source_detail) AS count
                            FROM gene_evidence ge2
                            WHERE ge2.gene_id = ge.gene_id
                            AND ge2.source_name::text = ge.source_name::text
                        )
                        ELSE 0::bigint
                    END
            END AS source_count
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        WHERE (ge.source_name::text = ANY (ARRAY['PanelApp'::text, 'HPO'::text, 'PubTator'::text, 'Literature'::text]))
            OR ge.source_name::text ~~ 'static_%'::text
    """)
