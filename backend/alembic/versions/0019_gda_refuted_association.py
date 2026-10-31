"""Susceptibility gains the Refuted association class

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-31

ClinGen's risk-allele scheme (Schmidt 2024) has a Refuted association class
(#473), so ck_gda_strength is recreated with it. No data change. Downgrade
refuses while any record uses the new class.
"""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

T = "gene_disease_associations"
# Inline on purpose: migrations must not import model constants that may change later
MENDELIAN = (
    "'Definitive', 'Strong', 'Moderate', 'Limited', 'Disputed', 'Refuted', "
    "'No Known Disease Relationship'"
)
SUSCEPTIBILITY = "'Established association', 'Likely association', 'Uncertain association'"
REFUTED = "Refuted association"


def _strength_check(susceptibility: str) -> None:
    op.drop_constraint("ck_gda_strength", T, type_="check")
    op.create_check_constraint(
        "ck_gda_strength",
        T,
        f"(relationship_type = 'mendelian' AND evidence_strength IN ({MENDELIAN})) OR "
        f"(relationship_type = 'susceptibility' AND evidence_strength IN ({susceptibility}))",
    )


def upgrade() -> None:
    _strength_check(f"{SUSCEPTIBILITY}, '{REFUTED}'")


def downgrade() -> None:
    refuted = (
        op.get_bind()
        .execute(sa.text(f"SELECT count(*) FROM {T} WHERE evidence_strength = :s"), {"s": REFUTED})
        .scalar_one()
    )
    if refuted:
        raise RuntimeError(f"cannot downgrade 0019: {refuted} records use '{REFUTED}'")
    _strength_check(SUSCEPTIBILITY)
