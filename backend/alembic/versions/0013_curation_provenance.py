"""Relationship type, MOI, methodology, provenance and diagnostics on curated associations

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-30

A curated association could not record its inheritance mode, a susceptibility
(risk) relationship, the methodology it followed, where it was curated (Gene
Curator) or its non-scoring diagnostics section (#437, #439). Existing rows
become Mendelian KGDB records; no existing constraint is relaxed. The entity
key becomes gene + disease + MOI (ClinGen's unit), with NULL MOIs equal.

Downgrade refuses while any row uses something 0012 cannot hold.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

T = "gene_disease_associations"
# Inline on purpose: migrations must not import model constants that may change later
MENDELIAN = (
    "'Definitive', 'Strong', 'Moderate', 'Limited', 'Disputed', 'Refuted', "
    "'No Known Disease Relationship'"
)
SUSCEPTIBILITY = "'Established association', 'Likely association', 'Uncertain association'"
OLD_STRENGTHS = "'Definitive', 'Strong', 'Moderate', 'Limited', 'Disputed', 'Refuted'"
CHECKS = {
    "ck_gda_relationship_type": "relationship_type IN ('mendelian', 'susceptibility')",
    "ck_gda_moi": "moi IS NULL OR moi ~ '^HP:[0-9]{7}$'",
    "ck_gda_source": "source IN ('kgdb', 'gene_curator')",
    "ck_gda_external_url": "external_url IS NULL OR external_url ~ '^https?://'",
    "ck_gda_external": "source = 'kgdb' OR (external_id IS NOT NULL AND external_url IS NOT NULL)",
    "ck_gda_scores_object": "scores IS NULL OR jsonb_typeof(scores) = 'object'",
    "ck_gda_diagnostics_object": "diagnostics IS NULL OR jsonb_typeof(diagnostics) = 'object'",
}


def upgrade() -> None:
    op.add_column(
        T,
        sa.Column("relationship_type", sa.String(20), nullable=False, server_default="mendelian"),
    )
    op.add_column(T, sa.Column("moi", sa.String(10), nullable=True))
    op.add_column(T, sa.Column("methodology", sa.String(100), nullable=True))
    op.add_column(T, sa.Column("methodology_version", sa.String(50), nullable=True))
    op.add_column(T, sa.Column("source", sa.String(20), nullable=False, server_default="kgdb"))
    op.add_column(T, sa.Column("external_id", sa.String(100), nullable=True))
    op.add_column(T, sa.Column("external_url", sa.Text(), nullable=True))
    op.add_column(T, sa.Column("external_curator", sa.String(255), nullable=True))
    op.add_column(T, sa.Column("external_reviewer", sa.String(255), nullable=True))
    op.add_column(T, sa.Column("scores", postgresql.JSONB(), nullable=True))
    op.add_column(T, sa.Column("diagnostics", postgresql.JSONB(), nullable=True))
    op.alter_column(T, "evidence_strength", type_=sa.String(40), existing_nullable=False)

    op.drop_constraint("ck_gda_strength", T, type_="check")
    op.create_check_constraint(
        "ck_gda_strength",
        T,
        f"(relationship_type = 'mendelian' AND evidence_strength IN ({MENDELIAN})) OR "
        f"(relationship_type = 'susceptibility' AND evidence_strength IN ({SUSCEPTIBILITY}))",
    )
    for name, condition in CHECKS.items():
        op.create_check_constraint(name, T, condition)

    op.drop_constraint("uq_gda_gene_disease", T, type_="unique")
    op.execute(
        f"ALTER TABLE {T} ADD CONSTRAINT uq_gda_gene_disease_moi "
        "UNIQUE NULLS NOT DISTINCT (gene_id, disease_id, moi)"
    )
    op.create_index(
        "uq_gda_source_external_id",
        T,
        ["source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    blockers = (
        op.get_bind()
        .execute(
            sa.text(
                f"SELECT count(*) FILTER (WHERE relationship_type = 'susceptibility'),"
                f" count(*) FILTER (WHERE evidence_strength NOT IN ({OLD_STRENGTHS})),"
                f" count(*) - count(DISTINCT (gene_id, disease_id)),"
                " count(*) FILTER (WHERE source <> 'kgdb' OR num_nonnulls(moi, methodology,"
                " methodology_version, external_id, external_url, external_curator,"
                f" external_reviewer, scores, diagnostics) > 0) FROM {T}"
            )
        )
        .one()
    )
    if any(blockers):
        raise RuntimeError(
            "cannot downgrade 0013: rows use what 0012 cannot hold "
            f"(susceptibility={blockers[0]}, strengths={blockers[1]}, "
            f"duplicates={blockers[2]}, MOI/provenance/points/diagnostics={blockers[3]})"
        )
    op.drop_index("uq_gda_source_external_id", table_name=T)
    op.drop_constraint("uq_gda_gene_disease_moi", T, type_="unique")
    op.create_unique_constraint("uq_gda_gene_disease", T, ["gene_id", "disease_id"])
    for name in CHECKS:
        op.drop_constraint(name, T, type_="check")
    op.drop_constraint("ck_gda_strength", T, type_="check")
    op.create_check_constraint("ck_gda_strength", T, f"evidence_strength IN ({OLD_STRENGTHS})")
    op.alter_column(T, "evidence_strength", type_=sa.String(20), existing_nullable=False)
    for column in (
        "diagnostics",
        "scores",
        "external_reviewer",
        "external_curator",
        "external_url",
        "external_id",
        "source",
        "methodology_version",
        "methodology",
        "moi",
        "relationship_type",
    ):
        op.drop_column(T, column)
