"""Schemas for expert-reviewed gene-disease association records (#26)."""

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

EvidenceStrength = Literal["Definitive", "Strong", "Moderate", "Limited", "Disputed", "Refuted"]
AssociationStatus = Literal["draft", "in_review", "published"]

_DISEASE_ID = re.compile(r"^(MONDO:\d{7}|OMIM:\d{6})$")
_PMID = re.compile(r"^(?:PMID:)?(\d{1,9})$")


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


DiseaseId = Annotated[str, AfterValidator(_disease_id)]
DiseaseName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Citations = Annotated[list[str], Field(min_length=1, max_length=100), AfterValidator(_citations)]
Summary = Annotated[str, Field(max_length=2000)]


class AssociationCreate(BaseModel):
    gene_symbol: str = Field(..., min_length=1, max_length=100)
    disease_id: DiseaseId
    disease_name: DiseaseName
    evidence_strength: EvidenceStrength
    citations: Citations
    evidence_summary: Summary | None = None


class AssociationUpdate(BaseModel):
    """Partial update of a draft; the gene is fixed once created."""

    disease_id: DiseaseId | None = None
    disease_name: DiseaseName | None = None
    evidence_strength: EvidenceStrength | None = None
    citations: Citations | None = None
    evidence_summary: Summary | None = None

    @model_validator(mode="after")
    def _required_not_null(self) -> "AssociationUpdate":
        # Omit a field to keep it; only evidence_summary may be cleared with null
        for name in self.model_fields_set - {"evidence_summary"}:
            if getattr(self, name) is None:
                raise ValueError(f"{name} must not be null")
        return self


class AssociationResponse(BaseModel):
    id: int
    gene_id: int
    gene_symbol: str
    disease_id: str
    disease_name: str
    evidence_strength: EvidenceStrength
    citations: list[str]
    evidence_summary: str | None = None
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
