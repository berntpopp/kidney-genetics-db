"""Fix diagnostic panel scoring aggregation

Revision ID: d8e9f1a2b3c4
Revises: c7d8e9f0a1b2
Create Date: 2025-08-22 12:30:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd8e9f1a2b3c4'
down_revision: str | None = 'c7d8e9f0a1b2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop existing views to recreate
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS combined_evidence_scores CASCADE")

    # Recreate combined_evidence_scores with aggregation for static sources
    op.execute("""
        CREATE VIEW combined_evidence_scores AS
        -- Pipeline sources (one-to-one)
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
    # Revert to previous version
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS combined_evidence_scores CASCADE")

    # Recreate old combined_evidence_scores (without aggregation)
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

    # Recreate old gene_scores
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
