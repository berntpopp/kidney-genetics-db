"""Headline odds ratio of a susceptibility association (#482)

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-31

A susceptibility record may carry the curation's headline odds ratio of its risk allele,
with an optional 95% CI, so the UI can flag a modest effect (OR < 2). Downgrade refuses
while any record carries one.
"""

import sqlalchemy as sa

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

T = "gene_disease_associations"
COLUMNS = ("odds_ratio", "odds_ratio_ci_low", "odds_ratio_ci_high")
# Inline on purpose: migrations must not import model constants that may change later.
# COALESCE: a NULL CI bound must fail the check, not pass it as unknown.
CHECK = (
    "(odds_ratio IS NULL AND odds_ratio_ci_low IS NULL AND odds_ratio_ci_high IS NULL) OR "
    "COALESCE(relationship_type = 'susceptibility' AND odds_ratio > 0 AND ("
    "(odds_ratio_ci_low IS NULL AND odds_ratio_ci_high IS NULL) OR (odds_ratio_ci_low > 0 "
    "AND odds_ratio_ci_low <= odds_ratio AND odds_ratio <= odds_ratio_ci_high)), false)"
)


def upgrade() -> None:
    for name in COLUMNS:
        op.add_column(T, sa.Column(name, sa.Float(), nullable=True))
    op.create_check_constraint("ck_gda_odds_ratio", T, CHECK)


def downgrade() -> None:
    blocking = (
        op.get_bind()
        .execute(sa.text(f"SELECT count(*) FROM {T} WHERE odds_ratio IS NOT NULL"))
        .scalar_one()
    )
    if blocking:
        raise RuntimeError(f"cannot downgrade 0021: {blocking} records carry an odds ratio")
    op.drop_constraint("ck_gda_odds_ratio", T, type_="check")
    for name in COLUMNS:
        op.drop_column(T, name)
