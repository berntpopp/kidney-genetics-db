"""Score minimum-count evidence above zero with cume_dist (#337)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-21

evidence_count_percentiles used percent_rank(), which is (rank - 1) / (n - 1):
every gene tied at a source's minimum count scored exactly 0, so genes whose
only evidence was, for example, a single PubTator publication fell into
no_evidence. cume_dist() is the share of genes with a count <= this one, in
(0, 1], so any evidence scores above 0 and the maximum stays 1.

The column keeps its name and double precision type, so CREATE OR REPLACE
keeps dependent views intact. gene_scores (and gene_distribution_analysis,
which reads it) are refreshed only when they are materialized views; a plain
view needs no refresh. The percentage divisor stays the global number of
active sources (#333). Stored evidence rows are not modified. SQL is inlined.
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_VIEW = """
    CREATE OR REPLACE VIEW evidence_count_percentiles AS
    SELECT evidence_source_counts.evidence_id,
        evidence_source_counts.gene_id,
        evidence_source_counts.approved_symbol,
        evidence_source_counts.source_name,
        evidence_source_counts.source_count,
        {rank}() OVER (
            PARTITION BY evidence_source_counts.source_name
            ORDER BY LN(1.0 + evidence_source_counts.source_count)
        ) AS percentile_score
    FROM evidence_source_counts
    WHERE evidence_source_counts.source_count > 0
"""

_REFRESH = """
    DO $$
    DECLARE mv text;
    BEGIN
        FOREACH mv IN ARRAY ARRAY['gene_scores', 'gene_distribution_analysis'] LOOP
            IF EXISTS (SELECT 1 FROM pg_matviews WHERE matviewname = mv) THEN
                EXECUTE format('REFRESH MATERIALIZED VIEW %I', mv);
            END IF;
        END LOOP;
    END $$;
"""


def _apply(rank: str) -> None:
    op.execute(_VIEW.format(rank=rank))
    op.execute(_REFRESH)


def upgrade() -> None:
    _apply("cume_dist")


def downgrade() -> None:
    _apply("percent_rank")
