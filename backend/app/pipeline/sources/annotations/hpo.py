"""
HPO (Human Phenotype Ontology) Annotation Source

Fetches HPO terms and disease associations for genes using the JAX HPO API.
Supports bulk file download from genes_to_phenotype.txt for fast batch
processing, with API fallback for genes not in the bulk file.

Clinical groups (#338, spec .planning/specs/2026-10-26-hpo-clinical-groups-v2.md)
are classified from the pinned HPO release only (genes_to_phenotype.txt + hp.json);
genes from the API fallback get no clinical_group.
"""

import asyncio
import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import ColumnElement, and_, func
from sqlalchemy.orm import Session

from app.core.datasource_config import get_source_parameter
from app.core.logging import get_logger
from app.models.gene import Gene
from app.models.gene_annotation import GeneAnnotation
from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

logger = get_logger(__name__)


# Tie-break order for equal clinical-group evidence (#254); neoplasia last (#338).
# Groups not listed here rank after these, alphabetically.
CLINICAL_GROUP_PRIORITY = (
    "complement",
    "cakut",
    "glomerulopathy",
    "cyst_cilio",
    "tubulopathy",
    "nephrolithiasis",
    "neoplasia",
)
CLINICAL_GROUP_METHOD = "hpo-freq-ic-v2"  # 0.5 again: v2 payloads valid, v2.1 (0.4) recomputed
# secondary: evidence >= this share of the primary's; no r beat 0.5 out of sample (spec, #338)
SECONDARY_GROUP_RATIO = 0.5

# HPO frequency classes -> class midpoints (hp.json); m/n smoothing and the prior for
# unknown frequency follow VarLens hpo-scoring.config.ts.
HPO_FREQUENCY_CLASSES = {
    "HP:0040280": 1.0,  # Obligate
    "HP:0040281": 0.895,  # Very frequent (80-99 %)
    "HP:0040282": 0.545,  # Frequent (30-79 %)
    "HP:0040283": 0.17,  # Occasional (5-29 %)
    "HP:0040284": 0.025,  # Very rare (1-4 %)
    "HP:0040285": 0.0,  # Excluded
}
UNKNOWN_FREQUENCY = 0.35


def _clinical_group_rank(group: str) -> tuple[int, str]:
    if group in CLINICAL_GROUP_PRIORITY:
        return CLINICAL_GROUP_PRIORITY.index(group), ""
    return len(CLINICAL_GROUP_PRIORITY), group


def hpo_frequency(value: str) -> float:
    """Weight of a genes_to_phenotype.txt frequency value (class ID, m/n, x% or -)."""
    if value in HPO_FREQUENCY_CLASSES:
        return HPO_FREQUENCY_CLASSES[value]
    if m := re.fullmatch(r"(\d+)/(\d+)", value):
        return (int(m[1]) + 0.8) / (int(m[2]) + 2.0)
    if m := re.fullmatch(r"([\d.]+)%", value):
        return float(m[1]) / 100
    return UNKNOWN_FREQUENCY


def verify_sha256(path: Path, expected: str) -> Path:
    """Fail closed on a truncated or wrong file: delete it so the next run re-downloads."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        path.unlink(missing_ok=True)
        raise ValueError(f"sha256 mismatch for {path.name}: {digest.hexdigest()} != {expected}")
    return path


def load_hpo_parents(path: Path) -> dict[str, set[str]]:
    """Read is_a parents from an HPO hp.json (obographs); raise if the file is unusable."""
    try:
        with open(path) as f:
            graph = json.load(f)["graphs"][0]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Unparseable HPO ontology file {path}: {e}") from e

    def curie(uri: str) -> str:
        return uri.rsplit("/", 1)[-1].replace("_", ":")

    parents: dict[str, set[str]] = {}
    for edge in graph.get("edges", []):
        if edge.get("pred") == "is_a":
            parents.setdefault(curie(edge["sub"]), set()).add(curie(edge["obj"]))
    if not parents:
        raise ValueError(f"No is_a relations in HPO ontology file {path}")
    return parents


class ClinicalGroupClassifier:
    """Kidney clinical groups from disease-level HPO annotations (#338).

    E(gene, group) = sum over the gene's diseases of f(d, t) * IC(t) over the
    disease's terms t at or below a group root, counting only the most specific
    (a term with an annotated descendant in the same group is skipped).
    """

    def __init__(
        self, parents: dict[str, set[str]], groups: dict[str, list[str]], release: str
    ) -> None:
        self.parents = parents
        self.groups = groups
        self.release = release
        self.ic: dict[str, float] = {}
        self._ancestors: dict[str, frozenset[str]] = {}
        self._descendants: dict[str, frozenset[str]] = {}
        self._children: dict[str, set[str]] = {}
        self._term_groups: dict[str, list[str]] = {}

    def ancestors(self, term: str) -> frozenset[str]:
        """The term and all its is_a ancestors (memoised)."""
        if term not in self._ancestors:
            out = {term}
            for parent in self.parents.get(term, ()):
                out |= self.ancestors(parent)
            self._ancestors[term] = frozenset(out)
        return self._ancestors[term]

    def descendants(self, root: str) -> frozenset[str]:
        """The term and all its is_a descendants (memoised); raise if not in this release."""
        if root not in self._descendants:
            if not self._children:
                for child, parents in self.parents.items():
                    for parent in parents:
                        self._children.setdefault(parent, set()).add(child)
            if root not in self.parents and root not in self._children:
                raise ValueError(f"{root} is not in HPO release {self.release}")
            out: set[str] = set()
            stack = [root]
            while stack:
                term = stack.pop()
                if term not in out:
                    out.add(term)
                    stack.extend(self._children.get(term, ()))
            self._descendants[root] = frozenset(out)
        return self._descendants[root]

    def fit_information_content(self, disease_terms: Iterable[Iterable[str]]) -> None:
        """IC(t) = -ln(n(t)/N): n(t) diseases annotated to t or a descendant."""
        counts: Counter[str] = Counter()
        n_diseases = 0
        for terms in disease_terms:
            n_diseases += 1
            counts.update(set().union(*(self.ancestors(t) for t in terms)))
        self.ic = {t: -math.log(c / n_diseases) for t, c in counts.items()}

    def _groups_of(self, term: str) -> list[str]:
        if term not in self._term_groups:
            ancestors = self.ancestors(term)
            self._term_groups[term] = [
                group for group, roots in self.groups.items() if not ancestors.isdisjoint(roots)
            ]
        return self._term_groups[term]

    def classify(self, disease_terms: dict[str, dict[str, float]]) -> dict[str, Any]:
        """Classify one gene from {disease: {term: frequency weight}}."""
        evidence = dict.fromkeys(self.groups, 0.0)
        supporting: dict[str, set[str]] = {group: set() for group in self.groups}
        for term_weights in disease_terms.values():
            matched: dict[str, list[str]] = {}
            for term in term_weights:
                for group in self._groups_of(term):
                    matched.setdefault(group, []).append(term)
            for group, terms in matched.items():
                for term in terms:
                    if any(other != term and term in self.ancestors(other) for other in terms):
                        continue
                    evidence[group] += term_weights[term] * self.ic.get(term, 0.0)
                    supporting[group].add(term)

        total = sum(evidence.values())
        primary: str | None = (
            min(evidence, key=lambda k: (-evidence[k], *_clinical_group_rank(k)))
            if total > 0
            else None
        )
        secondary = (
            sorted(
                (
                    k
                    for k in evidence
                    if k != primary
                    and evidence[k] > 0
                    and evidence[k] >= SECONDARY_GROUP_RATIO * evidence[primary]
                ),
                key=lambda k: (-evidence[k], *_clinical_group_rank(k)),
            )
            if primary
            else []
        )
        return {
            "primary": primary,
            "secondary": secondary,
            "scores": {k: round(v / total, 3) if total else 0.0 for k, v in evidence.items()},
            "evidence": {k: round(v, 3) for k, v in evidence.items()},
            "supporting_terms": sorted(supporting[primary]) if primary else [],
            "method": CLINICAL_GROUP_METHOD,
            "hpo_release": self.release,
        }


def score_syndromic_features(
    phenotype_ids: set[str], syndromic_descendants: dict[str, set[str]]
) -> dict[str, Any]:
    """Score extra-renal (syndromic) involvement; shared by both HPO pipelines (#254).

    Each category scores matched terms / all phenotype terms (rounded to 3 places).
    A term under several overlapping categories counts in each category's score but
    only once in syndromic_score (distinct extra-renal terms / all terms, so <= 1; #255).
    """
    if not phenotype_ids:
        return {
            "is_syndromic": False,
            "syndromic_score": 0.0,
            "category_scores": {},
            "extra_renal_categories": [],
            "extra_renal_term_counts": {},
        }

    category_counts: dict[str, int] = {}
    extra_renal_terms: set[str] = set()
    for category, descendant_terms in syndromic_descendants.items():
        if not descendant_terms:
            logger.sync_warning(f"No descendant terms for category {category}")
            continue
        matches = phenotype_ids.intersection(descendant_terms)
        if matches:
            category_counts[category] = len(matches)
            extra_renal_terms |= matches

    category_scores = {
        category: round(count / len(phenotype_ids), 3)
        for category, count in category_counts.items()
    }

    # SUM across categories with each term counted once (#255); computed from raw counts,
    # not the rounded category scores, whose rounding missed an exact 0.3 (#254).
    syndromic_score = len(extra_renal_terms) / len(phenotype_ids)
    # Threshold from the predecessor R implementation.
    threshold = get_source_parameter("HPO", "syndromic_threshold", 0.3)

    return {
        "is_syndromic": syndromic_score >= threshold,
        "syndromic_score": round(syndromic_score, 3),
        "category_scores": category_scores,
        "extra_renal_categories": list(category_counts),
        "extra_renal_term_counts": category_counts,
    }


class HPOAnnotationSource(BulkDataSourceMixin, BaseAnnotationSource):
    """
    HPO phenotype annotations for genes.

    Uses the JAX HPO API to fetch:
    1. NCBI Gene ID via gene symbol search
    2. HPO terms and diseases directly associated with the gene
    """

    source_name = "hpo"
    display_name = "Human Phenotype Ontology"
    version = "1.0"

    # Cache configuration
    cache_ttl_days = 90

    # API endpoints
    hpo_api_url = "https://ontology.jax.org/api"

    # Bulk download configuration: pinned release (#338)
    # genes_to_phenotype.txt: gene→phenotype associations (~15 MB)
    bulk_file_url = get_source_parameter("HPO", "genes_to_phenotype_url", "")
    bulk_cache_ttl_hours = 168  # 7 days
    bulk_file_format = "txt"

    _clinical_classifier: ClinicalGroupClassifier | None = None
    _clinical_classifier_error: Exception | None = None
    # Successful classifiers (ontology + IC) shared across instances, keyed by (release, both
    # sha256); the parsed genes_to_phenotype rows stay per instance so they are freed after a run
    _loaded_classifiers: dict[tuple[str, ...], ClinicalGroupClassifier] = {}

    def __init__(self, session: "Session") -> None:
        """Initialize the HPO annotation source."""
        super().__init__(session)

        # Update source configuration
        if self.source_record:
            self.source_record.update_frequency = "weekly"
            self.source_record.description = (
                "Human phenotype terms and disease associations for genes"
            )
            self.source_record.base_url = self.hpo_api_url
            self.session.commit()
        # Descendant sets of the pinned hp.json, built once per run instead of per gene
        self._descendants: dict[str, Any] = {}

    def parse_bulk_file(self, path: Path) -> dict[str, dict[str, Any]]:
        """Parse HPO genes_to_phenotype.txt into gene-keyed dict.

        File format (tab-separated):
          ncbi_gene_id, gene_symbol, hpo_id, hpo_name, frequency, disease_id

        Groups rows by gene_symbol, collecting unique phenotypes and diseases.
        Field names match the output of ``get_gene_annotations()`` for parity.
        ``disease_terms`` (disease -> term -> frequency weight, excluded terms dropped,
        duplicates take the max) feeds the clinical-group classifier (#338).
        """
        data: dict[str, dict[str, Any]] = {}
        # Track seen phenotype IDs per gene to deduplicate
        seen_phenotypes: dict[str, set[str]] = {}
        seen_diseases: dict[str, set[str]] = {}

        with open(path, newline="") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split("\t")
                if len(parts) < 4:
                    continue

                ncbi_gene_id = parts[0].strip()
                gene_symbol = parts[1].strip()
                hpo_id = parts[2].strip()
                hpo_name = parts[3].strip()
                disease_id = parts[5].strip() if len(parts) > 5 else ""

                # Skips the column-header row as well
                if not gene_symbol or not hpo_id.startswith("HP:"):
                    continue

                # Initialize gene entry
                if gene_symbol not in data:
                    data[gene_symbol] = {
                        "ncbi_gene_id": ncbi_gene_id,
                        "phenotypes": [],
                        "diseases": [],
                        "disease_terms": {},
                    }
                    seen_phenotypes[gene_symbol] = set()
                    seen_diseases[gene_symbol] = set()

                # Add phenotype (deduplicated by HPO ID)
                if hpo_id not in seen_phenotypes[gene_symbol]:
                    seen_phenotypes[gene_symbol].add(hpo_id)
                    data[gene_symbol]["phenotypes"].append(
                        {
                            "id": hpo_id,
                            "name": hpo_name,
                        }
                    )

                # Add disease (deduplicated by disease ID)
                if (
                    disease_id
                    and disease_id != "-"
                    and disease_id not in seen_diseases[gene_symbol]
                ):
                    seen_diseases[gene_symbol].add(disease_id)
                    # Parse disease_id into db and dbId (e.g., "OMIM:173900")
                    db = ""
                    db_id = disease_id
                    if ":" in disease_id:
                        db, db_id = disease_id.split(":", 1)
                    data[gene_symbol]["diseases"].append(
                        {
                            "id": disease_id,
                            "name": None,
                            "db": db,
                            "dbId": db_id,
                        }
                    )

                weight = hpo_frequency(parts[4].strip() if len(parts) > 4 else "")
                if weight > 0:
                    terms = data[gene_symbol]["disease_terms"].setdefault(disease_id, {})
                    terms[hpo_id] = max(weight, terms.get(hpo_id, 0.0))

        return data

    async def download_bulk_file(self, force: bool = False) -> Path:
        """Download genes_to_phenotype.txt and check its pinned sha256 before parsing."""
        path = await super().download_bulk_file(force=force)
        expected = str(get_source_parameter("HPO", "genes_to_phenotype_sha256"))
        return await asyncio.to_thread(verify_sha256, path, expected)

    async def _download_hp_json(self) -> Path:
        """Download (or reuse the cached) pinned hp.json via the bulk-file cache."""

        class _PinnedFile(BulkDataSourceMixin):
            bulk_file_url = get_source_parameter("HPO", "hp_json_url", "")
            bulk_file_format = "json"
            bulk_cache_dir = self.bulk_cache_dir

        path = await _PinnedFile().download_bulk_file_streaming()
        expected = str(get_source_parameter("HPO", "hp_json_sha256"))
        return await asyncio.to_thread(verify_sha256, path, expected)

    async def _load_clinical_group_classifier(self) -> ClinicalGroupClassifier:
        """Load the pinned files and IC once per run; fail closed (#338).

        Raises (and keeps raising for this run) if genes_to_phenotype.txt or hp.json
        cannot be downloaded or parsed, so no annotation is written without them.
        """
        if self._clinical_classifier is not None:
            return self._clinical_classifier
        if self._clinical_classifier_error is not None:
            raise self._clinical_classifier_error
        key = tuple(
            str(get_source_parameter("HPO", k))
            for k in ("hpo_release", "genes_to_phenotype_sha256", "hp_json_sha256")
        )
        try:
            await self.ensure_bulk_data_loaded()  # sha256-verified in download_bulk_file
            if not self._bulk_data:
                raise ValueError("HPO genes_to_phenotype.txt has no annotation rows")
            if key in self._loaded_classifiers:
                self._clinical_classifier = self._loaded_classifiers[key]
                return self._clinical_classifier
            groups = {
                group: config["root_terms"]
                for group, config in get_source_parameter("HPO", "clinical_groups", {}).items()
            }
            # hp.json parse and IC fit are CPU-bound: keep them off the event loop (#363)
            parents = await asyncio.to_thread(load_hpo_parents, await self._download_hp_json())
            classifier = ClinicalGroupClassifier(
                parents,
                groups,
                str(get_source_parameter("HPO", "hpo_release")),
            )
            corpus: dict[str, set[str]] = {}
            for gene_data in self._bulk_data.values():
                for disease, terms in gene_data["disease_terms"].items():
                    corpus.setdefault(disease, set()).update(terms)
            await asyncio.to_thread(classifier.fit_information_content, corpus.values())
        except Exception as e:
            self._clinical_classifier_error = e
            raise
        logger.sync_info(
            "HPO clinical-group classifier loaded",
            hpo_release=classifier.release,
            diseases=len(corpus),
            ontology_terms=len(classifier.parents),
        )
        self._clinical_classifier = classifier
        self._loaded_classifiers[key] = classifier
        return classifier

    async def search_gene_for_ncbi_id(self, gene_symbol: str) -> str | None:
        """
        Search for a gene symbol to get its NCBI Gene ID.

        Args:
            gene_symbol: Human gene symbol (e.g., "ARID1B")

        Returns:
            NCBI Gene ID (e.g., "2904") or None if not found
        """
        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            # Search for the gene using the gene search endpoint
            search_url = f"{self.hpo_api_url}/network/search/gene"
            params = {
                "q": gene_symbol,
                "limit": -1,  # Get all results
            }

            response = await client.get(search_url, params=params, timeout=30.0)

            # An outage must not look like "no match": raise so nothing is stored
            if response.status_code != 200:
                logger.sync_error(
                    f"Gene search failed for {gene_symbol}", status_code=response.status_code
                )
                response.raise_for_status()
                raise RuntimeError(f"HPO gene search returned HTTP {response.status_code}")

            # Parse JSON response
            data = response.json()

            # The response has a "results" array
            results = data.get("results", [])

            # Find exact match first
            for gene_result in results:
                if gene_result.get("name") == gene_symbol:
                    # Extract NCBI Gene ID from the id field
                    # Format is "NCBIGene:12345"
                    gene_id = str(gene_result.get("id", ""))
                    if gene_id.startswith("NCBIGene:"):
                        ncbi_id: str = gene_id.replace("NCBIGene:", "")
                        logger.sync_info(f"Found NCBI Gene ID for {gene_symbol}", ncbi_id=ncbi_id)
                        return ncbi_id

            # If no exact match, try case-insensitive match
            gene_symbol_upper = gene_symbol.upper()
            for gene_result in results:
                if str(gene_result.get("name", "")).upper() == gene_symbol_upper:
                    gene_id = str(gene_result.get("id", ""))
                    if gene_id.startswith("NCBIGene:"):
                        ncbi_id = gene_id.replace("NCBIGene:", "")
                        logger.sync_info(
                            f"Found NCBI Gene ID (case-insensitive) for {gene_symbol}",
                            ncbi_id=ncbi_id,
                        )
                        return ncbi_id

            logger.sync_warning(f"No NCBI Gene ID found for {gene_symbol}")
            return None

        except Exception as e:
            logger.sync_error(
                "Error searching for NCBI Gene ID", gene_symbol=gene_symbol, error_detail=str(e)
            )
            raise

    async def get_gene_annotations(self, ncbi_gene_id: str) -> dict[str, Any] | None:
        """
        Get HPO annotations for a gene using its NCBI Gene ID.

        Args:
            ncbi_gene_id: NCBI Gene ID (e.g., "2904")

        Returns:
            Dictionary with phenotypes and diseases or None if error
        """
        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            # Get annotations using the NCBI Gene ID
            annotation_url = f"{self.hpo_api_url}/network/annotation/NCBIGene:{ncbi_gene_id}"

            response = await client.get(annotation_url, timeout=30.0)

            if response.status_code == 404:
                logger.sync_warning(f"No HPO annotations found for NCBIGene:{ncbi_gene_id}")
                return {"phenotypes": [], "diseases": []}

            if response.status_code != 200:
                logger.sync_warning(
                    "Failed to get HPO annotations",
                    ncbi_gene_id=ncbi_gene_id,
                    status_code=response.status_code,
                )
                return None

            data = response.json()

            # Extract phenotypes (HPO terms)
            phenotypes = []
            for phenotype in data.get("phenotypes", []):
                phenotypes.append(
                    {
                        "id": phenotype.get("id"),
                        "name": phenotype.get("name"),
                        "definition": phenotype.get("definition"),
                    }
                )

            # Extract diseases
            diseases = []
            for disease in data.get("diseases", []):
                diseases.append(
                    {
                        "id": disease.get("id"),
                        "name": disease.get("name"),
                        "dbId": disease.get("dbId"),
                        "db": disease.get("db"),
                    }
                )

            return {"phenotypes": phenotypes, "diseases": diseases}

        except Exception as e:
            logger.sync_error(
                "Error fetching HPO annotations", ncbi_gene_id=ncbi_gene_id, error_detail=str(e)
            )
            return None

    async def get_kidney_term_descendants(self) -> set[str]:
        """Configured kidney root terms and their descendants in the pinned hp.json (#365)."""
        if "kidney" not in self._descendants:
            classifier = await self._load_clinical_group_classifier()
            roots = get_source_parameter("HPO", "kidney_terms", [])
            self._descendants["kidney"] = set().union(*(classifier.descendants(t) for t in roots))
        return self._descendants["kidney"]

    async def filter_kidney_phenotypes(self, phenotypes: list[dict]) -> list[dict]:
        """
        Filter for kidney-related phenotypes.
        Simple and clean - just checks if phenotype ID is in kidney term descendants.

        Args:
            phenotypes: List of HPO phenotype dictionaries

        Returns:
            List of kidney-related phenotypes
        """
        # Get the cached kidney term descendants
        kidney_term_ids = await self.get_kidney_term_descendants()

        # Simple filter - phenotype is kidney-related if its ID is in the descendant set
        return [phenotype for phenotype in phenotypes if phenotype.get("id") in kidney_term_ids]

    async def get_classification_term_descendants(
        self, classification_type: str
    ) -> dict[str, set[str]]:
        """Descendants per category ("onset_groups" or "syndromic_indicators").

        Taken from the pinned hp.json, so they match the release `clinical_group` cites
        and raise instead of silently shrinking when a term cannot be resolved (#365).
        """
        if classification_type in self._descendants:
            return self._descendants[classification_type]
        classifier = await self._load_clinical_group_classifier()
        descendants_map: dict[str, set[str]] = {}
        for group_key, group_config in get_source_parameter("HPO", classification_type, {}).items():
            # Single root_term or root_terms; syndromic_indicators map straight to the term
            if isinstance(group_config, dict):
                root_terms = group_config.get("root_terms") or [group_config["root_term"]]
            else:
                root_terms = [group_config]
            descendants_map[group_key] = set().union(
                *(classifier.descendants(t) for t in root_terms)
            )
        self._descendants[classification_type] = descendants_map
        return descendants_map

    async def classify_gene_phenotypes(
        self, phenotypes: list[dict], disease_terms: dict[str, dict[str, float]] | None = None
    ) -> dict[str, Any]:
        """
        Classify phenotypes into clinical, onset, and syndromic groups.

        Args:
            phenotypes: List of HPO phenotype dictionaries
            disease_terms: Pinned-release disease -> term -> frequency weight; without
                it (API fallback) no clinical_group is produced (#338)

        Returns:
            Classification results with scores and confidence
        """
        # Build set of phenotype IDs, filtering out None values and ensuring str type
        phenotype_ids: set[str] = {str(p.get("id")) for p in phenotypes if p.get("id") is not None}

        classification: dict[str, Any] = {}
        if disease_terms is not None:
            classifier = await self._load_clinical_group_classifier()
            classification["clinical_group"] = classifier.classify(disease_terms)
        classification["onset_group"] = await self._classify_onset_group(phenotype_ids)
        classification["syndromic_assessment"] = await self._assess_syndromic_features(
            phenotype_ids
        )

        return classification

    async def _classify_onset_group(self, phenotype_ids: set[str]) -> dict[str, Any]:
        """
        Classify based on age of onset using HPO term hierarchy.
        """
        # Get cached descendants for onset groups
        onset_descendants = await self.get_classification_term_descendants("onset_groups")

        scores: dict[str, int] = {}
        for group_key, descendant_terms in onset_descendants.items():
            matches = phenotype_ids.intersection(descendant_terms)
            scores[group_key] = len(matches)

        # Normalize scores to probabilities
        total = sum(scores.values())
        normalized_scores: dict[str, float] = {}
        if total > 0:
            normalized_scores = {k: round(v / total, 3) for k, v in scores.items()}
        else:
            normalized_scores = dict.fromkeys(scores, 0.0)

        primary: str | None = (
            max(normalized_scores, key=lambda k: normalized_scores.get(k, 0.0))
            if normalized_scores and max(normalized_scores.values()) > 0
            else None
        )

        return {
            "primary": primary,
            "scores": normalized_scores,
        }

    async def _assess_syndromic_features(self, phenotype_ids: set[str]) -> dict:
        """
        Assess syndromic features with sub-category scoring.
        Matches R implementation: checks ALL phenotypes and calculates per-category scores.
        """
        logger.sync_debug(f"Assessing syndromic features for {len(phenotype_ids)} phenotypes")

        # Get descendants for syndromic indicator terms (cached)
        syndromic_descendants = await self.get_classification_term_descendants(
            "syndromic_indicators"
        )

        # Log what we got
        logger.sync_debug(
            "Syndromic descendants loaded",
            categories=list(syndromic_descendants.keys()),
            sizes={k: len(v) for k, v in syndromic_descendants.items()},
        )

        result = score_syndromic_features(phenotype_ids, syndromic_descendants)

        logger.sync_debug(
            "Syndromic assessment complete",
            is_syndromic=result["is_syndromic"],
            score=result["syndromic_score"],
            categories_matched=len(result["extra_renal_categories"]),
        )

        return result

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """Fetch HPO annotation for a gene.

        Tries bulk data first, then falls back to API.
        """
        try:
            ncbi_gene_id = None
            phenotypes: list[dict[str, Any]] = []
            diseases: list[dict[str, Any]] = []
            disease_terms: dict[str, dict[str, float]] = {}

            # Pinned files are required; raises here (nothing written) if unavailable
            await self._load_clinical_group_classifier()

            # Try bulk lookup first
            if self._bulk_data is not None and gene.approved_symbol:
                bulk_result = self.lookup_gene(gene.approved_symbol)
                if bulk_result is not None:
                    ncbi_gene_id = bulk_result.get("ncbi_gene_id")
                    phenotypes = bulk_result.get("phenotypes", [])
                    diseases = bulk_result.get("diseases", [])
                    disease_terms = bulk_result.get("disease_terms", {})

            # Fall back to API if no bulk data
            if not phenotypes:
                api_result = await self._fetch_via_api(gene)
                if api_result is None:
                    return None
                return api_result

            # Build annotation from bulk data (same structure as API path)
            kidney_phenotypes = await self.filter_kidney_phenotypes(phenotypes)

            classification = {}
            if phenotypes:
                classification = await self.classify_gene_phenotypes(phenotypes, disease_terms)

            return {
                "gene_symbol": gene.approved_symbol,
                "ncbi_gene_id": ncbi_gene_id,
                "has_hpo_data": len(phenotypes) > 0 or len(diseases) > 0,
                "phenotypes": phenotypes,
                "phenotype_count": len(phenotypes),
                "diseases": diseases,
                "disease_count": len(diseases),
                "kidney_phenotypes": kidney_phenotypes,
                "kidney_phenotype_count": len(kidney_phenotypes),
                "has_kidney_phenotype": len(kidney_phenotypes) > 0,
                "classification": classification,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.sync_error(f"Error fetching HPO annotation for {gene.approved_symbol}: {str(e)}")
            return None

    async def _fetch_via_api(self, gene: Gene) -> dict[str, Any] | None:
        """Fetch HPO data via API (original implementation)."""
        try:
            ncbi_gene_id = await self.search_gene_for_ncbi_id(gene.approved_symbol)

            if not ncbi_gene_id:
                return {
                    "gene_symbol": gene.approved_symbol,
                    "ncbi_gene_id": None,
                    "has_hpo_data": False,
                    "phenotypes": [],
                    "phenotype_count": 0,
                    "diseases": [],
                    "disease_count": 0,
                    "kidney_phenotypes": [],
                    "kidney_phenotype_count": 0,
                    "has_kidney_phenotype": False,
                    "classification": {},
                    "classification_confidence": "none",
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }

            annotations = await self.get_gene_annotations(ncbi_gene_id)
            if annotations is None:
                return None

            phenotypes = annotations.get("phenotypes", [])
            diseases = annotations.get("diseases", [])
            kidney_phenotypes = await self.filter_kidney_phenotypes(phenotypes)

            classification = {}
            if phenotypes:
                classification = await self.classify_gene_phenotypes(phenotypes)

            return {
                "gene_symbol": gene.approved_symbol,
                "ncbi_gene_id": ncbi_gene_id,
                "has_hpo_data": len(phenotypes) > 0 or len(diseases) > 0,
                "phenotypes": phenotypes,
                "phenotype_count": len(phenotypes),
                "diseases": diseases,
                "disease_count": len(diseases),
                "kidney_phenotypes": kidney_phenotypes,
                "kidney_phenotype_count": len(kidney_phenotypes),
                "has_kidney_phenotype": len(kidney_phenotypes) > 0,
                "classification": classification,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.sync_error(f"Error fetching HPO annotation for {gene.approved_symbol}: {str(e)}")
            return None

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """Fetch annotations for multiple genes.

        Loads bulk data once, then does fast local lookups. Falls back to
        API for genes not found in the bulk file.
        """
        # Pinned genes_to_phenotype.txt + hp.json are required: fail before writing (#338)
        await self._load_clinical_group_classifier()

        results: dict[int, dict[str, Any]] = {}
        api_fallback_genes: list[Gene] = []

        # Fast bulk lookups (still need classification per gene)
        for gene in genes:
            if self._bulk_data is not None and gene.approved_symbol:
                bulk_result = self.lookup_gene(gene.approved_symbol)
                if bulk_result is not None:
                    try:
                        phenotypes = bulk_result.get("phenotypes", [])
                        diseases = bulk_result.get("diseases", [])
                        kidney_phenotypes = await self.filter_kidney_phenotypes(phenotypes)
                        classification = {}
                        if phenotypes:
                            classification = await self.classify_gene_phenotypes(
                                phenotypes, bulk_result.get("disease_terms", {})
                            )

                        results[gene.id] = {
                            "gene_symbol": gene.approved_symbol,
                            "ncbi_gene_id": bulk_result.get("ncbi_gene_id"),
                            "has_hpo_data": len(phenotypes) > 0 or len(diseases) > 0,
                            "phenotypes": phenotypes,
                            "phenotype_count": len(phenotypes),
                            "diseases": diseases,
                            "disease_count": len(diseases),
                            "kidney_phenotypes": kidney_phenotypes,
                            "kidney_phenotype_count": len(kidney_phenotypes),
                            "has_kidney_phenotype": len(kidney_phenotypes) > 0,
                            "classification": classification,
                            "last_updated": datetime.now(timezone.utc).isoformat(),
                        }
                        continue
                    except Exception as e:
                        # Not the API: it lacks the pinned data for clinical groups (#338);
                        # the caller retries this gene through fetch_annotation.
                        logger.sync_warning(
                            f"HPO bulk classification failed for {gene.approved_symbol}: {e}"
                        )
                        continue
            api_fallback_genes.append(gene)

        if api_fallback_genes:
            logger.sync_info(
                "HPO bulk miss, falling back to API",
                bulk_hits=len(results),
                api_fallback=len(api_fallback_genes),
            )

        # API fallback for misses
        batch_size = 10
        for i in range(0, len(api_fallback_genes), batch_size):
            batch = api_fallback_genes[i : i + batch_size]
            tasks = [self._fetch_via_api(gene) for gene in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for gene, result in zip(batch, batch_results, strict=False):
                if isinstance(result, Exception):
                    logger.sync_error(f"Failed to fetch HPO for {gene.approved_symbol}: {result}")
                elif isinstance(result, dict):
                    results[gene.id] = result

            if i + batch_size < len(api_fallback_genes):
                await asyncio.sleep(0.2)

        return results

    def _is_valid_annotation(self, annotation_data: dict) -> bool:
        """Reject cached annotations whose clinical_group predates v2 (#338)."""
        if isinstance(annotation_data, dict):
            group = (annotation_data.get("classification") or {}).get("clinical_group")
            if group is not None and group.get("method") != CLINICAL_GROUP_METHOD:
                return False
        return super()._is_valid_annotation(annotation_data)

    @classmethod
    def stale_annotation_filter(cls) -> ColumnElement[bool]:
        """SQL twin of _is_valid_annotation: a clinical_group from another method is stale."""
        group = GeneAnnotation.annotations[("classification", "clinical_group")]
        method = GeneAnnotation.annotations[("classification", "clinical_group", "method")]
        return and_(
            func.jsonb_typeof(group) == "object",
            method.astext.is_distinct_from(CLINICAL_GROUP_METHOD),
        )

    def validate_annotation(self, annotation_data: dict[str, Any]) -> bool:
        """Validate that annotation data has required fields"""
        required_fields = [
            "gene_symbol",
            "ncbi_gene_id",
            "has_hpo_data",
            "phenotypes",
            "phenotype_count",
            "diseases",
            "disease_count",
            "kidney_phenotypes",
            "kidney_phenotype_count",
            "has_kidney_phenotype",
        ]
        return all(field in annotation_data for field in required_fields)

    def get_summary_fields(self) -> dict[str, str]:
        """
        Get fields to include in materialized view.
        Returns mapping of JSONB paths to column names.
        """
        return {
            "hpo_ncbi_gene_id": "annotations->>'ncbi_gene_id'",
            "has_hpo_phenotypes": "(annotations->>'has_hpo_data')::BOOLEAN",
            "hpo_phenotype_count": "(annotations->>'phenotype_count')::INTEGER",
            "hpo_disease_count": "(annotations->>'disease_count')::INTEGER",
            "has_kidney_phenotype": "(annotations->>'has_kidney_phenotype')::BOOLEAN",
            "kidney_phenotype_count": "(annotations->>'kidney_phenotype_count')::INTEGER",
        }
