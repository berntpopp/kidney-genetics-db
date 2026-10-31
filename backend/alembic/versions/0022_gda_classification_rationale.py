"""Classification rationale kept apart from the synopsis

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-31

Gene Curator's curator_classification_rationale (why the final class departs from the point model
or from ClinGen) was appended to the synopsis; it gets its own column so the synopsis stays about
gene, disease and evidence. Existing appended notes are left as they are (none in production).
Downgrade refuses while any record carries a rationale.
"""

import sqlalchemy as sa

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

T = "gene_disease_associations"


def upgrade() -> None:
    op.add_column(T, sa.Column("classification_rationale", sa.Text(), nullable=True))


def downgrade() -> None:
    blocking = (
        op.get_bind()
        .execute(sa.text(f"SELECT count(*) FROM {T} WHERE classification_rationale IS NOT NULL"))
        .scalar_one()
    )
    if blocking:
        raise RuntimeError(f"cannot downgrade 0022: {blocking} records carry a rationale")
    op.drop_column(T, "classification_rationale")
