"""add pubtator evidence score column

Revision ID: 3a4b5c6d7e8f
Revises: 443aa8a1ddf7
Create Date: 2025-08-18 09:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3a4b5c6d7e8f"
down_revision: str | Sequence[str] | None = "2d3f4a5b6c7e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add evidence_score column to gene_evidence table for PubTator relevance scores.
    This allows us to store and query based on the relevance scores from PubTator3 search.
    """

    # Add evidence_score column to gene_evidence table
    op.add_column(
        "gene_evidence",
        sa.Column(
            "evidence_score",
            sa.Float(),
            nullable=True,
            comment="Relevance/confidence score from data source (e.g., PubTator relevance score)",
        ),
    )

    # Create an index on evidence_score for efficient queries
    op.create_index(
        "idx_gene_evidence_score",
        "gene_evidence",
        ["evidence_score"],
        postgresql_where=sa.text("evidence_score IS NOT NULL"),
    )

    # Create a composite index for efficient filtering by source and score
    op.create_index(
        "idx_gene_evidence_source_score",
        "gene_evidence",
        ["source_name", "evidence_score"],
        postgresql_where=sa.text("evidence_score IS NOT NULL"),
    )

    # Update the evidence_summary_view to include average evidence scores
    op.execute("""
        CREATE OR REPLACE VIEW evidence_summary_view AS
        SELECT
            ge.gene_id,
            g.approved_symbol as symbol,
            g.hgnc_id,
            COUNT(DISTINCT ge.source_name) as source_count,
            array_agg(DISTINCT ge.source_name ORDER BY ge.source_name) as sources,
            MAX(ge.evidence_date) as latest_evidence_date,
            MIN(ge.evidence_date) as earliest_evidence_date,
            COALESCE(AVG(ge.evidence_score) FILTER (WHERE ge.evidence_score IS NOT NULL), 0) as avg_evidence_score,
            MAX(ge.evidence_score) as max_evidence_score,
            jsonb_object_agg(
                ge.source_name,
                jsonb_build_object(
                    'evidence_date', ge.evidence_date,
                    'evidence_score', ge.evidence_score,
                    'source_detail', ge.source_detail
                )
            ) as source_details
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        GROUP BY ge.gene_id, g.approved_symbol, g.hgnc_id;
    """)

    # Add a function to extract PubTator-specific metrics from evidence_data
    op.execute("""
        CREATE OR REPLACE FUNCTION extract_pubtator_metrics(evidence_data jsonb)
        RETURNS jsonb AS $$
        BEGIN
            RETURN jsonb_build_object(
                'publication_count', COALESCE((evidence_data->>'publication_count')::int, 0),
                'total_mentions', COALESCE((evidence_data->>'total_mentions')::int, 0),
                'evidence_score', COALESCE((evidence_data->>'evidence_score')::float, 0),
                'top_pmids', COALESCE(evidence_data->'pmids', '[]'::jsonb)
            );
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
    """)

    # Create a materialized view for PubTator evidence specifically
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS pubtator_evidence_summary AS
        SELECT
            ge.gene_id,
            g.approved_symbol as symbol,
            g.hgnc_id,
            ge.evidence_score,
            extract_pubtator_metrics(ge.evidence_data) as pubtator_metrics,
            ge.evidence_data->'pmids' as pmids,
            ge.evidence_data->'top_mentions' as top_mentions,
            ge.evidence_date,
            ge.updated_at
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        WHERE ge.source_name = 'PubTator'
        ORDER BY ge.evidence_score DESC NULLS LAST;

        CREATE INDEX idx_pubtator_evidence_summary_gene_id
        ON pubtator_evidence_summary(gene_id);

        CREATE INDEX idx_pubtator_evidence_summary_score
        ON pubtator_evidence_summary(evidence_score DESC NULLS LAST);
    """)


def downgrade() -> None:
    """
    Remove evidence_score column and related indexes/views.
    """

    # Drop the materialized view
    op.execute("DROP MATERIALIZED VIEW IF EXISTS pubtator_evidence_summary CASCADE")

    # Drop the function
    op.execute("DROP FUNCTION IF EXISTS extract_pubtator_metrics(jsonb)")

    # Restore the original evidence_summary_view without evidence_score
    op.execute("""
        CREATE OR REPLACE VIEW evidence_summary_view AS
        SELECT
            ge.gene_id,
            g.approved_symbol as symbol,
            g.hgnc_id,
            COUNT(DISTINCT ge.source_name) as source_count,
            array_agg(DISTINCT ge.source_name ORDER BY ge.source_name) as sources,
            MAX(ge.evidence_date) as latest_evidence_date,
            MIN(ge.evidence_date) as earliest_evidence_date,
            jsonb_object_agg(
                ge.source_name,
                jsonb_build_object(
                    'evidence_date', ge.evidence_date,
                    'source_detail', ge.source_detail
                )
            ) as source_details
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        GROUP BY ge.gene_id, g.approved_symbol, g.hgnc_id;
    """)

    # Drop indexes
    op.drop_index("idx_gene_evidence_source_score", "gene_evidence")
    op.drop_index("idx_gene_evidence_score", "gene_evidence")

    # Drop column
    op.drop_column("gene_evidence", "evidence_score")
