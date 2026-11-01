"""Volunteer curator applications

Revision ID: 0025
Revises: 0024
Create Date: 2026-11-01

Public applications to curate a gene; approval by an admin creates or links the account.
"""

import sqlalchemy as sa

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "volunteer_application",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("gene_id", sa.BigInteger(), sa.ForeignKey("genes.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("affiliation", sa.String(300), nullable=True),
        sa.Column("orcid", sa.String(19), nullable=True),
        sa.Column("motivation", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("decided_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_volunteer_application_status"
        ),
    )
    op.create_index(
        "ix_volunteer_application_status_created",
        "volunteer_application",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_volunteer_application_status_created", table_name="volunteer_application")
    op.drop_table("volunteer_application")
