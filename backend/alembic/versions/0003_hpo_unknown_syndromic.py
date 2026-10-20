"""Keep unassessed genes NULL in gene_hpo_classifications.is_syndromic (#253)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-20

COALESCE(..., FALSE) turned "no HPO assessment" into "isolated". The column
keeps its name and boolean type, so CREATE OR REPLACE is sufficient; nothing
depends on this view. Stored annotations are not modified. SQL is inlined.
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_VIEW = """
    CREATE OR REPLACE VIEW gene_hpo_classifications AS
    SELECT
        g.id AS gene_id,
        g.approved_symbol AS gene_symbol,
        ga.annotations->'classification'->'clinical_group'->>'primary' AS clinical_group,
        ga.annotations->'classification'->'onset_group'->>'primary' AS onset_group,
        {is_syndromic} AS is_syndromic
    FROM genes g
    LEFT JOIN gene_annotations ga ON g.id = ga.gene_id AND ga.source = 'hpo'
"""
_ASSESSED = "(ga.annotations->'classification'->'syndromic_assessment'->>'is_syndromic')::boolean"


def upgrade() -> None:
    op.execute(_VIEW.format(is_syndromic=_ASSESSED))


def downgrade() -> None:
    op.execute(_VIEW.format(is_syndromic=f"COALESCE({_ASSESSED}, FALSE)"))
