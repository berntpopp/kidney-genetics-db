"""fix_gene_hpo_classifications_view_remove_invalid_filter

Revision ID: cc1fbec614ed
Revises: d2f24d1ed798
Create Date: 2025-10-09 10:57:22.239594

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc1fbec614ed"
down_revision: str | Sequence[str] | None = "d2f24d1ed798"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - fix gene_hpo_classifications view by removing invalid valid_to filter."""
    # Drop and recreate the view with corrected WHERE clause
    op.execute("DROP VIEW IF EXISTS gene_hpo_classifications")
    op.execute("""
        CREATE VIEW gene_hpo_classifications AS
        SELECT
            g.id AS gene_id,
            g.approved_symbol AS gene_symbol,
            ga.annotations->'classification'->'clinical_group'->>'primary' AS clinical_group,
            ga.annotations->'classification'->'onset_group'->>'primary' AS onset_group,
            COALESCE(
                (ga.annotations->'classification'->'syndromic_assessment'->>'is_syndromic')::boolean,
                FALSE
            ) AS is_syndromic
        FROM genes g
        LEFT JOIN gene_annotations ga ON g.id = ga.gene_id AND ga.source = 'hpo'
    """)


def downgrade() -> None:
    """Downgrade schema - restore original view with valid_to filter."""
    # Restore original view (though it was broken)
    op.execute("DROP VIEW IF EXISTS gene_hpo_classifications")
    op.execute("""
        CREATE VIEW gene_hpo_classifications AS
        SELECT
            g.id AS gene_id,
            g.approved_symbol AS gene_symbol,
            ga.annotations->'classification'->'clinical_group'->>'primary' AS clinical_group,
            ga.annotations->'classification'->'onset_group'->>'primary' AS onset_group,
            COALESCE(
                (ga.annotations->'classification'->'syndromic_assessment'->>'is_syndromic')::boolean,
                FALSE
            ) AS is_syndromic
        FROM genes g
        LEFT JOIN gene_annotations ga ON g.id = ga.gene_id AND ga.source = 'hpo'
        WHERE g.valid_to = 'infinity'::timestamptz
    """)
