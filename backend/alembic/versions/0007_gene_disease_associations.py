"""Add expert-reviewed gene-disease association records (#26)

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-26

Creates gene_disease_associations only: several MONDO/OMIM disease records
per gene, PMID citations, curator/reviewer ids and timestamps, and a
draft -> in_review -> published status. No existing table, view or evidence
row is read or modified. Downgrade drops only this table. SQL is inlined.
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        r"""
        CREATE TABLE gene_disease_associations (
            id BIGSERIAL PRIMARY KEY,
            gene_id BIGINT NOT NULL REFERENCES genes (id),
            disease_id VARCHAR(20) NOT NULL,
            disease_name VARCHAR(255) NOT NULL,
            evidence_strength VARCHAR(20) NOT NULL,
            citations JSONB NOT NULL,
            evidence_summary TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'draft',
            curator_id BIGINT NOT NULL REFERENCES users (id),
            reviewer_id BIGINT REFERENCES users (id),
            submitted_at TIMESTAMPTZ,
            reviewed_at TIMESTAMPTZ,
            published_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_gda_gene_disease UNIQUE (gene_id, disease_id),
            CONSTRAINT ck_gda_disease_id
                CHECK (disease_id ~ '^(MONDO:[0-9]{7}|OMIM:[0-9]{6})$'),
            CONSTRAINT ck_gda_strength CHECK (evidence_strength IN
                ('Definitive', 'Strong', 'Moderate', 'Limited', 'Disputed', 'Refuted')),
            CONSTRAINT ck_gda_status CHECK (status IN ('draft', 'in_review', 'published')),
            CONSTRAINT ck_gda_citations
                CHECK (citations::text ~ '^\["PMID:[0-9]{1,9}"(, "PMID:[0-9]{1,9}")*\]$'),
            CONSTRAINT ck_gda_distinct_reviewer
                CHECK (reviewer_id IS NULL OR reviewer_id <> curator_id),
            CONSTRAINT ck_gda_published_reviewed CHECK (
                status <> 'published' OR (reviewer_id IS NOT NULL AND published_at IS NOT NULL)
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_gene_disease_associations_gene_id ON gene_disease_associations (gene_id)"
    )
    op.execute(
        "CREATE INDEX ix_gene_disease_associations_status ON gene_disease_associations (status)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE gene_disease_associations")
