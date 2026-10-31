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
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text

from app.models.base import Base, TimestampMixin

RELATIONSHIP_TYPES = ("mendelian", "susceptibility")
MENDELIAN_STRENGTHS = (
    "Definitive",
    "Strong",
    "Moderate",
    "Limited",
    "Disputed",
    "Refuted",
    "No Known Disease Relationship",
)
# ClinGen risk-allele tiers plus Refuted association (Schmidt 2024; #437, #439, #473)
SUSCEPTIBILITY_STRENGTHS = (
    "Established association",
    "Likely association",
    "Uncertain association",
    "Refuted association",
)
EVIDENCE_STRENGTHS = MENDELIAN_STRENGTHS + SUSCEPTIBILITY_STRENGTHS
STATUSES = ("draft", "in_review", "published")
SOURCES = ("kgdb", "gene_curator")
# HPO mode-of-inheritance terms, labels from the pinned hp.json (HPO 2026-09-01)
MOI_TERMS = {
    "HP:0000006": "Autosomal dominant inheritance",
    "HP:0000007": "Autosomal recessive inheritance",
    "HP:0001417": "X-linked inheritance",
    "HP:0001419": "X-linked recessive inheritance",
    "HP:0001423": "X-linked dominant inheritance",
    "HP:0032113": "Semidominant inheritance",
    "HP:0001427": "Mitochondrial inheritance",
    "HP:0001450": "Y-linked inheritance",
    "HP:0010984": "Digenic inheritance",
    "HP:0001426": "Non-Mendelian inheritance",
    "HP:0010982": "Polygenic inheritance",  # GC's "Multifactorial (polygenic)" option (#619)
}


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class GeneDiseaseAssociation(Base, TimestampMixin):
    """One reviewed association between a gene and a MONDO/OMIM disease."""

    __tablename__ = "gene_disease_associations"
    __table_args__ = (
        # NULLS NOT DISTINCT: two records without an MOI (or allele) still collide (0013, 0018,
        # 0020); a susceptibility entity is one named risk allele
        UniqueConstraint(
            "gene_id",
            "disease_id",
            "moi",
            "relationship_type",
            "risk_allele",
            name="uq_gda_entity",
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "uq_gda_source_external_id",
            "source",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        CheckConstraint(
            r"disease_id ~ '^(MONDO:[0-9]{7}|OMIM:[0-9]{6})$'", name="ck_gda_disease_id"
        ),
        CheckConstraint(
            f"(relationship_type = 'mendelian' AND {_in('evidence_strength', MENDELIAN_STRENGTHS)})"
            f" OR (relationship_type = 'susceptibility'"
            f" AND {_in('evidence_strength', SUSCEPTIBILITY_STRENGTHS)})",
            name="ck_gda_strength",
        ),
        CheckConstraint(
            _in("relationship_type", RELATIONSHIP_TYPES), name="ck_gda_relationship_type"
        ),
        CheckConstraint(r"moi IS NULL OR moi ~ '^HP:[0-9]{7}$'", name="ck_gda_moi"),
        CheckConstraint(_in("source", SOURCES), name="ck_gda_source"),
        CheckConstraint(
            "external_url IS NULL OR external_url ~ '^https?://'", name="ck_gda_external_url"
        ),
        CheckConstraint(
            "source = 'kgdb' OR (external_id IS NOT NULL AND external_url IS NOT NULL)",
            name="ck_gda_external",
        ),
        CheckConstraint(
            "scores IS NULL OR jsonb_typeof(scores) = 'object'", name="ck_gda_scores_object"
        ),
        CheckConstraint(
            "diagnostics IS NULL OR jsonb_typeof(diagnostics) = 'object'",
            name="ck_gda_diagnostics_object",
        ),
        CheckConstraint(_in("status", STATUSES), name="ck_gda_status"),
        # jsonb renders arrays canonically as ["a", "b"], so one regex checks every element
        CheckConstraint(
            r"""citations::text ~ '^\["PMID:[0-9]{1,9}"(, "PMID:[0-9]{1,9}")*\]$' OR """
            r"""(citations::text = '[]' AND adopted_clingen IS NOT NULL)""",
            name="ck_gda_citations",
        ),
        CheckConstraint(
            "adopted_clingen IS NULL OR (source = 'gene_curator' "
            "AND jsonb_typeof(adopted_clingen) = 'object')",
            name="ck_gda_adopted_clingen",
        ),
        CheckConstraint(
            "risk_allele IS NULL OR relationship_type = 'susceptibility'",
            name="ck_gda_risk_allele",
        ),
        CheckConstraint(
            "ai_agents IS NULL OR (source = 'gene_curator' AND jsonb_typeof(ai_agents) = 'array')",
            name="ck_gda_ai_agents",
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
    evidence_strength = Column(String(40), nullable=False)
    relationship_type = Column(String(20), nullable=False, server_default="mendelian")
    moi = Column(String(10), nullable=True)
    risk_allele = Column(String(100), nullable=True)  # susceptibility: the named allele
    methodology = Column(String(100), nullable=True)
    methodology_version = Column(String(50), nullable=True)
    # Where the curation was made; a KGDB curator other than the author still publishes it
    source = Column(String(20), nullable=False, server_default="kgdb")
    external_id = Column(String(100), nullable=True)
    external_url = Column(Text, nullable=True)
    external_curator = Column(String(255), nullable=True)
    external_reviewer = Column(String(255), nullable=True)
    # none_as_null: Python None must be SQL NULL, not JSON null (object checks)
    scores = Column(JSONB(none_as_null=True), nullable=True)
    diagnostics = Column(JSONB(none_as_null=True), nullable=True)  # non-scoring (#439)
    # A ClinGen classification adopted in Gene Curator instead of curated there
    adopted_clingen = Column(JSONB(none_as_null=True), nullable=True)
    # Software agents Gene Curator credits for writing evidence rows (AI-assisted curation)
    ai_agents = Column(JSONB(none_as_null=True), nullable=True)
    citations = Column(JSONB, nullable=False)
    evidence_summary = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, server_default="draft", index=True)
    curator_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    reviewer_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    gene = relationship("Gene")
    curator = relationship("User", foreign_keys=[curator_id])

    def __repr__(self) -> str:
        return f"<GeneDiseaseAssociation(gene_id={self.gene_id}, disease_id='{self.disease_id}')>"


class GeneDiseaseAssociationEvent(Base):
    """Append-only trace of every curation action, with the record as it was afterwards."""

    __tablename__ = "gene_disease_association_events"

    id = Column(BigInteger, primary_key=True)
    association_id = Column(
        BigInteger, ForeignKey("gene_disease_associations.id"), nullable=False, index=True
    )
    action = Column(String(20), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    snapshot = Column(JSONB, nullable=False)
