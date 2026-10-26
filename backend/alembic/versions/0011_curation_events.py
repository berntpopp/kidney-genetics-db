"""Append-only trace of curation actions on gene-disease associations

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-26

Returning a published record to draft overwrote reviewer_id and cleared
published_at, so nothing showed who had published which version, or when it went
offline. Every curation action now appends the record as it was afterwards.
Existing records get one 'import' event with their current state, attributed to
their curator, so each record's trace starts somewhere.

Downgrade drops the table and its trace.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gene_disease_association_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "association_id",
            sa.BigInteger(),
            sa.ForeignKey("gene_disease_associations.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
    )
    op.create_index(
        "ix_gene_disease_association_events_association_id",
        "gene_disease_association_events",
        ["association_id"],
    )
    op.create_index(
        "ix_gene_disease_association_events_user_id",
        "gene_disease_association_events",
        ["user_id"],
    )
    op.execute(
        """
        INSERT INTO gene_disease_association_events (association_id, action, user_id, at, snapshot)
        SELECT id, 'import', curator_id, updated_at, to_jsonb(g) FROM gene_disease_associations g
        """
    )


def downgrade() -> None:
    op.drop_table("gene_disease_association_events")
