"""
MONDO disease mapping annotation source (#28).

Maps the disease IDs the database already holds for a gene (HPO annotation diseases,
GenCC and ClinGen evidence) to MONDO through the pinned MONDO SSSOM, using
``skos:exactMatch`` rows only. A source ID with several exactMatch MONDO IDs is
ambiguous and not mapped; an ID without one is reported as unmapped. MONDO IDs pass
through as direct after a format check. The pinned release, URL and sha256 are stored
with every payload. MONDO is CC BY 4.0.

Prefix normalisation: the SSSOM uses ``Orphanet:``; HPO writes ``ORPHA:``, so ``ORPHA:``
is rewritten to ``Orphanet:``. Every other prefix (``OMIM:``, ``DECIPHER:``, ...) is
looked up as written.
"""

import re
from pathlib import Path
from typing import Any

from app.core.datasource_config import get_annotation_config
from app.core.logging import get_logger
from app.models.gene import Gene, GeneEvidence
from app.models.gene_annotation import GeneAnnotation
from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.pipeline.sources.annotations.hpo import verify_sha256
from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

logger = get_logger(__name__)

PREDICATE = "skos:exactMatch"
MONDO_ID = re.compile(r"^MONDO:\d{7}$")
CURIE = re.compile(r"^[A-Za-z][\w.]*:\S+$")
PREFIX_ALIASES = {"ORPHA": "Orphanet"}

_CONFIG = get_annotation_config("mondo") or {}


def normalise_curie(curie: str) -> str:
    """Strip and rewrite known prefix aliases to the SSSOM spelling."""
    curie = curie.strip()
    prefix, sep, local = curie.partition(":")
    return f"{PREFIX_ALIASES.get(prefix, prefix)}{sep}{local}"


def parse_sssom(path: Path) -> tuple[dict[str, set[str]], dict[str, str]]:
    """Return (object_id -> exactMatch MONDO IDs, MONDO ID -> label) from an SSSOM TSV."""
    mappings: dict[str, set[str]] = {}
    labels: dict[str, str] = {}
    columns: list[str] | None = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if columns is None:
                columns = parts
                missing = {"subject_id", "predicate_id", "object_id"} - set(columns)
                if missing:
                    raise ValueError(f"MONDO SSSOM lacks columns {sorted(missing)}")
                continue
            row = dict(zip(columns, parts, strict=False))
            if row.get("predicate_id") != PREDICATE:
                continue
            subject = row["subject_id"]
            mappings.setdefault(row["object_id"], set()).add(subject)
            if row.get("subject_label"):
                labels[subject] = row["subject_label"]
    if not mappings:
        raise ValueError(f"MONDO SSSOM has no {PREDICATE} rows")
    return mappings, labels


def map_disease_ids(
    inputs: dict[str, set[str]],
    mappings: dict[str, set[str]],
    labels: dict[str, str],
    provenance: dict[str, str],
) -> dict[str, Any]:
    """Map {source disease ID: {HPO/GenCC/ClinGen}} to MONDO; deterministic (sorted) output."""
    mapped: dict[str, dict[str, set[str]]] = {}
    unmapped: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    for source_id in sorted(inputs):
        sources = inputs[source_id]
        curie = normalise_curie(source_id)
        if curie.startswith("MONDO:"):
            targets = {curie} if MONDO_ID.match(curie) else set()
            reason = "invalid MONDO ID"
        elif CURIE.match(curie):
            targets = mappings.get(curie, set())
            reason = "no exactMatch"
        else:
            targets, reason = set(), "invalid identifier"
        # Obsolete terms are marked only by their SSSOM label; an ID absent from the file passes
        live = {t for t in targets if not labels.get(t, "").lower().startswith("obsolete ")}
        if targets and not live:
            reason = "obsolete MONDO term"
        targets = live
        if len(targets) > 1:
            ambiguous.append(
                {
                    "source_id": source_id,
                    "sources": sorted(sources),
                    "candidates": sorted(targets),
                    "reason": "multiple exactMatch",
                }
            )
        elif targets:
            entry = mapped.setdefault(next(iter(targets)), {"source_ids": set(), "sources": set()})
            entry["source_ids"].add(source_id)
            entry["sources"] |= sources
        else:
            unmapped.append({"source_id": source_id, "sources": sorted(sources), "reason": reason})
    diseases = [
        {
            "mondo_id": mondo_id,
            "label": labels.get(mondo_id),
            "source_ids": sorted(entry["source_ids"]),
            "sources": sorted(entry["sources"]),
        }
        for mondo_id, entry in sorted(mapped.items())
    ]
    return {
        "mondo_diseases": diseases,
        "mapped_count": len(diseases),
        "unmapped": unmapped,
        "unmapped_count": len(unmapped),
        "ambiguous": ambiguous,
        "ambiguous_count": len(ambiguous),
        "provenance": provenance,
    }


class MondoAnnotationSource(BulkDataSourceMixin, BaseAnnotationSource):
    """Gene disease IDs mapped to MONDO via the pinned SSSOM (exactMatch only)."""

    source_name = "mondo"
    display_name = "MONDO Disease Ontology"
    version = str(_CONFIG.get("mondo_release", "unpinned"))
    batch_size = 500

    bulk_file_url = str(_CONFIG.get("sssom_url", ""))
    bulk_cache_ttl_hours = 168  # 7 days
    bulk_file_format = "tsv"

    def __init__(self, session: Any) -> None:
        super().__init__(session)
        self._mappings: dict[str, set[str]] | None = None
        self._labels: dict[str, str] = {}
        self._load_error: Exception | None = None

    @staticmethod
    def provenance() -> dict[str, str]:
        return {
            "mondo_release": str(_CONFIG.get("mondo_release")),
            "sssom_url": str(_CONFIG.get("sssom_url")),
            "sssom_sha256": str(_CONFIG.get("sssom_sha256")),
            "predicate": PREDICATE,
            "license": "CC BY 4.0",
        }

    async def _load_mappings(self) -> dict[str, set[str]]:
        """Download, verify and parse the pinned SSSOM once; fail closed for the whole run."""
        if self._mappings is not None:
            return self._mappings
        if self._load_error is not None:
            raise self._load_error
        try:
            if not self.bulk_file_url or not _CONFIG.get("sssom_sha256"):
                raise ValueError("MONDO SSSOM URL or sha256 is not configured")
            path = await self.download_bulk_file()
            verify_sha256(path, str(_CONFIG["sssom_sha256"]))
            self._mappings, self._labels = parse_sssom(path)
        except Exception as e:
            self._load_error = e
            logger.sync_error(f"MONDO SSSOM unavailable, source run fails: {e}")
            raise
        return self._mappings

    def _disease_ids(self, gene_ids: list[int]) -> dict[int, dict[str, set[str]]]:
        """{gene_id: {disease ID: {HPO/GenCC/ClinGen}}} from stored HPO annotations + evidence."""
        result: dict[int, dict[str, set[str]]] = {gid: {} for gid in gene_ids}

        def add(gene_id: int, disease_id: Any, source: str) -> None:
            if isinstance(disease_id, str) and disease_id.strip():
                result[gene_id].setdefault(disease_id.strip(), set()).add(source)

        hpo_rows = (
            self.session.query(GeneAnnotation.gene_id, GeneAnnotation.annotations)
            .filter(GeneAnnotation.gene_id.in_(gene_ids), GeneAnnotation.source == "hpo")
            .all()
        )
        for gene_id, data in hpo_rows:
            for disease in (data or {}).get("diseases") or []:
                add(gene_id, (disease or {}).get("id"), "HPO")

        evidence_rows = (
            self.session.query(
                GeneEvidence.gene_id, GeneEvidence.source_name, GeneEvidence.evidence_data
            )
            .filter(
                GeneEvidence.gene_id.in_(gene_ids),
                GeneEvidence.source_name.in_(["GenCC", "ClinGen"]),
            )
            .all()
        )
        for gene_id, source_name, data in evidence_rows:
            data = data or {}
            if source_name == "ClinGen":
                for validity in data.get("validities") or []:
                    add(gene_id, (validity or {}).get("mondo_id"), "ClinGen")
            else:
                for submission in data.get("submissions") or []:
                    raw = (submission or {}).get("raw_data") or {}
                    add(gene_id, raw.get("disease_curie"), "GenCC")
                    add(gene_id, raw.get("disease_original_curie"), "GenCC")
        return result

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        mappings = await self._load_mappings()  # raises: nothing is written without the file
        inputs = self._disease_ids([g.id for g in genes])
        provenance = self.provenance()
        return {
            gene_id: map_disease_ids(ids, mappings, self._labels, provenance)
            for gene_id, ids in inputs.items()
        }

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        return (await self.fetch_batch([gene])).get(gene.id)

    def _is_valid_annotation(self, annotation_data: dict) -> bool:
        """Reject cached payloads mapped with another SSSOM pin."""
        if not isinstance(annotation_data, dict):
            return False
        provenance = annotation_data.get("provenance") or {}
        if provenance.get("sssom_sha256") != _CONFIG.get("sssom_sha256"):
            return False
        return super()._is_valid_annotation(annotation_data)
