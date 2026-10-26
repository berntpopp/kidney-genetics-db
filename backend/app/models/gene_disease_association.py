"""Expert-reviewed gene-disease association records (#26).

Written only through the curation service; no pipeline or aggregation code
references this table, so automated updates cannot overwrite expert decisions.
"""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin

EVIDENCE_STRENGTHS = ("Definitive", "Strong", "Moderate", "Limited", "Disputed", "Refuted")
STATUSES = ("draft", "in_review", "published")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class GeneDiseaseAssociation(Base, TimestampMixin):
    """One reviewed association between a gene and a MONDO/OMIM disease."""

    __tablename__ = "gene_disease_associations"
    __table_args__ = (
        UniqueConstraint("gene_id", "disease_id", name="uq_gda_gene_disease"),
        CheckConstraint(
            r"disease_id ~ '^(MONDO:[0-9]{7}|OMIM:[0-9]{6})$'", name="ck_gda_disease_id"
        ),
        CheckConstraint(_in("evidence_strength", EVIDENCE_STRENGTHS), name="ck_gda_strength"),
        CheckConstraint(_in("status", STATUSES), name="ck_gda_status"),
        # jsonb renders arrays canonically as ["a", "b"], so one regex checks every element
        CheckConstraint(
            r"""citations::text ~ '^\["PMID:[0-9]{1,9}"(, "PMID:[0-9]{1,9}")*\]$'""",
            name="ck_gda_citations",
        ),
        CheckConstraint(
            "reviewer_id IS NULL OR reviewer_id <> curator_id", name="ck_gda_distinct_reviewer"
        ),
        CheckConstraint(
            "status <> 'published' OR (reviewer_id IS NOT NULL AND published_at IS NOT NULL)",
            name="ck_gda_published_reviewed",
        ),
    )

    id = Column(BigInteger, primary_key=True)
    # No ON DELETE CASCADE: deleting a gene must not silently drop expert records
    gene_id = Column(BigInteger, ForeignKey("genes.id"), nullable=False, index=True)
    disease_id = Column(String(20), nullable=False)
    disease_name = Column(String(255), nullable=False)
    evidence_strength = Column(String(20), nullable=False)
    citations = Column(JSONB, nullable=False)
    evidence_summary = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, server_default="draft", index=True)
    curator_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    reviewer_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    gene = relationship("Gene")

    def __repr__(self) -> str:
        return f"<GeneDiseaseAssociation(gene_id={self.gene_id}, disease_id='{self.disease_id}')>"
