"""Statistics and annotation-summary matviews in Alembic (#367)

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-26

- source_overlap_statistics (read by /api/statistics/summary) existed only in
  app/db/materialized_views.py and was never created on Alembic-built databases.
- gene_annotations_summary was created ad hoc at startup without an index, so
  every REFRESH ... CONCURRENTLY failed and fell back to a blocking refresh.
  Both are (re)created here with a unique index; a pre-existing copy (production
  was not built purely by Alembic) is dropped first so the definition is known.

gene_scores is deliberately left untouched: nothing here drops or rebuilds the
scoring view or its dependents. SQL is inlined (no runtime app.db imports).
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

# 0001-0008 definition (downgrade).
# Must match app/db/materialized_views.py.
_SOURCE_OVERLAP = """
    WITH source_totals AS (
        SELECT source_name, COUNT(DISTINCT gene_id) AS total
        FROM gene_evidence
        GROUP BY source_name
    )
    SELECT
        e1.source_name AS source1,
        e2.source_name AS source2,
        COUNT(DISTINCT e1.gene_id)::integer AS overlap_count,
        st1.total::integer AS source1_total,
        st2.total::integer AS source2_total,
        ROUND(
            COUNT(DISTINCT e1.gene_id)::numeric /
            NULLIF(st1.total, 0) * 100,
            2
        )::float8 AS overlap_percentage
    FROM gene_evidence e1
    JOIN gene_evidence e2
        ON e1.gene_id = e2.gene_id
        AND e1.source_name < e2.source_name
    JOIN source_totals st1 ON st1.source_name = e1.source_name
    JOIN source_totals st2 ON st2.source_name = e2.source_name
    GROUP BY e1.source_name, e2.source_name, st1.total, st2.total
"""

# Formerly created by app/core/database_init.py.
_ANNOTATIONS_SUMMARY = """
    SELECT
        g.id as gene_id,
        g.approved_symbol,
        g.hgnc_id,
        ga_hgnc.annotations->>'ncbi_gene_id' as ncbi_gene_id,
        ga_hgnc.annotations->>'ensembl_gene_id' as ensembl_gene_id,
        ga_hgnc.annotations->>'mane_select' as mane_select_transcript,
        (ga_gnomad.annotations->>'pLI')::float as pli,
        (ga_gnomad.annotations->>'oe_lof')::float as oe_lof,
        (ga_gnomad.annotations->>'oe_lof_upper')::float as oe_lof_upper,
        (ga_gnomad.annotations->>'oe_lof_lower')::float as oe_lof_lower,
        (ga_gnomad.annotations->>'lof_z')::float as lof_z,
        (ga_gnomad.annotations->>'mis_z')::float as mis_z,
        (ga_gnomad.annotations->>'syn_z')::float as syn_z,
        (ga_gnomad.annotations->>'oe_mis')::float as oe_mis,
        (ga_gnomad.annotations->>'oe_syn')::float as oe_syn
    FROM genes g
    LEFT JOIN gene_annotations ga_hgnc ON g.id = ga_hgnc.gene_id AND ga_hgnc.source = 'hgnc'
    LEFT JOIN gene_annotations ga_gnomad ON g.id = ga_gnomad.gene_id AND ga_gnomad.source = 'gnomad'
"""


def _drop_view(name: str) -> None:
    """Drop a leftover copy whether it is a plain or a materialized view."""
    op.execute(
        f"""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_matviews WHERE matviewname = '{name}') THEN
                DROP MATERIALIZED VIEW {name};
            ELSIF EXISTS (SELECT 1 FROM pg_views WHERE viewname = '{name}') THEN
                DROP VIEW {name};
            END IF;
        END $$
        """
    )


def upgrade() -> None:
    _drop_view("source_overlap_statistics")
    op.execute(f"CREATE MATERIALIZED VIEW source_overlap_statistics AS {_SOURCE_OVERLAP}")
    op.execute(
        "CREATE UNIQUE INDEX idx_source_overlap_sources "
        "ON source_overlap_statistics (source1, source2)"
    )
    _drop_view("gene_annotations_summary")
    op.execute(f"CREATE MATERIALIZED VIEW gene_annotations_summary AS {_ANNOTATIONS_SUMMARY}")
    op.execute(
        "CREATE UNIQUE INDEX idx_gene_annotations_summary_gene_id "
        "ON gene_annotations_summary (gene_id)"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS gene_annotations_summary")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS source_overlap_statistics")
