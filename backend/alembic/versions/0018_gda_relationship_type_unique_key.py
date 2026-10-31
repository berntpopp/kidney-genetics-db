"""Relationship type joins the curated-association key

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-31

A Mendelian and a susceptibility record for one gene, disease and MOI are
distinct claims (#472), so the key becomes gene + disease + MOI + relationship
type, with NULL MOIs still equal. Downgrade refuses while rows differ only by
relationship type.
"""

import sqlalchemy as sa

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

T = "gene_disease_associations"


def upgrade() -> None:
    op.drop_constraint("uq_gda_gene_disease_moi", T, type_="unique")
    op.execute(
        f"ALTER TABLE {T} ADD CONSTRAINT uq_gda_gene_disease_moi_relationship "
        "UNIQUE NULLS NOT DISTINCT (gene_id, disease_id, moi, relationship_type)"
    )


def downgrade() -> None:
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                f"SELECT count(*) - count(DISTINCT (gene_id, disease_id, coalesce(moi, ''))) FROM {T}"
            )
        )
        .scalar_one()
    )
    if duplicates:
        raise RuntimeError(
            f"cannot downgrade 0018: {duplicates} records share gene, disease and MOI"
            " with another relationship type"
        )
    op.drop_constraint("uq_gda_gene_disease_moi_relationship", T, type_="unique")
    op.execute(
        f"ALTER TABLE {T} ADD CONSTRAINT uq_gda_gene_disease_moi "
        "UNIQUE NULLS NOT DISTINCT (gene_id, disease_id, moi)"
    )
