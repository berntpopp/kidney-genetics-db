"""AI-approved Gene Curator imports and their later KGDB human review

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-31

A Gene Curator export row approved only by an AI (#639) is imported published, without a KGDB
reviewer, and marked "pending human review" until a KGDB curator reviews it (human_reviewed_*).
Downgrade refuses while any AI-approved record exists: the old check needs a reviewer.
"""

import sqlalchemy as sa

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

T = "gene_disease_associations"
OLD_PUBLISHED = "status <> 'published' OR (reviewer_id IS NOT NULL AND published_at IS NOT NULL)"
# Inlined, not imported from the model: a later model change must not alter this revision
NEW_PUBLISHED = (
    "status <> 'published' OR (published_at IS NOT NULL "
    "AND (reviewer_id IS NOT NULL OR approval_kind = 'ai'))"
)
APPROVAL = (
    "(approval_kind IS NULL OR (source = 'gene_curator' AND approval_kind IN ('human', 'ai'))) "
    "AND (approval_model IS NULL OR approval_kind = 'ai') "
    "AND ((human_reviewed_at IS NULL) = (human_reviewer_id IS NULL)) "
    "AND (human_reviewed_at IS NULL OR approval_kind = 'ai')"
)


def upgrade() -> None:
    op.add_column(T, sa.Column("approval_kind", sa.String(10), nullable=True))
    op.add_column(T, sa.Column("approval_model", sa.String(100), nullable=True))
    op.add_column(T, sa.Column("human_reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        T,
        sa.Column("human_reviewer_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.drop_constraint("ck_gda_published_reviewed", T, type_="check")
    op.create_check_constraint("ck_gda_published_reviewed", T, NEW_PUBLISHED)
    op.create_check_constraint("ck_gda_approval", T, APPROVAL)


def downgrade() -> None:
    blocking = (
        op.get_bind()
        .execute(sa.text(f"SELECT count(*) FROM {T} WHERE approval_kind = 'ai'"))
        .scalar_one()
    )
    if blocking:
        raise RuntimeError(f"cannot downgrade 0023: {blocking} records are AI-approved")
    op.drop_constraint("ck_gda_approval", T, type_="check")
    op.drop_constraint("ck_gda_published_reviewed", T, type_="check")
    op.create_check_constraint("ck_gda_published_reviewed", T, OLD_PUBLISHED)
    for column in ("human_reviewer_id", "human_reviewed_at", "approval_model", "approval_kind"):
        op.drop_column(T, column)
