"""Score ClinGen evidence by its strongest classification (#279)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-20

The ClinGen branch of evidence_classification_weights read only
classifications[0], so array order decided the weight. It now takes the
maximum over all classifications, like the GenCC branch. Weight mapping,
scalar 'classification' fallback and the 0.0 default are unchanged.

Output columns and types are unchanged, so CREATE OR REPLACE keeps dependent
views intact. gene_scores is refreshed so existing data is rescored; stored
evidence rows are not modified. SQL is inlined (no runtime app.db imports).
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_WEIGHT = """
    CASE {expr}
        WHEN 'Definitive'::text THEN 1.0
        WHEN 'Strong'::text THEN 0.8
        WHEN 'Moderate'::text THEN 0.6
        WHEN 'Limited'::text THEN 0.4
        WHEN 'Disputed'::text THEN 0.2
        WHEN 'No Known Disease Relationship'::text THEN 0.0
        WHEN 'No Known Disease Relationship*'::text THEN 0.0
        ELSE 0.0
    END
"""

_MAX_ARRAY = (
    "COALESCE((SELECT MAX("
    + _WEIGHT.format(expr="elem.value #>> '{}'")
    + ") FROM jsonb_array_elements(ge.evidence_data -> 'classifications'::text) elem), 0.0)"
)
_FIRST_ELEMENT = _WEIGHT.format(expr="(ge.evidence_data -> 'classifications'::text) ->> 0")

_VIEW = """
    CREATE OR REPLACE VIEW evidence_classification_weights AS
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
    ), clingen_weights AS (
        SELECT ge.id AS evidence_id,
            g.id AS gene_id,
            g.approved_symbol,
            ge.source_name,
            CASE
                WHEN jsonb_typeof(ge.evidence_data -> 'classifications'::text) = 'array'::text
                    THEN {array_weight}
                WHEN (ge.evidence_data ->> 'classification'::text) IS NOT NULL
                    THEN {scalar_weight}
                ELSE 0.0
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


def _apply(array_weight: str) -> None:
    scalar_weight = _WEIGHT.format(expr="ge.evidence_data ->> 'classification'::text")
    op.execute(_VIEW.format(array_weight=array_weight, scalar_weight=scalar_weight))
    op.execute("REFRESH MATERIALIZED VIEW gene_scores")


def upgrade() -> None:
    _apply(_MAX_ARRAY)


def downgrade() -> None:
    _apply(_FIRST_ELEMENT)
