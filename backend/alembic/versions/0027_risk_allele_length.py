"""Widen gene_disease_associations.risk_allele to 255 characters

Revision ID: 0027
Revises: 0026
Create Date: 2026-11-03

Gene Curator names some risk alleles in more than 100 characters (APOL1).
"""

import sqlalchemy as sa

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "gene_disease_associations",
        "risk_allele",
        type_=sa.String(255),
        existing_type=sa.String(100),
        existing_nullable=True,
    )


def downgrade() -> None:
    # fails, rather than truncating, if a stored risk allele is longer than 100 characters
    op.alter_column(
        "gene_disease_associations",
        "risk_allele",
        type_=sa.String(100),
        existing_type=sa.String(255),
        existing_nullable=True,
    )
