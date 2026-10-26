"""Score GenCC by quality, agreeing submitters and conflict (#330)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-26

The GenCC branch of evidence_classification_weights took the MAX of fixed
classification weights. It now scores each gene from its submissions:
Q = strongest weight (as before); n = distinct non-ClinGen submitters agreeing
on the top class (ClinGen is a separate source, #282; n >= 1);
C = min(1, Q * (1 + 0.1 * ln n)); minus 0.1 when counted submitters' strongest
classes are >= 2 ranks apart (Supportive, Orphanet/OMIM's
ungraded term, has no rank); floored at 0. Rows without submissions keep the
MAX of 'classifications'. Formula: .planning/specs/2026-10-26-gencc-two-stage.md.

ClinGen and the output columns/types are unchanged (classification_weight stays
numeric), so CREATE OR REPLACE keeps dependent views intact. gene_scores and
gene_distribution_analysis are refreshed only when materialized. Stored
evidence rows are not modified. SQL is inlined (no runtime app.db imports).
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

# Two-stage GenCC CTEs (upgrade); must match app/db/views.py at this revision.
_TWO_STAGE = """
    WITH gencc_submissions AS (
        -- Two-stage GenCC score (#330, .planning/specs/2026-10-26-gencc-two-stage.md)
        SELECT ge.id AS evidence_id,
            NULLIF(btrim(s.value ->> 'submitter'::text), ''::text) AS submitter,
            CASE lower(btrim(s.value ->> 'classification'::text))
                WHEN 'definitive' THEN 1.0
                WHEN 'strong' THEN 0.8
                WHEN 'moderate' THEN 0.6
                WHEN 'supportive' THEN 0.5
                WHEN 'limited' THEN 0.4
                WHEN 'disputed evidence' THEN 0.2
                ELSE 0.0
            END AS weight,
            CASE lower(btrim(s.value ->> 'classification'::text))
                WHEN 'definitive' THEN 6
                WHEN 'strong' THEN 5
                WHEN 'moderate' THEN 4
                -- supportive: Orphanet/OMIM's ungraded term (DiStefano 2022, PMC7613247), not an ordinal grade
                WHEN 'limited' THEN 2
                WHEN 'disputed evidence' THEN 1
                WHEN 'no known disease relationship' THEN 0
                WHEN 'refuted evidence' THEN 0
                ELSE NULL  -- unranked: ignored for agreement and conflict
            END AS rank
        FROM gene_evidence ge
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE WHEN jsonb_typeof(ge.evidence_data -> 'submissions'::text) = 'array'::text
                THEN ge.evidence_data -> 'submissions'::text
                ELSE '[]'::jsonb
            END) s
        WHERE ge.source_name::text = 'GenCC'::text
    ), gencc_submitters AS (
        -- Counted submitters: ClinGen is a separate source (#282); strongest ranked class each
        SELECT evidence_id, submitter, MAX(rank) AS rank
        FROM gencc_submissions
        WHERE submitter IS NOT NULL AND submitter <> 'ClinGen'::text AND rank IS NOT NULL
        GROUP BY evidence_id, submitter
    ), gencc_quality AS (
        SELECT evidence_id, MAX(weight) AS q, MAX(rank) AS top_rank
        FROM gencc_submissions
        GROUP BY evidence_id
    ), gencc_consensus AS (
        SELECT gq.evidence_id,
            gq.q,
            GREATEST(1, COUNT(gs.submitter) FILTER (WHERE gs.rank = gq.top_rank)) AS n,
            COALESCE(MAX(gs.rank) - MIN(gs.rank), 0) AS rank_spread
        FROM gencc_quality gq
        LEFT JOIN gencc_submitters gs ON gs.evidence_id = gq.evidence_id
        GROUP BY gq.evidence_id, gq.q, gq.top_rank
    ), gencc_weighted AS (
        SELECT ge.id AS evidence_id,
            g.id AS gene_id,
            g.approved_symbol,
            ge.source_name,
            CASE WHEN gc.evidence_id IS NOT NULL THEN
                GREATEST(0.0,
                    LEAST(1.0, gc.q * (1.0 + 0.1 * ln(gc.n::numeric)))
                    - CASE WHEN gc.rank_spread >= 2 THEN 0.1 ELSE 0.0 END
                )::numeric
            -- Fallback for rows without submissions: MAX of classification weights
            ELSE COALESCE(
                (SELECT MAX(
                    CASE lower(replace(elem.value::text, '"', ''))
                        WHEN 'definitive' THEN 1.0
                        WHEN 'strong' THEN 0.8
                        WHEN 'moderate' THEN 0.6
                        WHEN 'supportive' THEN 0.5
                        WHEN 'limited' THEN 0.4
                        WHEN 'disputed evidence' THEN 0.2
                        WHEN 'no known disease relationship' THEN 0.0
                        ELSE 0.0  -- Unknown = no evidence
                    END
                ) FROM jsonb_array_elements(ge.evidence_data -> 'classifications') elem),
                0.0
            ) END AS classification_weight
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        LEFT JOIN gencc_consensus gc ON gc.evidence_id = ge.id
        WHERE ge.source_name::text = 'GenCC'::text
"""

# MAX of classification weights (revisions 0001-0005), restored on downgrade.
_MAX = """
    WITH gencc_weighted AS (
        SELECT ge.id AS evidence_id,
            g.id AS gene_id,
            g.approved_symbol,
            ge.source_name,
            COALESCE(
                (SELECT MAX(
                    CASE lower(replace(elem.value::text, '"', ''))
                        WHEN 'definitive' THEN 1.0
                        WHEN 'strong' THEN 0.8
                        WHEN 'moderate' THEN 0.6
                        WHEN 'supportive' THEN 0.5
                        WHEN 'limited' THEN 0.4
                        WHEN 'disputed evidence' THEN 0.2
                        WHEN 'no known disease relationship' THEN 0.0
                        ELSE 0.0
                    END
                ) FROM jsonb_array_elements(ge.evidence_data -> 'classifications') elem),
                0.0
            ) AS classification_weight
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        WHERE ge.source_name::text = 'GenCC'::text
"""

_REST = """\
    ), clingen_weights AS (
        SELECT ge.id AS evidence_id,
            g.id AS gene_id,
            g.approved_symbol,
            ge.source_name,
            CASE
                WHEN jsonb_typeof(ge.evidence_data -> 'classifications'::text) = 'array'::text THEN
                    -- Strongest classification, independent of array order (#279)
                    COALESCE(
                        (SELECT MAX(
                            CASE elem.value #>> '{}'
                                WHEN 'Definitive'::text THEN 1.0
                                WHEN 'Strong'::text THEN 0.8
                                WHEN 'Moderate'::text THEN 0.6
                                WHEN 'Limited'::text THEN 0.4
                                WHEN 'Disputed'::text THEN 0.2
                                WHEN 'No Known Disease Relationship'::text THEN 0.0
                                WHEN 'No Known Disease Relationship*'::text THEN 0.0
                                ELSE 0.0  -- Unknown = no evidence
                            END
                        ) FROM jsonb_array_elements(
                            ge.evidence_data -> 'classifications'::text) elem),
                        0.0
                    )
                WHEN (ge.evidence_data ->> 'classification'::text) IS NOT NULL THEN
                    CASE ge.evidence_data ->> 'classification'::text
                        WHEN 'Definitive'::text THEN 1.0
                        WHEN 'Strong'::text THEN 0.8
                        WHEN 'Moderate'::text THEN 0.6
                        WHEN 'Limited'::text THEN 0.4
                        WHEN 'Disputed'::text THEN 0.2
                        WHEN 'No Known Disease Relationship'::text THEN 0.0
                        WHEN 'No Known Disease Relationship*'::text THEN 0.0
                        ELSE 0.0  -- Unknown = no evidence
                    END
                ELSE 0.0  -- Unknown = no evidence
            END AS classification_weight
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        WHERE ge.source_name::text = 'ClinGen'::text
    )
    SELECT clingen_weights.evidence_id,
        clingen_weights.gene_id,
        clingen_weights.approved_symbol,
        clingen_weights.source_name,
        clingen_weights.classification_weight
    FROM clingen_weights
    UNION ALL
    SELECT gencc_weighted.evidence_id,
        gencc_weighted.gene_id,
        gencc_weighted.approved_symbol,
        gencc_weighted.source_name,
        gencc_weighted.classification_weight
    FROM gencc_weighted
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


def _apply(gencc: str) -> None:
    op.execute("CREATE OR REPLACE VIEW evidence_classification_weights AS" + gencc + _REST)
    op.execute(_REFRESH)


def upgrade() -> None:
    _apply(_TWO_STAGE)


def downgrade() -> None:
    _apply(_MAX)
