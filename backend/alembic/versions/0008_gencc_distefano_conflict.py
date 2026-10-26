"""Use DiStefano et al. 2022 Level 3 conflicts for GenCC (#330)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-26

0006's GenCC conflict penalty fired when counted submitters' strongest classes
across the whole gene were >= 2 ordinal ranks apart. It now uses the published
definition (DiStefano et al. 2022, Genet Med, PMC7613247): "a conflict was
defined as a Limited/Disputed/Refuted assertion versus a
Moderate/Strong/Definitive assertion", at the paper's Level 3: "“Level 3
conflicts” were those where gene, disease term, and mode of inheritance all
matched but gene-disease validity terms conflicted" (Levels 1 and 2 match on
gene only, or on gene and mode of inheritance only).

Conflict iff some group of submissions with the same gene, disease
(raw_data.disease_curie) and mode of inheritance (raw_data.moi_curie) has,
over counted (non-ClinGen) submitters' strongest class within that group, one
Definitive/Strong/Moderate and one Limited/Disputed Evidence/Refuted
Evidence/No Known Disease Relationship. A submission with a missing or empty
disease_curie or moi_curie never forms a conflict. Supportive is in neither
set. NKDR is not named in the definition; it is placed with Refuted following
the paper's "Limited or below (including ... No Known Disease Relationship)"
grouping; on the 2026-10-26 dev snapshot this affects C4B only. Q, n (agreement on the top class across the gene), the cap, the 0.1
penalty, the legacy fallback and the numeric column type are unchanged.
Spec: .planning/specs/2026-10-26-gencc-two-stage.md.

0006 is not edited in place because v0.10.0 shipped it. CREATE OR REPLACE keeps
dependent views; gene_scores and gene_distribution_analysis are refreshed only
when materialized. Stored evidence rows are not modified. SQL is inlined (no
runtime app.db imports); downgrade restores 0006's definition exactly.
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

# GenCC CTEs with DiStefano Level 3 conflicts (upgrade); must match app/db/views.py.
_DISTEFANO = """
    WITH gencc_submissions AS (
        -- Two-stage GenCC score (#330, .planning/specs/2026-10-26-gencc-two-stage.md)
        SELECT ge.id AS evidence_id,
            NULLIF(btrim(s.value ->> 'submitter'::text), ''::text) AS submitter,
            NULLIF(btrim(s.value -> 'raw_data'::text ->> 'disease_curie'::text), ''::text) AS disease,
            NULLIF(btrim(s.value -> 'raw_data'::text ->> 'moi_curie'::text), ''::text) AS moi,
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
    ), gencc_groups AS (
        -- DiStefano 2022 (PMC7613247) Level 3: same gene, disease and MOI; strongest class per
        -- counted submitter in each group. Missing disease or MOI never forms a conflict.
        SELECT evidence_id, disease, moi, submitter, MAX(rank) AS rank
        FROM gencc_submissions
        WHERE submitter IS NOT NULL AND submitter <> 'ClinGen'::text AND rank IS NOT NULL
            AND disease IS NOT NULL AND moi IS NOT NULL
        GROUP BY evidence_id, disease, moi, submitter
    ), gencc_conflicts AS (
        -- Limited/Disputed/Refuted/NKDR vs Moderate/Strong/Definitive within one group
        SELECT DISTINCT evidence_id
        FROM gencc_groups
        GROUP BY evidence_id, disease, moi
        HAVING bool_or(rank >= 4) AND bool_or(rank <= 2)
    ), gencc_quality AS (
        SELECT evidence_id, MAX(weight) AS q, MAX(rank) AS top_rank
        FROM gencc_submissions
        GROUP BY evidence_id
    ), gencc_consensus AS (
        SELECT gq.evidence_id,
            gq.q,
            GREATEST(1, COUNT(gs.submitter) FILTER (WHERE gs.rank = gq.top_rank)) AS n
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
                    - CASE WHEN gx.evidence_id IS NOT NULL THEN 0.1 ELSE 0.0 END
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
        LEFT JOIN gencc_conflicts gx ON gx.evidence_id = ge.id
        WHERE ge.source_name::text = 'GenCC'::text
"""

# GenCC CTEs of revision 0006 (>= 2-rank conflict rule), restored on downgrade.
_RANK_SPREAD = """
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
    _apply(_DISTEFANO)


def downgrade() -> None:
    _apply(_RANK_SPREAD)
