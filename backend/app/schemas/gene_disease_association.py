"""Schemas for expert-reviewed gene-disease association records (#26)."""

import re
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.models.gene_disease_association import (
    MENDELIAN_STRENGTHS,
    SUSCEPTIBILITY_STRENGTHS,
)

EvidenceStrength = Literal[
    "Definitive",
    "Strong",
    "Moderate",
    "Limited",
    "Disputed",
    "Refuted",
    "No Known Disease Relationship",
    "Established association",
    "Likely association",
    "Uncertain association",
]
AssociationStatus = Literal["draft", "in_review", "published"]
RelationshipType = Literal["mendelian", "susceptibility"]
Source = Literal["kgdb", "gene_curator"]
Moi = Literal[
    "HP:0000006",
    "HP:0000007",
    "HP:0001417",
    "HP:0001419",
    "HP:0001423",
    "HP:0032113",
    "HP:0001427",
    "HP:0001450",
    "HP:0010984",
    "HP:0001426",
]

_DISEASE_ID = re.compile(r"^(MONDO:\d{7}|OMIM:\d{6})$")
_PMID = re.compile(r"^(?:PMID:)?0*([1-9]\d{0,8})$")  # no PMID 0, no zero-padded duplicates


def _disease_id(value: str) -> str:
    value = value.strip().upper()
    if value.startswith("HP:"):
        raise ValueError(
            "HPO identifiers describe phenotypes, not diseases; use a MONDO or OMIM identifier"
        )
    if not _DISEASE_ID.match(value):
        raise ValueError("disease_id must be MONDO:NNNNNNN (7 digits) or OMIM:NNNNNN (6 digits)")
    return value


def _citations(values: list[str]) -> list[str]:
    normalised: list[str] = []
    for raw in values:
        match = _PMID.match(raw.strip().upper().replace(" ", ""))
        if not match:
            raise ValueError(f"invalid PMID '{raw}': use digits or PMID:digits")
        pmid = f"PMID:{match.group(1)}"
        if pmid not in normalised:
            normalised.append(pmid)
    return normalised


def _http_link(value: str) -> str:
    # Rendered as a link: anything but http(s) (javascript:, data:, ...) is refused
    if not re.match(r"^https?://\S+$", value):
        raise ValueError("links must start with http:// or https://")
    return value


DiseaseId = Annotated[str, AfterValidator(_disease_id)]
DiseaseName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Citations = Annotated[list[str], Field(min_length=1, max_length=100), AfterValidator(_citations)]
Summary = Annotated[str, Field(max_length=2000)]
HttpLink = Annotated[str, Field(max_length=2000), AfterValidator(_http_link)]


def _text(max_length: int, min_length: int = 0) -> Any:
    return Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=min_length, max_length=max_length)
    ]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Scores(_Strict):
    genetic: float | None = Field(None, ge=0, le=100)
    experimental: float | None = Field(None, ge=0, le=100)
    total: float | None = Field(None, ge=0, le=100)


class RecommendedTranscript(_Strict):
    refseq: Annotated[str, Field(pattern=r"^NM_\d+\.\d+$")] | None = None
    ensembl: Annotated[str, Field(pattern=r"^ENST\d{11}\.\d+$")] | None = None
    mane_status: Literal["select", "plus_clinical", "none", "not_checked"]
    legacy_transcript: _text(50) | None = None
    numbering_conversion: _text(500) | None = None


class DetectabilityTool(_Strict):
    name: _text(100, 1)
    url: HttpLink | None = None
    pmid_or_doi: _text(100) | None = None


class Detectability(_Strict):
    challenge: _text(300, 1)
    share_of_variants: _text(100) | None = None
    affected_variants: _text(300) | None = None
    methods: Annotated[list[_text(50, 1)], Field(max_length=20)] = []
    tools: Annotated[list[DetectabilityTool], Field(max_length=10)] = []
    negative_report_does_not_exclude: bool = False
    sources: Annotated[list[_text(300, 1)], Field(max_length=10)] = []


class Verified(_Strict):
    method: Literal["fetched", "api", "captcha_title_only"]
    date: date


class Resource(_Strict):
    type: Literal["patient_organisation", "registry", "variant_database", "guideline", "other"]
    name: _text(200, 1)
    url: HttpLink
    language: _text(20) | None = None
    audiences: Annotated[list[_text(50, 1)], Field(max_length=10)] = []
    maintainer: _text(200) | None = None
    conflict_of_interest: _text(500) | None = None
    verified: Verified


class Diagnostics(_Strict):
    """Non-scoring clinical diagnostics section (#439); never feeds a score."""

    recommended_transcript: RecommendedTranscript | None = None
    detectability: Annotated[list[Detectability], Field(max_length=20)] = []
    resources: Annotated[list[Resource], Field(max_length=50)] = []


def check_classification(relationship_type: str, strength: str) -> None:
    allowed = MENDELIAN_STRENGTHS if relationship_type == "mendelian" else SUSCEPTIBILITY_STRENGTHS
    if strength not in allowed:
        raise ValueError(
            f"'{strength}' is not a {relationship_type} classification; use one of: "
            + ", ".join(allowed)
        )


def check_provenance(source: str, external_id: str | None, external_url: str | None) -> None:
    if source == "gene_curator" and not (external_id and external_url):
        raise ValueError("a Gene Curator record needs external_id and external_url")


class _Provenance(BaseModel):
    """Fields shared by create and update (#437)."""

    moi: Moi | None = None
    methodology: _text(100, 1) | None = None
    methodology_version: _text(50, 1) | None = None
    external_id: _text(100, 1) | None = None
    external_url: HttpLink | None = None
    external_curator: _text(255, 1) | None = None
    external_reviewer: _text(255, 1) | None = None
    scores: Scores | None = None
    diagnostics: Diagnostics | None = None


class AssociationCreate(_Provenance):
    gene_symbol: str = Field(..., min_length=1, max_length=100)
    disease_id: DiseaseId
    disease_name: DiseaseName
    relationship_type: RelationshipType = "mendelian"
    evidence_strength: EvidenceStrength
    citations: Citations
    evidence_summary: Summary | None = None
    source: Source = "kgdb"

    @model_validator(mode="after")
    def _consistent(self) -> "AssociationCreate":
        check_classification(self.relationship_type, self.evidence_strength)
        check_provenance(self.source, self.external_id, self.external_url)
        return self


class AssociationUpdate(_Provenance):
    """Partial update of a draft; the gene is fixed once created.

    Classification and provenance consistency is checked by the service on the merged record.
    """

    disease_id: DiseaseId | None = None
    disease_name: DiseaseName | None = None
    relationship_type: RelationshipType | None = None
    evidence_strength: EvidenceStrength | None = None
    citations: Citations | None = None
    evidence_summary: Summary | None = None
    source: Source | None = None

    @model_validator(mode="after")
    def _required_not_null(self) -> "AssociationUpdate":
        # Omit a field to keep it; optional fields may be cleared with null
        for name in self.model_fields_set & _REQUIRED:
            if getattr(self, name) is None:
                raise ValueError(f"{name} must not be null")
        return self


_REQUIRED = {
    "disease_id",
    "disease_name",
    "relationship_type",
    "evidence_strength",
    "citations",
    "source",
}


class ReviewDecision(BaseModel):
    """The version the reviewer looked at; a record changed since then answers 409."""

    expected_updated_at: datetime


class AssociationResponse(BaseModel):
    id: int
    gene_id: int
    gene_symbol: str
    disease_id: str
    disease_name: str
    relationship_type: RelationshipType
    evidence_strength: EvidenceStrength
    moi: str | None = None
    moi_label: str | None = None
    methodology: str | None = None
    methodology_version: str | None = None
    citations: list[str]
    evidence_summary: str | None = None
    source: Source
    external_id: str | None = None
    external_url: str | None = None
    external_curator: str | None = None
    external_reviewer: str | None = None
    scores: dict[str, Any] | None = None
    diagnostics: dict[str, Any] | None = None
    status: AssociationStatus
    curator_id: int
    reviewer_id: int | None = None
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    published_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AssociationList(BaseModel):
    data: list[AssociationResponse]
    meta: dict[str, int]
