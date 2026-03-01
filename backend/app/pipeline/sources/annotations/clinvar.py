"""
ClinVar Annotation Source

Fetches variant counts and clinical significance data from ClinVar.
Primary strategy: bulk download of variant_summary.txt.gz (~414 MB,
updated weekly) with streaming decompression and parsing.  Falls back
to NCBI eUtils API for genes not found in the bulk file.

Supports an optional NCBI API key for higher API throughput (10 req/s
vs 3 req/s) when the API fallback is needed.
"""

import asyncio
import csv
import gzip
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.pipeline.sources.annotations.clinvar_utils import (
    GeneAccumulator,
    parse_protein_position,
    parse_variant_row,
)
from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

logger = get_logger(__name__)

# Assembly priority for dedup: higher = preferred
_ASSEMBLY_PRIORITY: dict[str, int] = {
    "GRCh38": 3,
    "GRCh37": 2,
    "na": 1,
}

# Cap per-gene variant detail lists to bound JSONB size and memory.
_MAX_DETAIL_VARIANTS = 200


class ClinVarAnnotationSource(BulkDataSourceMixin, BaseAnnotationSource):
    """
    ClinVar variant annotation source.

    Downloads variant_summary.txt.gz in bulk, parses it for target genes,
    and aggregates variant statistics.  Falls back to NCBI eUtils API for
    genes not present in the bulk file.
    """

    source_name = "clinvar"
    display_name = "ClinVar"
    version = "2.0"

    # Cache and rate limiting (BaseAnnotationSource)
    cache_ttl_days = 7
    requests_per_second = 3.0  # NCBI default; upgraded to 10 when API key is set

    # Base configuration
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    # Default values (overridden by config)
    batch_size = 50
    variant_batch_size = 200
    search_batch_size = 10000
    max_concurrent_variant_fetches = 2

    # Bulk download: variant_summary.txt.gz (~414 MB)
    bulk_file_url = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
    bulk_cache_ttl_hours = 168  # 7 days
    bulk_file_format = "txt.gz"
    bulk_file_min_size_bytes = 300_000_000  # ~300 MB; full file is ~414 MB

    # Review status confidence levels (loaded from configuration)
    _review_confidence_levels: dict[str, int] | None = None

    # Target genes loaded from DB for filtering bulk file
    _target_genes: set[str] | None = None

    def __init__(self, session: Session) -> None:
        """Initialize the ClinVar annotation source."""
        super().__init__(session)

        from app.core.datasource_config import get_annotation_config

        config = get_annotation_config("clinvar") or {}

        self.batch_size = config.get("gene_batch_size", 10)
        self.variant_batch_size = config.get("variant_batch_size", 200)
        self.search_batch_size = config.get("search_batch_size", 10000)
        self.max_concurrent_variant_fetches = config.get("max_concurrent_variant_fetches", 2)

        # NCBI API key (env var or config) — 3 req/s without, 10 req/s with
        self.ncbi_api_key: str | None = os.environ.get("NCBI_API_KEY") or config.get("ncbi_api_key")
        if self.ncbi_api_key:
            logger.sync_info("NCBI API key configured, using 10 req/s rate limit")

        if self.source_record:
            self.source_record.update_frequency = "weekly"
            self.source_record.description = "Clinical variant data from ClinVar database"
            self.source_record.base_url = self.base_url
            self.session.commit()

    # ------------------------------------------------------------------
    # Bulk: variant_summary.txt.gz download + parsing
    # ------------------------------------------------------------------

    def _load_target_genes(self) -> set[str]:
        """Load approved symbols for all genes in the DB."""
        if self._target_genes is not None:
            return self._target_genes
        genes = (
            self.session.query(Gene.approved_symbol).filter(Gene.approved_symbol.isnot(None)).all()
        )
        self._target_genes = {g[0] for g in genes if g[0]}
        # Release DB transaction before long-running parse to avoid
        # idle_in_transaction_session_timeout (30 s) during 60-90 s file parse.
        self.session.commit()
        logger.sync_info(
            "Loaded target genes for ClinVar bulk filter", count=len(self._target_genes)
        )
        return self._target_genes

    async def ensure_bulk_data_loaded(self, force: bool = False) -> None:
        """Download variant_summary.txt.gz via streaming, parse for target genes.

        Overrides the base mixin to use streaming download (414 MB file)
        and offloads the heavy parsing to a thread pool so the event loop
        is never blocked.
        """
        if self._bulk_data is not None and not force:
            return

        raw_path = await self.download_bulk_file_streaming(force=force)

        # Offload DB query + heavy file parsing to thread pool
        target_genes = await run_in_threadpool(self._load_target_genes)

        logger.sync_info(
            "Parsing ClinVar variant_summary.txt.gz",
            path=str(raw_path),
            target_genes=len(target_genes),
        )
        self._bulk_data = await run_in_threadpool(
            self._parse_variant_summary, raw_path, target_genes
        )
        logger.sync_info(
            "ClinVar bulk data loaded",
            gene_count=len(self._bulk_data),
        )

    def parse_bulk_file(self, path: Path) -> dict[str, dict[str, Any]]:
        """Parse variant_summary.txt.gz into gene-keyed aggregated annotations.

        This delegates to _parse_variant_summary with current target genes.
        Called by the base mixin if ensure_bulk_data_loaded is not overridden.
        """
        target_genes = self._load_target_genes()
        return self._parse_variant_summary(path, target_genes)

    def _parse_variant_summary(
        self, path: Path, target_genes: set[str]
    ) -> dict[str, dict[str, Any]]:
        """Stream-parse variant_summary.txt.gz and aggregate per gene.

        Two-pass streaming keeps memory bounded (~70 MB vs ~8.8 GB):

        Pass 1 — Build a compact dedup map ``{gene: {var_id_int: priority}}``.
                 Only integers are stored, so the map is ~5 MB for 50K variants.
        Pass 2 — Stream the file again.  For each winning (gene, var_id)
                 pair, call ``parse_variant_row()`` and feed into a
                 ``GeneAccumulator`` that aggregates on-the-fly.  Detail
                 lists are capped at ``_MAX_DETAIL_VARIANTS``.
        """
        confidence_levels = self._get_review_confidence_levels()
        open_fn = gzip.open if str(path).endswith(".gz") else open

        # ---- Pass 1: dedup map (ints only → low memory) ----
        dedup: dict[str, dict[int, int]] = defaultdict(dict)

        with open_fn(path, "rt", encoding="utf-8", errors="replace") as fh:  # type: ignore[call-overload]
            reader = csv.DictReader(fh, delimiter="\t")
            for row in reader:
                gene_symbol_raw = row.get("GeneSymbol", "")
                if not gene_symbol_raw:
                    continue

                row_genes = [g.strip() for g in gene_symbol_raw.split(";")]
                matching_genes = [g for g in row_genes if g in target_genes]
                if not matching_genes:
                    continue

                variation_id = row.get("VariationID", "")
                if not variation_id:
                    continue

                try:
                    var_id_int = int(variation_id)
                except ValueError:
                    continue

                assembly = row.get("Assembly", "na")
                priority = _ASSEMBLY_PRIORITY.get(assembly, 0)

                for gene in matching_genes:
                    existing_priority = dedup[gene].get(var_id_int)
                    if existing_priority is None or priority > existing_priority:
                        dedup[gene][var_id_int] = priority

        logger.sync_info(
            "Pass 1 complete: built dedup map",
            genes_found=len(dedup),
            total_unique_variants=sum(len(v) for v in dedup.values()),
        )

        # ---- Pass 2: stream again, aggregate on-the-fly ----
        accumulators: dict[str, GeneAccumulator] = {
            gene: GeneAccumulator(confidence_levels, _MAX_DETAIL_VARIANTS) for gene in dedup
        }

        with open_fn(path, "rt", encoding="utf-8", errors="replace") as fh:  # type: ignore[call-overload]
            reader = csv.DictReader(fh, delimiter="\t")
            for row in reader:
                gene_symbol_raw = row.get("GeneSymbol", "")
                if not gene_symbol_raw:
                    continue

                variation_id = row.get("VariationID", "")
                if not variation_id:
                    continue

                try:
                    var_id_int = int(variation_id)
                except ValueError:
                    continue

                assembly = row.get("Assembly", "na")
                priority = _ASSEMBLY_PRIORITY.get(assembly, 0)

                row_genes = [g.strip() for g in gene_symbol_raw.split(";")]

                for gene in row_genes:
                    gene_dedup = dedup.get(gene)
                    if gene_dedup is None:
                        continue
                    if gene_dedup.get(var_id_int) != priority:
                        continue

                    # This is the winning row — parse and aggregate
                    variant = parse_variant_row(row, confidence_levels)
                    accumulators[gene].add_variant(variant)

                    # Remove entry to prevent double-counting
                    del gene_dedup[var_id_int]

        logger.sync_info(
            "Pass 2 complete: aggregated variants",
            genes_aggregated=len(accumulators),
        )

        # ---- Build results ----
        result: dict[str, dict[str, Any]] = {}
        for gene_symbol, acc in accumulators.items():
            stats = acc.finalize()
            result[gene_symbol] = self._build_annotation(gene_symbol, stats)

        # Add empty results for target genes with no variants
        for gene_symbol in target_genes:
            if gene_symbol not in result:
                result[gene_symbol] = self._empty_annotation(gene_symbol)

        return result

    # ------------------------------------------------------------------
    # NCBI API key helper
    # ------------------------------------------------------------------

    def _ncbi_params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return base eUtils params, injecting ``api_key`` when set."""
        params: dict[str, Any] = {}
        if self.ncbi_api_key:
            params["api_key"] = self.ncbi_api_key
        if extra:
            params.update(extra)
        return params

    def _get_review_confidence_levels(self) -> dict[str, int]:
        """Get review status confidence levels from configuration."""
        if self._review_confidence_levels is None:
            from app.core.datasource_config import DATA_SOURCE_CONFIG

            config = DATA_SOURCE_CONFIG.get("ClinVar", {})
            self._review_confidence_levels = config.get(
                "review_confidence",
                {
                    "practice guideline": 4,
                    "reviewed by expert panel": 4,
                    "criteria provided, multiple submitters, no conflicts": 3,
                    "criteria provided, conflicting classifications": 2,
                    "criteria provided, single submitter": 2,
                    "no assertion for the individual variant": 1,
                    "no assertion criteria provided": 1,
                    "no classification provided": 0,
                },
            )
        result: dict[str, int] = self._review_confidence_levels  # type: ignore[assignment]
        return result

    # ------------------------------------------------------------------
    # API fallback methods (for genes missing from bulk file)
    # ------------------------------------------------------------------

    @retry_with_backoff(config=RetryConfig(max_retries=5))
    async def _search_variants(self, gene_symbol: str) -> list[str]:
        """Search for ClinVar variant IDs via eUtils esearch."""
        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            search_url = f"{self.base_url}/esearch.fcgi"
            params = self._ncbi_params(
                {
                    "db": "clinvar",
                    "term": f"{gene_symbol}[gene]",
                    "retmax": self.search_batch_size,
                    "retmode": "json",
                }
            )

            response = await client.get(search_url, params=params)
            data = response.json()

            id_list: list[str] = data.get("esearchresult", {}).get("idlist", [])

            logger.sync_debug(f"Found {len(id_list)} ClinVar variants", gene_symbol=gene_symbol)
            return id_list

        except httpx.HTTPStatusError as e:
            logger.sync_error(
                "Failed to search ClinVar variants",
                gene_symbol=gene_symbol,
                status_code=e.response.status_code,
                response=e.response.text[:200],
            )
            raise

        except Exception as e:
            logger.sync_error(f"Error searching ClinVar variants for {gene_symbol}: {e}")
            raise

    def _parse_variant(self, variant_data: dict[str, Any]) -> dict[str, Any]:
        """Parse a single variant from ClinVar esummary API response."""
        import re

        result: dict[str, Any] = {
            "variant_id": variant_data.get("uid"),
            "accession": variant_data.get("accession"),
            "title": variant_data.get("title"),
            "variant_type": variant_data.get("obj_type"),
            "classification": "Not classified",
            "review_status": "No data",
            "traits": [],
            "molecular_consequences": variant_data.get("molecular_consequence_list", []),
            "chromosome": None,
            "genomic_start": None,
            "genomic_end": None,
        }

        if "germline_classification" in variant_data:
            gc = variant_data["germline_classification"]
            result["classification"] = gc.get("description", "Not provided")
            result["review_status"] = gc.get("review_status", "No assertion")

            if "trait_set" in gc:
                for trait in gc["trait_set"]:
                    trait_info: dict[str, Any] = {
                        "name": trait.get("trait_name"),
                        "omim_id": None,
                        "medgen_id": None,
                    }
                    if "trait_xrefs" in trait:
                        for xref in trait["trait_xrefs"]:
                            if xref["db_source"] == "OMIM":
                                trait_info["omim_id"] = xref["db_id"]
                            elif xref["db_source"] == "MedGen":
                                trait_info["medgen_id"] = xref["db_id"]
                    result["traits"].append(trait_info)

        if "variation_set" in variant_data and variant_data["variation_set"]:
            var = variant_data["variation_set"][0]
            result["cdna_change"] = var.get("cdna_change", "")

            protein_match = re.search(r"\((p\..*?)\)", result["title"])
            result["protein_change"] = protein_match.group(1) if protein_match else ""

            if "variation_loc" in var:
                grch38_loc = None
                any_loc = None
                for loc in var["variation_loc"]:
                    if loc.get("assembly_name") == "GRCh38":
                        grch38_loc = loc
                        break
                    elif any_loc is None:
                        any_loc = loc

                loc_to_use = grch38_loc or any_loc
                if loc_to_use:
                    result["chromosome"] = loc_to_use.get("chr")
                    result["genomic_start"] = loc_to_use.get("start")
                    result["genomic_end"] = loc_to_use.get("stop")

        return result

    @retry_with_backoff(config=RetryConfig(max_retries=5))
    async def _fetch_variant_batch(self, variant_ids: list[str]) -> list[dict[str, Any]]:
        """Fetch variant details via eUtils esummary."""
        if not variant_ids:
            return []

        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            summary_url = f"{self.base_url}/esummary.fcgi"
            params = self._ncbi_params(
                {"db": "clinvar", "id": ",".join(variant_ids), "retmode": "json"}
            )

            response = await client.get(summary_url, params=params)
            data = response.json()

            result = data.get("result", {})

            variants = []
            for uid in result.get("uids", []):
                if uid in result:
                    variant = self._parse_variant(result[uid])
                    variants.append(variant)

            return variants

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 or "X-RateLimit-Remaining" in e.response.headers:
                remaining = e.response.headers.get("X-RateLimit-Remaining", "unknown")
                logger.sync_error(
                    "ClinVar rate limit hit",
                    status_code=e.response.status_code,
                    remaining_requests=remaining,
                    batch_size=len(variant_ids),
                )
            else:
                logger.sync_error(
                    "Failed to fetch ClinVar variant details",
                    status_code=e.response.status_code,
                    batch_size=len(variant_ids),
                )
            raise

        except Exception as e:
            logger.sync_error(
                f"Error fetching ClinVar variant batch ({len(variant_ids)} variants): {e}"
            )
            raise

    async def _fetch_via_api(self, gene: Gene) -> dict[str, Any] | None:
        """Fetch ClinVar annotation for a single gene via the NCBI eUtils API.

        This is the original API-based implementation, now used only as a
        fallback when a gene is not found in the bulk file.
        """
        try:
            variant_ids = await self._search_variants(gene.approved_symbol)

            if not variant_ids:
                return self._empty_annotation(gene.approved_symbol)

            all_variants: list[dict[str, Any]] = []
            total_batches = (
                len(variant_ids) + self.variant_batch_size - 1
            ) // self.variant_batch_size

            semaphore = asyncio.Semaphore(self.max_concurrent_variant_fetches)

            async def fetch_batch_with_semaphore(
                batch_ids: list[str], batch_num: int
            ) -> list[dict[str, Any]]:
                async with semaphore:
                    try:
                        if batch_num % 5 == 0:
                            logger.sync_debug(
                                "Fetching ClinVar variants (API fallback)",
                                gene_symbol=gene.approved_symbol,
                                batch=f"{batch_num + 1}/{total_batches}",
                            )
                        batch_result: list[dict[str, Any]] = await self._fetch_variant_batch(
                            batch_ids
                        )
                        return batch_result
                    except Exception as e:
                        logger.sync_error(
                            f"Failed variant batch {batch_num} for {gene.approved_symbol}: {e}"
                        )
                        if self.circuit_breaker and self.circuit_breaker.state == "open":
                            logger.sync_error("Circuit breaker open, using partial data")
                        return []

            tasks = []
            for batch_num, i in enumerate(range(0, len(variant_ids), self.variant_batch_size)):
                batch_ids = variant_ids[i : i + self.variant_batch_size]
                tasks.append(fetch_batch_with_semaphore(batch_ids, batch_num))

            batch_results = await asyncio.gather(*tasks, return_exceptions=False)

            for batch_variants in batch_results:
                if batch_variants:
                    all_variants.extend(batch_variants)

            stats = self._aggregate_variants(all_variants)
            annotation = self._build_annotation(gene.approved_symbol, stats)

            logger.sync_info(
                "ClinVar API fallback complete",
                gene_symbol=gene.approved_symbol,
                total_variants=stats["total_count"],
                pathogenic=stats["pathogenic_count"] + stats["likely_pathogenic_count"],
            )
            return annotation

        except Exception as e:
            logger.sync_error(f"Error in ClinVar API fallback for {gene.approved_symbol}: {e}")
            return None

    # ------------------------------------------------------------------
    # Aggregation + annotation building
    # ------------------------------------------------------------------

    def _parse_protein_position(self, protein_change: str) -> int | None:
        """Parse protein position from HGVS notation. Delegates to clinvar_utils."""
        return parse_protein_position(protein_change)

    def _aggregate_variants(self, variants: list[dict[str, Any]]) -> dict[str, Any]:
        """Aggregate variant data into summary statistics."""
        total_count = len(variants)
        pathogenic_count = 0
        likely_pathogenic_count = 0
        vus_count = 0
        benign_count = 0
        likely_benign_count = 0
        conflicting_count = 0
        not_provided_count = 0
        high_confidence_count = 0
        variant_type_counts: dict[str, int] = defaultdict(int)
        traits_summary: dict[str, int] = defaultdict(int)
        molecular_consequences: dict[str, int] = defaultdict(int)
        protein_variants: list[dict[str, Any]] = []
        genomic_variants: list[dict[str, Any]] = []
        consequence_categories: dict[str, int] = {
            "truncating": 0,
            "missense": 0,
            "inframe": 0,
            "splice_region": 0,
            "regulatory": 0,
            "intronic": 0,
            "synonymous": 0,
            "other": 0,
        }

        confidence_levels = self._get_review_confidence_levels()

        TRUNCATING = {"nonsense", "frameshift variant", "start lost"}
        SPLICE = {"splice donor variant", "splice acceptor variant", "splice region variant"}

        for variant in variants:
            classification = variant["classification"].lower()

            # Count by classification
            is_pathogenic = False
            if "pathogenic" in classification:
                is_pathogenic = True
                if "likely" in classification:
                    likely_pathogenic_count += 1
                elif "/" not in classification:
                    pathogenic_count += 1
                elif "pathogenic/likely pathogenic" in classification:
                    pathogenic_count += 1

            # Determine category for filtering
            if is_pathogenic:
                if "likely" in classification:
                    category = "likely_pathogenic"
                else:
                    category = "pathogenic"
            elif "benign" in classification:
                if "likely" in classification:
                    category = "likely_benign"
                else:
                    category = "benign"
            elif "uncertain" in classification or "vus" in classification.lower():
                category = "vus"
            elif "conflicting" in classification:
                category = "conflicting"
            else:
                category = "other"

            confidence = confidence_levels.get(variant.get("review_status", ""), 0)
            mol_consequences = variant.get("molecular_consequences", [])

            # Determine effect category
            effect_category = "other"
            for conseq in mol_consequences:
                conseq_lower = conseq.lower()
                if conseq_lower in TRUNCATING:
                    effect_category = "truncating"
                    break
                elif conseq_lower in SPLICE or "splice" in conseq_lower:
                    if effect_category not in ("truncating",):
                        effect_category = "splice_region"
                elif "missense" in conseq_lower:
                    if effect_category not in ("truncating", "splice_region"):
                        effect_category = "missense"
                elif "inframe" in conseq_lower:
                    if effect_category not in ("truncating", "splice_region", "missense"):
                        effect_category = "inframe"
                elif "synonymous" in conseq_lower:
                    if effect_category == "other":
                        effect_category = "synonymous"

            # Protein variants
            protein_change = variant.get("protein_change", "")
            position = parse_protein_position(protein_change)
            if position:
                protein_variants.append(
                    {
                        "position": position,
                        "protein_change": protein_change,
                        "cdna_change": variant.get("cdna_change", ""),
                        "accession": variant.get("accession", ""),
                        "classification": variant.get("classification", ""),
                        "category": category,
                        "effect_category": effect_category,
                        "review_status": variant.get("review_status", ""),
                        "confidence": confidence,
                        "molecular_consequences": mol_consequences,
                        "variant_type": variant.get("variant_type", ""),
                        "title": variant.get("title", ""),
                        "chromosome": variant.get("chromosome"),
                        "genomic_start": variant.get("genomic_start"),
                        "genomic_end": variant.get("genomic_end"),
                    }
                )

            # Genomic variants
            genomic_start = variant.get("genomic_start")
            if genomic_start is not None:
                genomic_variants.append(
                    {
                        "position": position,
                        "protein_change": protein_change,
                        "cdna_change": variant.get("cdna_change", ""),
                        "accession": variant.get("accession", ""),
                        "classification": variant.get("classification", ""),
                        "category": category,
                        "effect_category": effect_category,
                        "review_status": variant.get("review_status", ""),
                        "confidence": confidence,
                        "molecular_consequences": mol_consequences,
                        "variant_type": variant.get("variant_type", ""),
                        "title": variant.get("title", ""),
                        "chromosome": variant.get("chromosome"),
                        "genomic_start": genomic_start,
                        "genomic_end": variant.get("genomic_end"),
                    }
                )

            if not is_pathogenic and "benign" in classification:
                if "likely" in classification:
                    likely_benign_count += 1
                elif "/" not in classification:
                    benign_count += 1
            elif "uncertain" in classification or "vus" in classification.lower():
                vus_count += 1
            elif "conflicting" in classification:
                conflicting_count += 1
            elif "not provided" in classification:
                not_provided_count += 1

            confidence = confidence_levels.get(variant["review_status"], 0)
            if confidence >= 3:
                high_confidence_count += 1

            variant_type_counts[variant.get("variant_type", "")] += 1

            for trait in variant.get("traits", []):
                if trait.get("name"):
                    traits_summary[trait["name"]] += 1

        TRUNCATING_CONSEQUENCES = {"nonsense", "frameshift variant", "start lost"}
        SPLICE_CONSEQUENCES = {
            "splice donor variant",
            "splice acceptor variant",
            "splice region variant",
        }

        for variant in variants:
            for consequence in variant.get("molecular_consequences", []):
                molecular_consequences[consequence] += 1
                consequence_lower = consequence.lower()

                if consequence_lower in TRUNCATING_CONSEQUENCES:
                    consequence_categories["truncating"] += 1
                elif consequence_lower in SPLICE_CONSEQUENCES or "splice" in consequence_lower:
                    consequence_categories["splice_region"] += 1
                elif "missense" in consequence_lower:
                    consequence_categories["missense"] += 1
                elif "synonymous" in consequence_lower:
                    consequence_categories["synonymous"] += 1
                elif "inframe" in consequence_lower:
                    consequence_categories["inframe"] += 1
                elif "UTR" in consequence:
                    consequence_categories["regulatory"] += 1
                elif "intron" in consequence.lower():
                    consequence_categories["intronic"] += 1
                else:
                    consequence_categories["other"] += 1

        top_consequences = sorted(molecular_consequences.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]
        top_molecular_consequences = [
            {"consequence": c[0], "count": c[1]} for c in top_consequences
        ]

        percentages: dict[str, float] = {}
        if total_count > 0:
            for cat_name in consequence_categories:
                percentages[f"{cat_name}_percentage"] = round(
                    (consequence_categories[cat_name] / total_count) * 100, 1
                )

        top_traits_sorted = sorted(traits_summary.items(), key=lambda x: x[1], reverse=True)[:5]
        top_traits = [{"trait": t[0], "count": t[1]} for t in top_traits_sorted]

        high_confidence_percentage = 0.0
        pathogenic_percentage = 0.0
        if total_count > 0:
            high_confidence_percentage = round((high_confidence_count / total_count) * 100, 1)
            pathogenic_percentage = round(
                ((pathogenic_count + likely_pathogenic_count) / total_count) * 100, 1
            )

        has_pathogenic = pathogenic_count > 0 or likely_pathogenic_count > 0

        stats: dict[str, Any] = {
            "total_count": total_count,
            "pathogenic_count": pathogenic_count,
            "likely_pathogenic_count": likely_pathogenic_count,
            "vus_count": vus_count,
            "benign_count": benign_count,
            "likely_benign_count": likely_benign_count,
            "conflicting_count": conflicting_count,
            "not_provided_count": not_provided_count,
            "high_confidence_count": high_confidence_count,
            "variant_type_counts": dict(variant_type_counts),
            "molecular_consequences": dict(molecular_consequences),
            "protein_variants": protein_variants,
            "genomic_variants": genomic_variants,
            "consequence_categories": consequence_categories,
            "top_molecular_consequences": top_molecular_consequences,
            "top_traits": top_traits,
            "high_confidence_percentage": high_confidence_percentage,
            "pathogenic_percentage": pathogenic_percentage,
            "has_pathogenic": has_pathogenic,
        }
        stats.update(percentages)

        return stats

    def _build_annotation(self, gene_symbol: str, stats: dict[str, Any]) -> dict[str, Any]:
        """Build the final annotation dict from aggregated stats."""
        annotation: dict[str, Any] = {
            "gene_symbol": gene_symbol,
            "total_variants": stats["total_count"],
            "pathogenic_count": stats["pathogenic_count"],
            "likely_pathogenic_count": stats["likely_pathogenic_count"],
            "vus_count": stats["vus_count"],
            "benign_count": stats["benign_count"],
            "likely_benign_count": stats["likely_benign_count"],
            "conflicting_count": stats["conflicting_count"],
            "not_provided_count": stats.get("not_provided_count", 0),
            "has_pathogenic": stats["has_pathogenic"],
            "pathogenic_percentage": stats["pathogenic_percentage"],
            "high_confidence_count": stats["high_confidence_count"],
            "high_confidence_percentage": stats["high_confidence_percentage"],
            "variant_types": stats["variant_type_counts"],
            "top_traits": stats["top_traits"],
            "molecular_consequences": dict(stats["molecular_consequences"]),
            "consequence_categories": stats["consequence_categories"],
            "top_molecular_consequences": stats["top_molecular_consequences"],
            "truncating_percentage": stats.get("truncating_percentage", 0),
            "missense_percentage": stats.get("missense_percentage", 0),
            "synonymous_percentage": stats.get("synonymous_percentage", 0),
            "protein_variants": stats.get("protein_variants", []),
            "genomic_variants": stats.get("genomic_variants", []),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        if stats["has_pathogenic"]:
            p_count = stats["pathogenic_count"] + stats["likely_pathogenic_count"]
            annotation["variant_summary"] = f"{p_count} pathogenic/likely pathogenic variants"
        elif stats["vus_count"] > 0:
            annotation["variant_summary"] = f"{stats['vus_count']} VUS variants"
        else:
            annotation["variant_summary"] = "No pathogenic variants"

        return annotation

    @staticmethod
    def _empty_annotation(gene_symbol: str) -> dict[str, Any]:
        """Return a zero-count annotation for a gene with no ClinVar variants."""
        return {
            "gene_symbol": gene_symbol,
            "total_variants": 0,
            "variant_summary": "No variants",
            "pathogenic_count": 0,
            "likely_pathogenic_count": 0,
            "vus_count": 0,
            "benign_count": 0,
            "likely_benign_count": 0,
            "conflicting_count": 0,
            "not_provided_count": 0,
            "has_pathogenic": False,
            "pathogenic_percentage": 0,
            "high_confidence_percentage": 0,
            "high_confidence_count": 0,
            "variant_types": {},
            "top_traits": [],
            "molecular_consequences": {},
            "consequence_categories": {},
            "top_molecular_consequences": [],
            "truncating_percentage": 0,
            "missense_percentage": 0,
            "synonymous_percentage": 0,
            "protein_variants": [],
            "genomic_variants": [],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Public fetch methods
    # ------------------------------------------------------------------

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """Fetch ClinVar annotation for a gene.

        Looks up bulk data first, falls back to NCBI API if not found.
        """
        try:
            # Try bulk lookup first
            if self._bulk_data is not None and gene.approved_symbol:
                bulk_result = self._bulk_data.get(gene.approved_symbol)
                if bulk_result is not None:
                    return bulk_result

            # API fallback
            return await self._fetch_via_api(gene)

        except Exception as e:
            logger.sync_error(f"Error fetching ClinVar annotation for {gene.approved_symbol}: {e}")
            return None

    def _is_valid_annotation(self, annotation_data: dict) -> bool:
        """Validate ClinVar annotation data."""
        if not super()._is_valid_annotation(annotation_data):
            return False

        required_fields = ["total_variants", "gene_symbol"]
        has_required = all(field in annotation_data for field in required_fields)

        return has_required

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """Fetch annotations for multiple genes.

        Loads bulk variant_summary.txt.gz once, then does fast local lookups.
        Falls back to NCBI API for genes not found in the bulk file.
        """
        # Load bulk data (no-op if already loaded)
        try:
            await self.ensure_bulk_data_loaded()
        except Exception as exc:
            logger.sync_warning(
                "Failed to load ClinVar bulk data, falling back to API-only",
                error=str(exc),
            )

        results: dict[int, dict[str, Any]] = {}
        api_fallback_genes: list[Gene] = []

        # Fast bulk lookups
        for gene in genes:
            if self._bulk_data is not None and gene.approved_symbol:
                bulk_result = self._bulk_data.get(gene.approved_symbol)
                if bulk_result is not None:
                    results[gene.id] = bulk_result
                    continue
            api_fallback_genes.append(gene)

        if api_fallback_genes:
            logger.sync_info(
                "ClinVar bulk miss, falling back to API",
                bulk_hits=len(results),
                api_fallback=len(api_fallback_genes),
            )

        # API fallback for misses
        for i, gene in enumerate(api_fallback_genes):
            try:
                if i % 10 == 0 and api_fallback_genes:
                    logger.sync_info(
                        "Processing ClinVar API fallback",
                        progress=f"{i}/{len(api_fallback_genes)}",
                    )
                annotation = await self._fetch_via_api(gene)
                if annotation and self._is_valid_annotation(annotation):
                    results[gene.id] = annotation
            except Exception as e:
                logger.sync_error(
                    f"Failed to fetch ClinVar annotation for {gene.approved_symbol}",
                    error_detail=str(e),
                )
                if self.circuit_breaker and self.circuit_breaker.state == "open":
                    logger.sync_error("Circuit breaker open, stopping API fallback")
                    break

        return results
