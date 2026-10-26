"""Statistics and annotation-summary matviews in Alembic; gene_scores divisor once (#367)

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-26

- source_overlap_statistics (read by /api/statistics/summary) existed only in
  app/db/materialized_views.py and was never created on Alembic-built databases.
- gene_annotations_summary was created ad hoc at startup without an index, so
  every REFRESH ... CONCURRENTLY failed and fell back to a blocking refresh.
  Both are (re)created here with a unique index; a pre-existing copy (production
  was not built purely by Alembic) is dropped first so the definition is known.
- gene_scores computed COUNT(DISTINCT source_name) over the scoring chain in 9
  scalar subqueries; it is now one CTE cross-joined in. Output is unchanged.
  Materialized views cannot be replaced, so gene_scores is dropped with CASCADE
  and every dependent view (gene_list_detailed, plus any found in the database)
  is recreated from its stored definition and indexes.

SQL is inlined (no runtime app.db imports); downgrade restores 0008's
gene_scores and drops the two matviews.
"""

from sqlalchemy import text

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

# Must match app/db/views.py gene_scores.
_GENE_SCORES = """
    WITH source_scores_per_gene AS (
        SELECT g.id AS gene_id,
               g.approved_symbol,
               g.hgnc_id,
               ces.source_name,
               MAX(ces.normalized_score) AS source_score
        FROM genes g
        INNER JOIN combined_evidence_scores ces ON g.id = ces.gene_id
        GROUP BY g.id, g.approved_symbol, g.hgnc_id, ces.source_name
    ), active_sources AS (
        -- Computed once (#367); every percentage below divides by it
        SELECT COUNT(DISTINCT source_name) AS n FROM combined_evidence_scores
    )
    SELECT gene_id,
           approved_symbol,
           hgnc_id,
           COUNT(DISTINCT source_name) AS source_count,
           COUNT(DISTINCT source_name) AS evidence_count,  -- Alias for backward compatibility
           SUM(source_score) AS raw_score,
           -- Sum of scores divided by total possible sources, as percentage.
           -- Global divisor on purpose: rewards breadth across sources (#333,
           -- .planning/specs/2026-10-21-scoring-percentile-divisor.md)
           SUM(source_score) / a.n * 100 AS percentage_score,
           -- Source breakdown
           jsonb_object_agg(source_name, ROUND(source_score::numeric, 4))
               AS source_scores,
           -- Total active sources for reference
           a.n AS total_active_sources,
           -- Evidence tier classification
           CASE
               WHEN COUNT(DISTINCT source_name) >= 4 AND SUM(source_score) / a.n * 100 >= 50
                   THEN 'comprehensive_support'
               WHEN COUNT(DISTINCT source_name) >= 3 AND SUM(source_score) / a.n * 100 >= 35
                   THEN 'multi_source_support'
               WHEN COUNT(DISTINCT source_name) >= 2 AND SUM(source_score) / a.n * 100 >= 20
                   THEN 'established_support'
               WHEN SUM(source_score) / a.n * 100 >= 10
                   THEN 'preliminary_evidence'
               WHEN SUM(source_score) / a.n * 100 > 0
                   THEN 'minimal_evidence'
               ELSE 'no_evidence'
           END AS evidence_tier,
           -- Evidence group classification
           CASE
               WHEN COUNT(DISTINCT source_name) >= 2 AND SUM(source_score) / a.n * 100 >= 20
                   THEN 'well_supported'
               WHEN SUM(source_score) / a.n * 100 > 0
                   THEN 'emerging_evidence'
               ELSE 'insufficient'
           END AS evidence_group
    FROM source_scores_per_gene
    CROSS JOIN active_sources a
    GROUP BY gene_id, approved_symbol, hgnc_id, a.n
"""

# 0001-0008 definition (downgrade).
_GENE_SCORES_0008 = """
    WITH source_scores_per_gene AS (
        SELECT g.id AS gene_id,
               g.approved_symbol,
               g.hgnc_id,
               ces.source_name,
               MAX(ces.normalized_score) AS source_score
        FROM genes g
        INNER JOIN combined_evidence_scores ces ON g.id = ces.gene_id
        GROUP BY g.id, g.approved_symbol, g.hgnc_id, ces.source_name
    )
    SELECT gene_id,
           approved_symbol,
           hgnc_id,
           COUNT(DISTINCT source_name) AS source_count,
           COUNT(DISTINCT source_name) AS evidence_count,  -- Alias for backward compatibility
           SUM(source_score) AS raw_score,
           -- Sum of scores divided by total possible sources, as percentage.
           -- Global divisor on purpose: rewards breadth across sources (#333,
           -- .planning/specs/2026-10-21-scoring-percentile-divisor.md)
           SUM(source_score) /
               (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
               * 100 AS percentage_score,
           -- Source breakdown
           jsonb_object_agg(source_name, ROUND(source_score::numeric, 4))
               AS source_scores,
           -- Total active sources for reference
           (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
               AS total_active_sources,
           -- Evidence tier classification
           CASE
               WHEN COUNT(DISTINCT source_name) >= 4 AND SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 >= 50
                   THEN 'comprehensive_support'
               WHEN COUNT(DISTINCT source_name) >= 3 AND SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 >= 35
                   THEN 'multi_source_support'
               WHEN COUNT(DISTINCT source_name) >= 2 AND SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 >= 20
                   THEN 'established_support'
               WHEN SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 >= 10
                   THEN 'preliminary_evidence'
               WHEN SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 > 0
                   THEN 'minimal_evidence'
               ELSE 'no_evidence'
           END AS evidence_tier,
           -- Evidence group classification
           CASE
               WHEN COUNT(DISTINCT source_name) >= 2 AND SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 >= 20
                   THEN 'well_supported'
               WHEN SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 > 0
                   THEN 'emerging_evidence'
               ELSE 'insufficient'
           END AS evidence_group
    FROM source_scores_per_gene
    GROUP BY gene_id, approved_symbol, hgnc_id
"""

_GENE_SCORES_INDEXES = (
    "CREATE UNIQUE INDEX idx_gene_scores_gene_id ON gene_scores (gene_id)",
    "CREATE INDEX idx_gene_scores_percentage_score ON gene_scores (percentage_score)",
    "CREATE INDEX idx_gene_scores_evidence_tier ON gene_scores (evidence_tier)",
)

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

# Views depending (transitively) on gene_scores, deepest last, with their indexes.
_DEPENDENTS = """
    WITH RECURSIVE dep(oid, depth) AS (
        SELECT DISTINCT r.ev_class, 1
        FROM pg_depend d JOIN pg_rewrite r ON r.oid = d.objid
        WHERE d.classid = 'pg_rewrite'::regclass AND d.refobjid = 'gene_scores'::regclass
            AND r.ev_class <> d.refobjid
        UNION ALL
        SELECT DISTINCT r.ev_class, dep.depth + 1
        FROM dep JOIN pg_depend d ON d.refobjid = dep.oid
        JOIN pg_rewrite r ON r.oid = d.objid
        WHERE d.classid = 'pg_rewrite'::regclass AND r.ev_class <> d.refobjid
    )
    SELECT c.relname, c.relkind, pg_get_viewdef(c.oid),
        ARRAY(SELECT pg_get_indexdef(i.indexrelid) FROM pg_index i WHERE i.indrelid = c.oid)
    FROM (SELECT oid, MAX(depth) AS depth FROM dep GROUP BY oid) d
    JOIN pg_class c ON c.oid = d.oid
    ORDER BY d.depth, c.relname
"""


def _replace_gene_scores(sql: str) -> None:
    dependents = op.get_bind().execute(text(_DEPENDENTS)).all()
    op.execute("DROP MATERIALIZED VIEW gene_scores CASCADE")
    op.execute(f"CREATE MATERIALIZED VIEW gene_scores AS {sql}")
    for index in _GENE_SCORES_INDEXES:
        op.execute(index)
    for name, kind, definition, indexes in dependents:
        kind_sql = "MATERIALIZED VIEW" if kind == "m" else "VIEW"
        op.execute(f'CREATE {kind_sql} "{name}" AS {definition}')
        for index in indexes:
            op.execute(index)


def upgrade() -> None:
    _replace_gene_scores(_GENE_SCORES)
    op.execute("DROP MATERIALIZED VIEW IF EXISTS source_overlap_statistics")
    op.execute(f"CREATE MATERIALIZED VIEW source_overlap_statistics AS {_SOURCE_OVERLAP}")
    op.execute(
        "CREATE UNIQUE INDEX idx_source_overlap_sources "
        "ON source_overlap_statistics (source1, source2)"
    )
    op.execute("DROP MATERIALIZED VIEW IF EXISTS gene_annotations_summary")
    op.execute(f"CREATE MATERIALIZED VIEW gene_annotations_summary AS {_ANNOTATIONS_SUMMARY}")
    op.execute(
        "CREATE UNIQUE INDEX idx_gene_annotations_summary_gene_id "
        "ON gene_annotations_summary (gene_id)"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS gene_annotations_summary")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS source_overlap_statistics")
    _replace_gene_scores(_GENE_SCORES_0008)
