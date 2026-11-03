"""Gene Curator "no primary kidney association" assessments

Revision ID: 0028
Revises: 0027
Create Date: 2026-11-03

Gene-level, so apart from gene_disease_associations, which name a disease (#535).
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

TABLE = "gene_no_association_assessments"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("gene_id", sa.BigInteger(), sa.ForeignKey("genes.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence_summary", sa.Text(), nullable=True),
        sa.Column("sources_checked", JSONB(), nullable=False),
        sa.Column("non_kidney_entities", JSONB(), nullable=False),
        sa.Column("methodology", sa.String(100), nullable=True),
        sa.Column("methodology_version", sa.String(50), nullable=True),
        sa.Column("external_id", sa.String(100), nullable=False, unique=True),
        sa.Column("external_url", sa.Text(), nullable=False),
        sa.Column("external_curator", sa.String(255), nullable=True),
        sa.Column("external_reviewer", sa.String(255), nullable=True),
        sa.Column("ai_agents", JSONB(), nullable=True),
        sa.Column("approval_kind", sa.String(10), nullable=False, server_default="human"),
        sa.Column("approval_model", sa.String(100), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_gnaa_status"),
        sa.CheckConstraint("external_url ~ '^https?://'", name="ck_gnaa_external_url"),
        sa.CheckConstraint(
            "approval_kind IN ('human', 'ai') AND (approval_model IS NULL OR approval_kind = 'ai')",
            name="ck_gnaa_approval",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(sources_checked) = 'array' AND jsonb_typeof(non_kidney_entities) = "
            "'array' AND (ai_agents IS NULL OR jsonb_typeof(ai_agents) = 'array')",
            name="ck_gnaa_json_arrays",
        ),
    )
    op.create_index(f"ix_{TABLE}_gene_id", TABLE, ["gene_id"])
    # One active assessment per gene; replaced ones stay as archived history
    op.create_index(
        "uq_gnaa_active_gene",
        TABLE,
        ["gene_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_gnaa_active_gene", table_name=TABLE)
    op.drop_index(f"ix_{TABLE}_gene_id", table_name=TABLE)
    op.drop_table(TABLE)
