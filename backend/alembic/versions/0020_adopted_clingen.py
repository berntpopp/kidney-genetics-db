"""Adopted ClinGen classification, AI credit and the susceptibility risk allele

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-31

Gene Curator adopts ClinGen expert-panel classifications instead of re-curating
them (GC #105); such a curation has no PMID rows of its own. adopted_clingen
holds the ClinGen record (CGGV id, class, expert panel, date, link), and only
such a record may have empty citations. ai_agents lists the software agents GC
credits for the evidence (AI-assisted curation). A susceptibility entity is one
named risk allele (GC #614), so risk_allele joins the key (uq_gda_entity, NULLs
equal). Downgrade refuses while an adopted, allele-specific or AI-credited record
exists.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

T = "gene_disease_associations"
# Inline on purpose: migrations must not import model constants that may change later
PMIDS = r"""citations::text ~ '^\["PMID:[0-9]{1,9}"(, "PMID:[0-9]{1,9}")*\]$'"""


def upgrade() -> None:
    op.add_column(T, sa.Column("adopted_clingen", JSONB(), nullable=True))
    op.create_check_constraint(
        "ck_gda_adopted_clingen",
        T,
        "adopted_clingen IS NULL OR (source = 'gene_curator' "
        "AND jsonb_typeof(adopted_clingen) = 'object')",
    )
    op.add_column(T, sa.Column("ai_agents", JSONB(), nullable=True))
    op.create_check_constraint(
        "ck_gda_ai_agents",
        T,
        "ai_agents IS NULL OR (source = 'gene_curator' AND jsonb_typeof(ai_agents) = 'array')",
    )
    op.add_column(T, sa.Column("risk_allele", sa.String(100), nullable=True))
    op.create_check_constraint(
        "ck_gda_risk_allele", T, "risk_allele IS NULL OR relationship_type = 'susceptibility'"
    )
    op.drop_constraint("uq_gda_gene_disease_moi_relationship", T, type_="unique")
    op.execute(
        f"ALTER TABLE {T} ADD CONSTRAINT uq_gda_entity UNIQUE NULLS NOT DISTINCT "
        "(gene_id, disease_id, moi, relationship_type, risk_allele)"
    )
    op.drop_constraint("ck_gda_citations", T, type_="check")
    op.create_check_constraint(
        "ck_gda_citations",
        T,
        f"{PMIDS} OR (citations::text = '[]' AND adopted_clingen IS NOT NULL)",
    )


def downgrade() -> None:
    blocking = (
        op.get_bind()
        .execute(
            sa.text(
                f"SELECT count(*) FROM {T} "
                "WHERE adopted_clingen IS NOT NULL OR risk_allele IS NOT NULL OR ai_agents IS NOT NULL"
            )
        )
        .scalar_one()
    )
    if blocking:
        raise RuntimeError(
            f"cannot downgrade 0020: {blocking} records adopt a ClinGen class, name a risk allele or credit AI"
        )
    op.drop_constraint("uq_gda_entity", T, type_="unique")
    op.execute(
        f"ALTER TABLE {T} ADD CONSTRAINT uq_gda_gene_disease_moi_relationship "
        "UNIQUE NULLS NOT DISTINCT (gene_id, disease_id, moi, relationship_type)"
    )
    op.drop_constraint("ck_gda_risk_allele", T, type_="check")
    op.drop_column(T, "risk_allele")
    op.drop_constraint("ck_gda_citations", T, type_="check")
    op.create_check_constraint("ck_gda_citations", T, PMIDS)
    op.drop_constraint("ck_gda_ai_agents", T, type_="check")
    op.drop_column(T, "ai_agents")
    op.drop_constraint("ck_gda_adopted_clingen", T, type_="check")
    op.drop_column(T, "adopted_clingen")
