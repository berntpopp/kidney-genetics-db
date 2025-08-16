"""Add percentage scoring with source count

Revision ID: 5024f3c7fab3
Revises: 5e5f74345f03
Create Date: 2025-08-16 14:46:20.989680

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5024f3c7fab3'
down_revision: str | Sequence[str] | None = '5e5f74345f03'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create view for tracking active sources
    op.execute("""
        CREATE OR REPLACE VIEW active_sources AS
        SELECT DISTINCT source_name
        FROM gene_evidence
        ORDER BY source_name;
    """)

    # Create view for source count
    op.execute("""
        CREATE OR REPLACE VIEW source_count AS
        SELECT COUNT(DISTINCT source_name) AS total_sources
        FROM gene_evidence;
    """)

    # Drop existing view first (can't rename columns with CREATE OR REPLACE)
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE;")

    # Create new gene_scores view with percentage scoring
    op.execute("""
        CREATE VIEW gene_scores AS
        WITH percentiles AS (
            SELECT
                gene_id,
                source_name,
                source_count_percentile
            FROM gene_evidence_with_percentiles
        ),
        source_stats AS (
            SELECT COUNT(DISTINCT source_name) AS total_sources
            FROM gene_evidence
        )
        SELECT
            g.id AS gene_id,
            g.approved_symbol,
            g.hgnc_id,
            COUNT(DISTINCT p.source_name) AS source_count,
            COUNT(p.*) AS evidence_count,
            -- Raw percentile sum (0 to N where N = number of sources)
            COALESCE(SUM(p.source_count_percentile), 0) AS raw_score,
            -- Percentage score (0-100)
            CASE
                WHEN ss.total_sources > 0 THEN
                    ROUND((COALESCE(SUM(p.source_count_percentile), 0) / ss.total_sources * 100)::numeric, 2)
                ELSE 0
            END AS percentage_score,
            -- Store total active sources
            ss.total_sources AS total_active_sources,
            -- Store individual source percentiles as JSONB
            jsonb_object_agg(
                p.source_name,
                p.source_count_percentile
            ) FILTER (WHERE p.source_name IS NOT NULL) AS source_percentiles
        FROM genes g
        CROSS JOIN source_stats ss
        LEFT JOIN percentiles p ON g.id = p.gene_id
        GROUP BY g.id, g.approved_symbol, g.hgnc_id, ss.total_sources;
    """)

    # Create a materialized view for performance (optional, can be refreshed periodically)
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS gene_scores_cached AS
        SELECT * FROM gene_scores;
    """)

    # Create index on materialized view
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gene_scores_cached_gene_id
        ON gene_scores_cached(gene_id);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gene_scores_cached_percentage_score
        ON gene_scores_cached(percentage_score DESC);
    """)

    # Create function to refresh the materialized view
    op.execute("""
        CREATE OR REPLACE FUNCTION refresh_gene_scores()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY gene_scores_cached;
        END;
        $$ LANGUAGE plpgsql;
    """)

    print("Created enhanced views with percentage scoring and source tracking")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP FUNCTION IF EXISTS refresh_gene_scores() CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS gene_scores_cached CASCADE;")

    # Restore original gene_scores view
    op.execute("""
        CREATE OR REPLACE VIEW gene_scores AS
        WITH percentiles AS (
            SELECT
                gene_id,
                source_name,
                source_count_percentile
            FROM gene_evidence_with_percentiles
        )
        SELECT
            g.id AS gene_id,
            g.approved_symbol,
            g.hgnc_id,
            COUNT(DISTINCT p.source_name) AS source_count,
            COUNT(p.*) AS evidence_count,
            COALESCE(SUM(p.source_count_percentile), 0) AS total_score,
            jsonb_object_agg(
                p.source_name,
                p.source_count_percentile
            ) FILTER (WHERE p.source_name IS NOT NULL) AS source_percentiles
        FROM genes g
        LEFT JOIN percentiles p ON g.id = p.gene_id
        GROUP BY g.id, g.approved_symbol, g.hgnc_id;
    """)

    op.execute("DROP VIEW IF EXISTS source_count CASCADE;")
    op.execute("DROP VIEW IF EXISTS active_sources CASCADE;")
