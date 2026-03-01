"""
gnomAD annotation source for gene constraint scores.

Supports bulk TSV download from gnomAD v4.1 constraint metrics for fast
batch processing, with GraphQL API fallback for genes not in the bulk file.
"""

import csv
from pathlib import Path
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource
from app.pipeline.sources.unified.bulk_mixin import BulkDataSourceMixin

logger = get_logger(__name__)

# TSV column -> our annotation field name
# Maps gnomAD v4.1 constraint_metrics.tsv columns to the field names
# used by _extract_constraint_data() (the GraphQL API path), ensuring
# data parity between bulk and API approaches.
_TSV_FIELD_MAP: dict[str, str] = {
    "lof.pLI": "pli",
    "lof.z_score": "lof_z",
    "mis.z_score": "mis_z",
    "syn.z_score": "syn_z",
    "lof.oe": "oe_lof",
    "lof.oe_ci.lower": "oe_lof_lower",
    "lof.oe_ci.upper": "oe_lof_upper",
    "mis.oe": "oe_mis",
    "mis.oe_ci.lower": "oe_mis_lower",
    "mis.oe_ci.upper": "oe_mis_upper",
    "syn.oe": "oe_syn",
    "syn.oe_ci.lower": "oe_syn_lower",
    "syn.oe_ci.upper": "oe_syn_upper",
    "lof.obs": "obs_lof",
    "lof.exp": "exp_lof",
    "mis.obs": "obs_mis",
    "mis.exp": "exp_mis",
    "syn.obs": "obs_syn",
    "syn.exp": "exp_syn",
}


class GnomADAnnotationSource(BulkDataSourceMixin, BaseAnnotationSource):
    """
    gnomAD (Genome Aggregation Database) annotation source.

    Uses bulk TSV download of constraint metrics for fast batch processing.
    Falls back to GraphQL API for genes not found in the bulk file.
    """

    source_name = "gnomad"
    display_name = "gnomAD"
    version = "v4.1.0"

    # API configuration (fallback)
    graphql_url = "https://gnomad.broadinstitute.org/api"
    headers = {"Content-Type": "application/json", "User-Agent": "KidneyGeneticsDB/1.0"}

    # Cache configuration
    cache_ttl_days = 90

    # Reference genome
    reference_genome = "GRCh38"

    # Bulk download configuration
    bulk_file_url = (
        "https://storage.googleapis.com/gcp-public-data--gnomad"
        "/release/4.1/constraint/gnomad.v4.1.constraint_metrics.tsv"
    )
    bulk_cache_ttl_hours = 168  # 7 days
    bulk_file_format = "tsv"

    def parse_bulk_file(self, path: Path) -> dict[str, dict[str, Any]]:
        """Parse gnomAD constraint metrics TSV into gene-keyed dict.

        Only canonical transcripts are included. Field names match the
        output of ``_extract_constraint_data()`` for data parity.
        """
        data: dict[str, dict[str, Any]] = {}

        with open(path, newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                if row.get("canonical", "").lower() != "true":
                    continue

                gene_symbol = row.get("gene", "").strip()
                if not gene_symbol:
                    continue

                annotation: dict[str, Any] = {
                    "source_version": "gnomad_v4",
                    "gene_symbol": gene_symbol,
                    "canonical_transcript": row.get("transcript", ""),
                }

                for tsv_col, our_field in _TSV_FIELD_MAP.items():
                    val = row.get(tsv_col, "")
                    if val and val != "NA":
                        try:
                            annotation[our_field] = float(val)
                        except ValueError:
                            annotation[our_field] = val

                # Parse flags from string representation
                flags_str = row.get("constraint_flags", "[]")
                if flags_str and flags_str != "[]" and flags_str != "NA":
                    annotation["flags"] = [
                        f.strip().strip("'\"")
                        for f in flags_str.strip("[]").split(",")
                        if f.strip()
                    ]
                else:
                    annotation["flags"] = []

                # Remove None values
                annotation = {k: v for k, v in annotation.items() if v is not None}

                if any(annotation.get(f) is not None for f in ("pli", "lof_z", "oe_lof")):
                    data[gene_symbol] = annotation

        return data

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """Fetch gnomAD constraint scores for a single gene.

        Tries bulk data first, then falls back to GraphQL API.
        """
        # Try bulk lookup first
        if self._bulk_data is not None and gene.approved_symbol:
            bulk_result = self.lookup_gene(gene.approved_symbol)
            if bulk_result is not None:
                return bulk_result

        # Fall back to GraphQL API
        return await self._fetch_via_api(gene)

    async def _fetch_via_api(self, gene: Gene) -> dict[str, Any] | None:
        """Fetch gnomAD data via GraphQL API (original implementation)."""
        constraint_data = None

        if gene.approved_symbol:
            constraint_data = await self._fetch_by_symbol(gene.approved_symbol)

        if not constraint_data:
            await logger.warning(
                "No gnomAD gene data found",
                gene_id=gene.id,
                gene_symbol=gene.approved_symbol,
                hgnc_id=gene.hgnc_id,
            )
            return None

        return constraint_data

    async def _fetch_by_symbol(self, symbol: str) -> dict | None:
        """Fetch gnomAD data by gene symbol via GraphQL."""
        query = """
        query gene($gene_symbol: String!, $reference_genome: ReferenceGenomeId!) {
            gene(gene_symbol: $gene_symbol, reference_genome: $reference_genome) {
                gene_id
                gene_version
                symbol
                name
                canonical_transcript_id
                gnomad_constraint {
                    exp_lof
                    exp_mis
                    exp_syn
                    obs_lof
                    obs_mis
                    obs_syn
                    oe_lof
                    oe_lof_lower
                    oe_lof_upper
                    oe_mis
                    oe_mis_lower
                    oe_mis_upper
                    oe_syn
                    oe_syn_lower
                    oe_syn_upper
                    lof_z
                    mis_z
                    syn_z
                    pLI
                    flags
                }
                exac_constraint {
                    exp_syn
                    obs_syn
                    syn_z
                    exp_mis
                    obs_mis
                    mis_z
                    exp_lof
                    obs_lof
                    lof_z
                    pLI
                }
            }
        }
        """

        variables = {"gene_symbol": symbol, "reference_genome": self.reference_genome}
        result = await self._execute_query(query, variables)

        if result and result.get("gene"):
            return self._extract_constraint_data(result["gene"])

        return None

    async def _fetch_by_ensembl_id(self, ensembl_id: str) -> dict | None:
        """Fetch gnomAD data by Ensembl gene ID."""
        query = """
        query gene($gene_id: String!, $reference_genome: ReferenceGenomeId!) {
            gene(gene_id: $gene_id, reference_genome: $reference_genome) {
                gene_id
                gene_version
                symbol
                name
                canonical_transcript_id
                gnomad_constraint {
                    exp_lof
                    exp_mis
                    exp_syn
                    obs_lof
                    obs_mis
                    obs_syn
                    oe_lof
                    oe_lof_lower
                    oe_lof_upper
                    oe_mis
                    oe_mis_lower
                    oe_mis_upper
                    oe_syn
                    oe_syn_lower
                    oe_syn_upper
                    lof_z
                    mis_z
                    syn_z
                    pLI
                    flags
                }
                exac_constraint {
                    exp_syn
                    obs_syn
                    syn_z
                    exp_mis
                    obs_mis
                    mis_z
                    exp_lof
                    obs_lof
                    lof_z
                    pLI
                }
            }
        }
        """

        clean_id = ensembl_id.split(".")[0]
        variables = {"gene_id": clean_id, "reference_genome": self.reference_genome}

        result = await self._execute_query(query, variables)

        if result and result.get("gene"):
            return self._extract_constraint_data(result["gene"])

        return None

    @retry_with_backoff(config=RetryConfig(max_retries=5))
    async def _execute_query(self, query: str, variables: dict) -> dict | None:
        """Execute a GraphQL query with retry logic and rate limiting."""
        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            response = await client.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                headers=self.headers,
            )

            data = response.json()

            if data.get("errors"):
                logger.sync_error(
                    "GraphQL errors in gnomAD response",
                    errors=data["errors"],
                    gene_symbol=variables.get("gene_symbol"),
                )
                return None

            result: dict[Any, Any] | None = data.get("data")
            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("retry-after")
                logger.sync_error(
                    "gnomAD rate limit hit",
                    status_code=429,
                    retry_after=retry_after,
                    gene_symbol=variables.get("gene_symbol"),
                )
                raise
            else:
                logger.sync_error(
                    "gnomAD API error",
                    status_code=e.response.status_code,
                    gene_symbol=variables.get("gene_symbol"),
                )
                raise

        except Exception as e:
            logger.sync_error(
                f"Unexpected error querying gnomAD: {str(e)}",
                gene_symbol=variables.get("gene_symbol"),
            )
            raise

    def _extract_constraint_data(self, gene_data: dict) -> dict[str, Any]:
        """Extract constraint scores from gnomAD GraphQL API response."""
        constraint = gene_data.get("gnomad_constraint", {})
        exac_constraint = gene_data.get("exac_constraint", {})

        if not constraint:
            if exac_constraint:
                return {
                    "source_version": "exac",
                    "gene_id": gene_data.get("gene_id"),
                    "gene_symbol": gene_data.get("symbol"),
                    "canonical_transcript": gene_data.get("canonical_transcript_id"),
                    "pli": exac_constraint.get("pLI"),
                    "lof_z": exac_constraint.get("lof_z"),
                    "mis_z": exac_constraint.get("mis_z"),
                    "syn_z": exac_constraint.get("syn_z"),
                    "obs_lof": exac_constraint.get("obs_lof"),
                    "exp_lof": exac_constraint.get("exp_lof"),
                    "obs_mis": exac_constraint.get("obs_mis"),
                    "exp_mis": exac_constraint.get("exp_mis"),
                    "obs_syn": exac_constraint.get("obs_syn"),
                    "exp_syn": exac_constraint.get("exp_syn"),
                    "flags": [],
                }
            return {
                "source_version": "gnomad_v4",
                "gene_id": gene_data.get("gene_id"),
                "gene_symbol": gene_data.get("symbol"),
                "gene_name": gene_data.get("name"),
                "canonical_transcript": gene_data.get("canonical_transcript_id"),
                "constraint_not_available": True,
                "message": "Constraint not available for this gene",
                "pli": None,
                "lof_z": None,
                "mis_z": None,
                "syn_z": None,
                "oe_lof": None,
                "obs_lof": None,
                "exp_lof": None,
            }

        annotations = {
            "source_version": "gnomad_v4",
            "gene_id": gene_data.get("gene_id"),
            "gene_symbol": gene_data.get("symbol"),
            "gene_name": gene_data.get("name"),
            "canonical_transcript": gene_data.get("canonical_transcript_id"),
            "pli": constraint.get("pLI"),
            "lof_z": constraint.get("lof_z"),
            "mis_z": constraint.get("mis_z"),
            "syn_z": constraint.get("syn_z"),
            "oe_lof": constraint.get("oe_lof"),
            "oe_lof_lower": constraint.get("oe_lof_lower"),
            "oe_lof_upper": constraint.get("oe_lof_upper"),
            "oe_mis": constraint.get("oe_mis"),
            "oe_mis_lower": constraint.get("oe_mis_lower"),
            "oe_mis_upper": constraint.get("oe_mis_upper"),
            "oe_syn": constraint.get("oe_syn"),
            "oe_syn_lower": constraint.get("oe_syn_lower"),
            "oe_syn_upper": constraint.get("oe_syn_upper"),
            "obs_lof": constraint.get("obs_lof"),
            "exp_lof": constraint.get("exp_lof"),
            "obs_mis": constraint.get("obs_mis"),
            "exp_mis": constraint.get("exp_mis"),
            "obs_syn": constraint.get("obs_syn"),
            "exp_syn": constraint.get("exp_syn"),
            "flags": constraint.get("flags", []),
        }

        return {k: v for k, v in annotations.items() if v is not None}

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """Fetch annotations for multiple genes.

        Loads bulk data once, then does fast local lookups. Falls back to
        GraphQL API for genes not found in the bulk file.
        """
        # Load bulk data if not already loaded
        try:
            await self.ensure_bulk_data_loaded()
        except Exception as e:
            logger.sync_warning(
                f"Failed to load gnomAD bulk data, falling back to API: {e}",
            )

        results: dict[int, dict[str, Any]] = {}
        api_fallback_genes: list[Gene] = []

        # Fast bulk lookups
        for gene in genes:
            if self._bulk_data is not None and gene.approved_symbol:
                bulk_result = self.lookup_gene(gene.approved_symbol)
                if bulk_result is not None:
                    results[gene.id] = bulk_result
                    continue
            api_fallback_genes.append(gene)

        if api_fallback_genes:
            logger.sync_info(
                "gnomAD bulk miss, falling back to API",
                bulk_hits=len(results),
                api_fallback=len(api_fallback_genes),
            )

        # API fallback for misses
        for i, gene in enumerate(api_fallback_genes):
            try:
                if i % 10 == 0 and api_fallback_genes:
                    logger.sync_info(
                        "Processing gnomAD API fallback",
                        progress=f"{i}/{len(api_fallback_genes)}",
                    )
                annotation = await self._fetch_via_api(gene)
                if annotation and self._is_valid_annotation(annotation):
                    results[gene.id] = annotation
            except Exception as e:
                logger.sync_error(
                    f"Failed to fetch gnomAD annotation for {gene.approved_symbol}",
                    error_detail=str(e),
                )
                if self.circuit_breaker and self.circuit_breaker.state == "open":
                    logger.sync_error(
                        "Circuit breaker open, stopping API fallback",
                    )
                    break

        return results

    def _is_valid_annotation(self, annotation_data: dict) -> bool:
        """Validate gnomAD annotation data."""
        if not super()._is_valid_annotation(annotation_data):
            return False

        if annotation_data.get("constraint_not_available"):
            return True

        constraint_fields = ["pli", "lof_z", "oe_lof", "mis_z", "syn_z"]
        return any(annotation_data.get(field) is not None for field in constraint_fields)

    async def get_transcript_constraint(self, transcript_id: str) -> dict | None:
        """Get constraint scores for a specific transcript."""
        query = """
        query transcript($transcript_id: String!, $reference_genome: ReferenceGenomeId!) {
            transcript(transcript_id: $transcript_id, reference_genome: $reference_genome) {
                transcript_id
                transcript_version
                gene_id
                gnomad_constraint {
                    exp_lof
                    exp_mis
                    exp_syn
                    obs_lof
                    obs_mis
                    obs_syn
                    oe_lof
                    oe_lof_lower
                    oe_lof_upper
                    oe_mis
                    oe_mis_lower
                    oe_mis_upper
                    oe_syn
                    oe_syn_lower
                    oe_syn_upper
                    lof_z
                    mis_z
                    syn_z
                    pLI
                    flags
                }
            }
        }
        """

        variables = {
            "transcript_id": transcript_id.split(".")[0],
            "reference_genome": self.reference_genome,
        }

        result = await self._execute_query(query, variables)

        if result and result.get("transcript"):
            transcript = result["transcript"]
            if transcript.get("gnomad_constraint"):
                return {
                    "transcript_id": transcript.get("transcript_id"),
                    "gene_id": transcript.get("gene_id"),
                    **transcript["gnomad_constraint"],
                }

        return None
