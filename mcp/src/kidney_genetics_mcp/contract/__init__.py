"""KGDB API contract — generated from the backend OpenAPI snapshot.

This package is the single source of truth for the *contract values* the curated
MCP tools / services / allowlist consume: API path templates, gene filter / sort
vocabularies, source name lists, and (best-effort) response-model field names.
The ``_generated_*`` modules are produced by ``scripts/gen_contract.py``
(``make contract``) from ``contract/openapi.snapshot.json`` and must not be
hand-edited.

Public surface:

- :data:`ALL_PATHS` and the named path-template constants from
  :mod:`._generated_paths`.
- The enum :class:`typing.Literal` aliases and their ``*_VALUES`` tuples from
  :mod:`._generated_enums`.
- The pydantic response models from :mod:`._generated_models` (imported as
  :data:`models` for namespaced access). The KGDB gene/annotation endpoints
  return JSON:API ``dict`` payloads, so few typed response models exist; the
  release endpoints do (:data:`ReleaseResponse`, :data:`ReleaseList`).
"""

from __future__ import annotations

from . import _generated_models as models
from ._generated_enums import (
    ANNOTATION_SOURCE_VALUES,
    EVIDENCE_GROUP_VALUES,
    EVIDENCE_SOURCE_VALUES,
    EVIDENCE_TIER_VALUES,
    GENE_SORT_FIELD_VALUES,
    AnnotationSource,
    EvidenceGroup,
    EvidenceSource,
    EvidenceTier,
    GeneSortField,
)
from ._generated_models import ReleaseList, ReleaseResponse
from ._generated_paths import (
    ALL_PATHS,
    ANNOTATIONS_GENES_BY_GENE_ID_ANNOTATIONS,
    ANNOTATIONS_GENES_BY_GENE_ID_ANNOTATIONS_SUMMARY,
    ANNOTATIONS_SOURCES,
    DATASOURCES,
    GENES,
    GENES_BY_GENE_SYMBOL,
    GENES_BY_GENE_SYMBOL_EVIDENCE,
    GENES_RESOLVE,
    RELEASES,
    STATISTICS_SUMMARY,
)

__all__ = [
    # path constants
    "ALL_PATHS",
    "GENES",
    "GENES_RESOLVE",
    "GENES_BY_GENE_SYMBOL",
    "GENES_BY_GENE_SYMBOL_EVIDENCE",
    "ANNOTATIONS_GENES_BY_GENE_ID_ANNOTATIONS",
    "ANNOTATIONS_GENES_BY_GENE_ID_ANNOTATIONS_SUMMARY",
    "ANNOTATIONS_SOURCES",
    "STATISTICS_SUMMARY",
    "DATASOURCES",
    "RELEASES",
    # enum Literal aliases
    "EvidenceTier",
    "EvidenceGroup",
    "GeneSortField",
    "EvidenceSource",
    "AnnotationSource",
    # enum value tuples
    "EVIDENCE_TIER_VALUES",
    "EVIDENCE_GROUP_VALUES",
    "GENE_SORT_FIELD_VALUES",
    "EVIDENCE_SOURCE_VALUES",
    "ANNOTATION_SOURCE_VALUES",
    # response models
    "models",
    "ReleaseResponse",
    "ReleaseList",
]
