"""Data-class taxonomy tags attached to every payload.

Each tool result carries a ``data_class`` string from this module so a client
can reason about what kind of record it received (a curated gene, a scored
evidence row, a descriptive annotation, …) without re-parsing the payload shape.
"""

from __future__ import annotations

#: A curated gene record (score, tier, group, sources).
GENE = "gene"
#: A per-source scored evidence row.
EVIDENCE = "evidence"
#: A descriptive (non-scored) annotation record.
ANNOTATION = "annotation"
#: A protein-protein interaction partner record.
INTERACTION = "interaction"
#: A database-wide statistics rollup.
STATISTICS = "statistics"
#: A data-source / provenance descriptor.
SOURCE = "source"
#: A published data-release descriptor (version + DOI + citation).
RELEASE = "release"
#: A canonical gene-identity resolution (id, hgnc_id, approved_symbol).
GENE_IDENTITY = "gene_identity"
#: Server-local operational metadata (capabilities, resources).
OPERATIONAL_METADATA = "operational_metadata"
