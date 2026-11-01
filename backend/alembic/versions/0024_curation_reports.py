"""Curation reports and per-user notification preferences

Revision ID: 0024
Revises: 0023
Create Date: 2026-11-01

Public problem/suggestion reports on curated associations (curators triage them) and the
user_notification_pref table behind email notifications (a missing row means enabled).
"""

import sqlalchemy as sa

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "curation_report",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("gene_id", sa.BigInteger(), sa.ForeignKey("genes.id"), nullable=False),
        sa.Column(
            "association_id",
            sa.BigInteger(),
            sa.ForeignKey("gene_disease_associations.id"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("reporter_name", sa.String(200), nullable=True),
        sa.Column("reporter_email", sa.String(320), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("handled_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("kind IN ('problem', 'suggestion')", name="ck_curation_report_kind"),
        sa.CheckConstraint(
            "status IN ('open', 'resolved', 'dismissed')", name="ck_curation_report_status"
        ),
    )
    op.create_index("ix_curation_report_status_gene", "curation_report", ["status", "gene_id"])
    op.create_table(
        "user_notification_pref",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("event", sa.String(40), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_notification_pref")
    op.drop_index("ix_curation_report_status_gene", table_name="curation_report")
    op.drop_table("curation_report")
