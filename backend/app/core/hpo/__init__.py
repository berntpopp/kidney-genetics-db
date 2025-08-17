"""
HPO (Human Phenotype Ontology) API client modules.

This package provides a modular, extensible architecture for interacting with
the HPO API, including term hierarchy traversal, gene-disease-phenotype
annotations, and inheritance pattern extraction.
"""

from app.core.hpo.annotations import HPOAnnotations
from app.core.hpo.base import HPOAPIBase
from app.core.hpo.models import (
    Disease,
    DiseaseAnnotations,
    Gene,
    GeneInfo,
    HPOTerm,
    InheritancePattern,
    Phenotype,
    SearchResults,
    TermAnnotations,
)
from app.core.hpo.terms import HPOTerms

__all__ = [
    # Base classes
    "HPOAPIBase",
    # API modules
    "HPOTerms",
    "HPOAnnotations",
    # Models
    "HPOTerm",
    "Gene",
    "Disease",
    "InheritancePattern",
    "Phenotype",
    "TermAnnotations",
    "DiseaseAnnotations",
    "GeneInfo",
    "SearchResults",
]