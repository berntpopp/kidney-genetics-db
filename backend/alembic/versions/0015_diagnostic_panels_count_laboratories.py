"""DiagnosticPanels score counts laboratories, not panel names

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-30

evidence_source_counts counted a gene's DiagnosticPanels evidence as its number
of distinct panel names, so one laboratory with many sub-panels (Blueprint
Genetics lists 24) outweighed several laboratories with one panel each. The
count is now provider_count, falling back to the length of providers; the
percentile (cume_dist over LN(1 + count)), percentage_score and the 0014 tier
rule are unchanged. Stored evidence rows are not modified.

The column keeps its name and bigint type, so CREATE OR REPLACE keeps every
dependent view (and its grants and indexes) in place; materialized views
built on it (gene_scores, and ad hoc ones such as gene_distribution_analysis
where they exist) are refreshed, deepest last. SQL is inlined (no
runtime app.db imports); downgrade restores the 0014 definition exactly.
"""

from sqlalchemy import text

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

# evidence_source_counts; {dp} is the DiagnosticPanels count. Must match app/db/views.py.
_VIEW = """
    CREATE OR REPLACE VIEW evidence_source_counts AS
    SELECT ge.id AS evidence_id,
        ge.gene_id,
        g.approved_symbol,
        ge.source_name,
        CASE ge.source_name
            WHEN 'PanelApp'::text THEN
                (COALESCE(jsonb_array_length(ge.evidence_data -> 'panels'::text),
                    0))::bigint
            WHEN 'HPO'::text THEN
                ((COALESCE(jsonb_array_length(ge.evidence_data -> 'hpo_terms'::text), 0)
                + COALESCE(jsonb_array_length(ge.evidence_data -> 'diseases'::text),
                    0)))::bigint
            WHEN 'PubTator'::text THEN
                (COALESCE((ge.evidence_data ->> 'publication_count'::text)::integer,
                jsonb_array_length(ge.evidence_data -> 'pmids'::text)))::bigint
            WHEN 'DiagnosticPanels'::text THEN
                {dp}
            WHEN 'GenCC'::text THEN
                (COALESCE(jsonb_array_length(
                    ge.evidence_data -> 'classifications'::text), 0))::bigint
            WHEN 'ClinGen'::text THEN
                (COALESCE((ge.evidence_data ->> 'assertion_count'::text)::integer,
                    1))::bigint
            WHEN 'Literature'::text THEN
                (COALESCE((ge.evidence_data ->> 'publication_count'::text)::integer,
                jsonb_array_length(ge.evidence_data -> 'publications'::text)))::bigint
            ELSE (0)::bigint
        END AS source_count
    FROM gene_evidence ge
    JOIN genes g ON ge.gene_id = g.id
"""

_LABORATORIES = """(COALESCE((ge.evidence_data ->> 'provider_count'::text)::integer,
                jsonb_array_length(ge.evidence_data -> 'providers'::text)))::bigint"""

# Revision 0014's count (restored on downgrade).
_PANEL_NAMES = """(COALESCE((ge.evidence_data ->> 'panel_count'::text)::integer,
                jsonb_array_length(ge.evidence_data -> 'panels'::text)))::bigint"""

# Materialized views built on evidence_source_counts, deepest last.
_MATVIEWS = """
    WITH RECURSIVE dep(oid, depth) AS (
        SELECT r.ev_class, 1
        FROM pg_depend d JOIN pg_rewrite r ON r.oid = d.objid
        WHERE d.refobjid = 'evidence_source_counts'::regclass AND r.ev_class <> d.refobjid
        UNION
        SELECT r.ev_class, dep.depth + 1
        FROM dep JOIN pg_depend d ON d.refobjid = dep.oid JOIN pg_rewrite r ON r.oid = d.objid
        WHERE r.ev_class <> d.refobjid
    )
    SELECT c.relname
    FROM (SELECT oid, max(depth) AS depth FROM dep GROUP BY oid) x
    JOIN pg_class c ON c.oid = x.oid
    WHERE c.relkind = 'm'
    ORDER BY x.depth, c.relname
"""


def _apply(dp: str) -> None:
    op.execute(_VIEW.format(dp=dp))
    for (name,) in op.get_bind().execute(text(_MATVIEWS)).all():
        op.execute(f'REFRESH MATERIALIZED VIEW "{name}"')


def upgrade() -> None:
    _apply(_LABORATORIES)


def downgrade() -> None:
    _apply(_PANEL_NAMES)
