"""Require an assertion source for established support and above (#450)

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-30

A gene reached established_support (and evidence_group well_supported) on two
count-derived sources alone, e.g. HPO + PubTator percentiles. It now needs at
least one curated gene-disease assertion source (ClinGen, GenCC, PanelApp,
DiagnosticPanels) for established_support, multi_source_support,
comprehensive_support and well_supported; genes with only HPO, PubTator,
Literature (or any other non-assertion source) cap at preliminary_evidence /
emerging_evidence. percentage_score and source_scores are unchanged.

gene_scores is a materialized view, so it is dropped and recreated with its
indexes; every view built on it (gene_list_detailed, plus any ad hoc view or
matview such as gene_distribution_analysis where it exists) is recreated from
its live definition and indexes. Grants and comments are not carried over.
SQL is inlined (no runtime app.db imports); downgrade restores the 0013
definition exactly. Stored evidence rows are not modified.
"""

from sqlalchemy import text

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

# gene_scores with the assertion-source rule (upgrade); must match app/db/views.py.
_ASSERTION_GATED = """
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
           -- Evidence tier classification. Established support and above need a
           -- gene-disease assertion source; count-only sources cap at preliminary (#450)
           CASE
               WHEN NOT bool_or(source_name IN ('ClinGen', 'GenCC', 'PanelApp', 'DiagnosticPanels'))
                   AND SUM(source_score) /
                   (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores)
                   * 100 >= 10
                   THEN 'preliminary_evidence'
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
               WHEN COUNT(DISTINCT source_name) >= 2
                   AND bool_or(source_name IN ('ClinGen', 'GenCC', 'PanelApp', 'DiagnosticPanels'))
                   AND SUM(source_score) /
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

# gene_scores of revision 0013 (restored on downgrade).
_UNGATED = """
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


# Views and matviews built on gene_scores, deepest last (production may hold ad hoc ones,
# e.g. gene_distribution_analysis); recreated from their live definitions and indexes.
_DEPENDENTS = """
    WITH RECURSIVE dep(oid, depth) AS (
        SELECT r.ev_class, 1
        FROM pg_depend d JOIN pg_rewrite r ON r.oid = d.objid
        WHERE d.refobjid = 'gene_scores'::regclass AND r.ev_class <> d.refobjid
        UNION
        SELECT r.ev_class, dep.depth + 1
        FROM dep JOIN pg_depend d ON d.refobjid = dep.oid JOIN pg_rewrite r ON r.oid = d.objid
        WHERE r.ev_class <> d.refobjid
    )
    SELECT c.relname, c.relkind, pg_get_viewdef(c.oid),
        ARRAY(SELECT indexdef FROM pg_indexes i
              WHERE i.schemaname = n.nspname AND i.tablename = c.relname)
    FROM (SELECT oid, max(depth) AS depth FROM dep GROUP BY oid) x
    JOIN pg_class c ON c.oid = x.oid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    ORDER BY x.depth, c.relname
"""


def _replace(sql: str) -> None:
    dependents = op.get_bind().execute(text(_DEPENDENTS)).all()
    op.execute("DROP MATERIALIZED VIEW gene_scores CASCADE")
    op.execute("CREATE MATERIALIZED VIEW gene_scores AS" + sql)
    op.execute("CREATE UNIQUE INDEX idx_gene_scores_gene_id ON gene_scores (gene_id)")
    op.execute("CREATE INDEX idx_gene_scores_percentage_score ON gene_scores (percentage_score)")
    op.execute("CREATE INDEX idx_gene_scores_evidence_tier ON gene_scores (evidence_tier)")
    for name, kind, definition, indexes in dependents:
        op.execute(
            f"CREATE {'MATERIALIZED VIEW' if kind == 'm' else 'VIEW'} {name} AS {definition}"
        )
        for index in indexes:
            op.execute(index)


def upgrade() -> None:
    _replace(_ASSERTION_GATED)


def downgrade() -> None:
    _replace(_UNGATED)
