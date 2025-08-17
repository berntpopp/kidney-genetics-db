"""
Pydantic models for HPO API responses and data structures.
"""

from typing import Any

from pydantic import BaseModel, Field


class HPOTerm(BaseModel):
    """HPO term model."""

    id: str
    name: str
    definition: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    is_obsolete: bool = False
    replaced_by: str | None = None
    children: list[str] = Field(default_factory=list)
    parents: list[str] = Field(default_factory=list)


class Gene(BaseModel):
    """Gene model from HPO."""

    id: str  # NCBIGene:XXXXX
    name: str  # Gene symbol

    @property
    def symbol(self) -> str:
        """Get gene symbol (alias for name)."""
        return self.name

    @property
    def entrez_id(self) -> int | None:
        """Extract numeric Entrez ID from NCBIGene identifier."""
        if self.id and self.id.startswith("NCBIGene:"):
            try:
                return int(self.id.split(":")[1])
            except (ValueError, IndexError):
                pass
        return None


class Disease(BaseModel):
    """Disease model from HPO."""

    id: str  # Disease ID (e.g., OMIM:XXXXX, ORPHA:XXXXX) from HPO API
    name: str
    mondoId: str | None = Field(None, alias="mondoId")
    description: str | None = None

    class Config:
        populate_by_name = True


class InheritancePattern(BaseModel):
    """Inheritance pattern model."""

    hpo_id: str = Field(alias="id")
    name: str
    frequency: str | None = None
    sources: list[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class PhenotypeMetadata(BaseModel):
    """Metadata for phenotype annotations."""

    sex: str | None = ""
    onset: str | None = ""
    frequency: str | None = ""
    sources: list[str] = Field(default_factory=list)


class Phenotype(BaseModel):
    """Phenotype annotation model."""

    id: str  # HPO term ID
    name: str
    category: str
    metadata: PhenotypeMetadata = Field(default_factory=PhenotypeMetadata)


class TermAnnotations(BaseModel):
    """Annotations for an HPO term."""

    genes: list[Gene] = Field(default_factory=list)
    diseases: list[Disease] = Field(default_factory=list)
    assays: list[dict] = Field(default_factory=list)
    medicalActions: list[dict] = Field(default_factory=list, alias="medicalActions")

    class Config:
        populate_by_name = True


class DiseaseCategories(BaseModel):
    """Disease phenotype categories."""

    inheritance: list[InheritancePattern] = Field(default_factory=list, alias="Inheritance")
    genitourinary_system: list[Phenotype] = Field(default_factory=list, alias="Genitourinary system")

    class Config:
        populate_by_name = True
        extra = "allow"  # Allow additional categories

    def get_all_phenotypes(self) -> list[Phenotype]:
        """Get all phenotypes from all categories except inheritance."""
        phenotypes = []
        for field_name, field_value in self:
            if field_name != "inheritance" and isinstance(field_value, list):
                for item in field_value:
                    if isinstance(item, dict):
                        phenotypes.append(Phenotype(
                            id=item.get("id", ""),
                            name=item.get("name", ""),
                            category=field_name.replace("_", " ").title(),
                            metadata=PhenotypeMetadata(**item.get("metadata", {}))
                        ))
        return phenotypes


class DiseaseAnnotations(BaseModel):
    """Comprehensive disease annotations."""

    disease: dict | None = None
    genes: list[Gene] = Field(default_factory=list)
    categories: dict[str, Any] = Field(default_factory=dict)
    medicalActions: list[dict] = Field(default_factory=list, alias="medicalActions")

    class Config:
        populate_by_name = True

    @property
    def disease_id(self) -> str | None:
        """Extract disease ID."""
        if self.disease:
            return self.disease.get("diseaseId")
        return None

    @property
    def disease_name(self) -> str | None:
        """Extract disease name."""
        if self.disease:
            return self.disease.get("diseaseName")
        return None

    def get_inheritance_patterns(self) -> list[InheritancePattern]:
        """Extract inheritance patterns from categories."""
        patterns = []
        inheritance_data = self.categories.get("Inheritance", [])

        for item in inheritance_data:
            patterns.append(InheritancePattern(
                id=item.get("id", ""),
                name=item.get("name", ""),
                frequency=item.get("metadata", {}).get("frequency"),
                sources=item.get("metadata", {}).get("sources", [])
            ))

        return patterns

    def get_phenotypes(self) -> list[Phenotype]:
        """Extract all phenotypes from categories."""
        phenotypes = []

        for category_name, items in self.categories.items():
            if category_name != "Inheritance" and isinstance(items, list):
                for item in items:
                    phenotypes.append(Phenotype(
                        id=item.get("id", ""),
                        name=item.get("name", ""),
                        category=category_name,
                        metadata=PhenotypeMetadata(**item.get("metadata", {}))
                    ))

        return phenotypes


class GeneInfo(BaseModel):
    """Detailed gene information from HPO browser."""

    gene_id: str = Field(alias="geneId")
    gene_symbol: str = Field(alias="geneSymbol")
    gene_name: str | None = Field(None, alias="geneName")
    entrez_id: int | None = Field(None, alias="entrezId")
    phenotypes: list[HPOTerm] = Field(default_factory=list)
    diseases: list[Disease] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class SearchResults(BaseModel):
    """Search results across HPO."""

    terms: list[HPOTerm] = Field(default_factory=list)
    genes: list[Gene] = Field(default_factory=list)
    diseases: list[Disease] = Field(default_factory=list)
