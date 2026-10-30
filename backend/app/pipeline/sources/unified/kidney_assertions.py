"""Ontology-based kidney filter for GenCC and ClinGen assertions (#438).

An assertion whose disease text has no kidney keyword is still kidney-related when HPO
annotates that gene-disease pair with a term under ``kidney_assertion_hpo_root``
(HP:0000077, Abnormality of the kidney) and the gene already has PanelApp or
DiagnosticPanels evidence (plan .planning/plans/2026-10-30-kidney-assertion-filter.md).

Uses only the pinned, sha256-checked HPO genes_to_phenotype.txt, phenotype.hpoa (for the
NOT qualifiers genes_to_phenotype.txt drops) and hp.json and the MONDO SSSOM (exactMatch;
ambiguous or obsolete mappings ignored). Building fails soft:
the loader returns None and the sources fall back to today's keyword-only filter.
"""

import asyncio
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from app.core.datasource_config import get_annotation_config, get_source_parameter
from app.core.logging import get_logger
from app.pipeline.sources.annotations.hpo import hpo_frequency, load_hpo_parents, verify_sha256
from app.pipeline.sources.annotations.mondo import normalise_curie, parse_sssom
from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

logger = get_logger(__name__)

PANEL_SOURCES = ("PanelApp", "DiagnosticPanels")


class KidneyAssertionIndex:
    """Kidney gene-disease pairs from HPO, MONDO cross-references and the panel-gene gate."""

    def __init__(
        self,
        kidney_pairs: set[tuple[str, str]],
        mondo_xrefs: dict[str, set[str]],
        panel_genes: set[str],
    ) -> None:
        self.kidney_pairs = kidney_pairs
        self.mondo_xrefs = mondo_xrefs
        self.panel_genes = {g.upper() for g in panel_genes}

    @classmethod
    def build(
        cls,
        parents: dict[str, set[str]],
        g2p_path: Path,
        hpoa_path: Path,
        sssom: dict[str, set[str]],
        labels: dict[str, str],
        panel_genes: set[str],
        root: str,
    ) -> "KidneyAssertionIndex":
        children: dict[str, set[str]] = {}
        for child, ps in parents.items():
            for parent in ps:
                children.setdefault(parent, set()).add(child)
        kidney_terms, stack = {root}, [root]
        while stack:
            for child in children.get(stack.pop(), ()):
                if child not in kidney_terms:
                    kidney_terms.add(child)
                    stack.append(child)

        # (disease, term) pairs that phenotype.hpoa marks NOT: g2p lists them with frequency "-"
        negated: set[tuple[str, str]] = set()
        with open(hpoa_path, newline="") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) > 3 and parts[2] == "NOT":
                    negated.add((parts[0].strip(), parts[3].strip()))

        pairs: set[tuple[str, str]] = set()
        with open(g2p_path, newline="") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 6 or parts[2] not in kidney_terms:
                    continue
                freq = parts[4].strip()
                # skip NOT, "Excluded" and 0/n (seen in none of n patients) annotations
                if (parts[5].strip(), parts[2]) in negated or freq.startswith("0/"):
                    continue
                if hpo_frequency(freq) > 0:
                    pairs.add((parts[1].strip().upper(), normalise_curie(parts[5])))

        xrefs: dict[str, set[str]] = {}
        for source_id, mondo_ids in sssom.items():
            live = {m for m in mondo_ids if not labels.get(m, "").lower().startswith("obsolete ")}
            if len(live) == 1:
                xrefs.setdefault(next(iter(live)), set()).add(source_id)
        return cls(pairs, xrefs, panel_genes)

    def matches(self, gene_symbol: str, disease_ids: Iterable[Any]) -> bool:
        symbol = gene_symbol.strip().upper()
        if symbol not in self.panel_genes:
            return False
        for raw in disease_ids:
            if not isinstance(raw, str) or not raw.strip():
                continue
            curie = normalise_curie(raw)
            for candidate in {curie} | self.mondo_xrefs.get(curie, set()):
                if (symbol, candidate) in self.kidney_pairs:
                    return True
        return False


def ciliopathy_match(index: KidneyAssertionIndex | None, symbol: Any, text: str) -> str | None:
    """Kidney match for a "ciliopathy" title, which kidney_exclude blanks (#451).

    Retinal, motile and skeletal ciliopathy titles (ARL2BP, TUBB4B) are not kidney-related,
    but "BBS1-related ciliopathy" is: keep them for PanelApp/DiagnosticPanels genes only.
    Without an index keep them all, as before #454, so a failed index never drops BBS genes.
    """
    if "ciliopathy" not in text.lower():
        return None
    if index is None:
        return "keyword"
    if isinstance(symbol, str) and symbol.strip().upper() in index.panel_genes:
        return "keyword_panel"
    return None


async def _pinned_file(url: str, fmt: str, sha256: str) -> Path:
    class _Pinned(BulkDataSourceMixin):
        bulk_file_url = url
        bulk_file_format = fmt

    path = await _Pinned().download_bulk_file_streaming()
    return await asyncio.to_thread(verify_sha256, path, sha256)


def _panel_genes(db: Any) -> set[str]:
    from app.models.gene import Gene, GeneEvidence

    rows = (
        db.query(Gene.approved_symbol)
        .join(GeneEvidence, GeneEvidence.gene_id == Gene.id)
        .filter(GeneEvidence.source_name.in_(PANEL_SOURCES))
        .distinct()
        .all()
    )
    return {symbol for (symbol,) in rows}


async def load_kidney_assertion_index(db: Any) -> KidneyAssertionIndex | None:
    """Build the index for this run; None (keyword-only fallback) if anything fails."""
    if db is None:
        return None
    try:
        mondo = get_annotation_config("mondo") or {}
        hp_json = await _pinned_file(
            get_source_parameter("HPO", "hp_json_url", ""),
            "json",
            str(get_source_parameter("HPO", "hp_json_sha256")),
        )
        g2p = await _pinned_file(
            get_source_parameter("HPO", "genes_to_phenotype_url", ""),
            "txt",
            str(get_source_parameter("HPO", "genes_to_phenotype_sha256")),
        )
        hpoa = await _pinned_file(
            get_source_parameter("HPO", "phenotype_hpoa_url", ""),
            "hpoa",
            str(get_source_parameter("HPO", "phenotype_hpoa_sha256")),
        )
        sssom = await _pinned_file(str(mondo["sssom_url"]), "tsv", str(mondo["sssom_sha256"]))
        parents = await asyncio.to_thread(load_hpo_parents, hp_json)
        mappings, labels = await asyncio.to_thread(parse_sssom, sssom)
        panel_genes = _panel_genes(db)
        if not panel_genes:
            raise ValueError("no PanelApp/DiagnosticPanels genes in the database")
        root = str(get_source_parameter("HPO", "kidney_assertion_hpo_root", "HP:0000077"))
        index = await asyncio.to_thread(
            KidneyAssertionIndex.build, parents, g2p, hpoa, mappings, labels, panel_genes, root
        )
    except Exception as e:
        logger.sync_error(f"Kidney assertion index unavailable, keyword-only filter: {e}")
        return None
    logger.sync_info(
        "Kidney assertion index loaded",
        kidney_pairs=len(index.kidney_pairs),
        panel_genes=len(index.panel_genes),
    )
    return index
