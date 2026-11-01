"""Curated kidney clinical group on gene-disease associations

Revision ID: 0026
Revises: 0025
Create Date: 2026-11-01

Gene Curator curations name the entity's kidney clinical group (primary, secondary, rationale),
using the same keys as the HPO clinical groups on gene pages. Descriptive only, never scores.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None

T = "gene_disease_associations"
# Inlined, not imported from the model: a later model change must not alter this revision
GROUPS = (
    "'complement', 'cakut', 'glomerulopathy', 'cyst_cilio', 'tubulopathy', "
    "'nephrolithiasis', 'neoplasia'"
)


def upgrade() -> None:
    op.add_column(T, sa.Column("clinical_group", JSONB(none_as_null=True), nullable=True))
    op.create_check_constraint(
        "ck_gda_clinical_group",
        T,
        f"clinical_group IS NULL OR clinical_group->>'primary' IN ({GROUPS})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_gda_clinical_group", T, type_="check")
    op.drop_column(T, "clinical_group")
