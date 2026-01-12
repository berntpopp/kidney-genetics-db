"""
gnomAD annotation source for gene constraint scores.
"""

from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource

logger = get_logger(__name__)


class GnomADAnnotationSource(BaseAnnotationSource):
    """
    gnomAD (Genome Aggregation Database) annotation source with proper rate limiting.

    Fetches gene constraint scores from gnomAD GraphQL API including:
    - pLI (probability of loss-of-function intolerance)
    - oe_lof (observed/expected ratio for loss-of-function variants)
    - lof_z (Z-score for loss-of-function variants)
    - mis_z (Z-score for missense variants)
    - syn_z (Z-score for synonymous variants)
    - And other constraint metrics
    """

    source_name = "gnomad"
    display_name = "gnomAD"
    version = "v4.0.0"

    # API configuration
    graphql_url = "https://gnomad.broadinstitute.org/api"
    headers = {"Content-Type": "application/json", "User-Agent": "KidneyGeneticsDB/1.0"}

    # Cache configuration
    cache_ttl_days = 90  # gnomAD data updates less frequently

    # Reference genome
    reference_genome = "GRCh38"  # Default to GRCh38 for v4

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """
        Fetch gnomAD constraint scores for a single gene.

        Args:
            gene: Gene object to fetch annotations for

        Returns:
            Dictionary of annotation data or None if not found
        """
        # Get Ensembl ID from HGNC annotations if available
        ensembl_id = None
        if hasattr(gene, "annotations") and gene.annotations:
            for ann in gene.annotations:
                if ann.source == "hgnc" and ann.annotations:
                    ensembl_id = ann.annotations.get("ensembl_gene_id")
                    break

        await logger.debug(
            "Starting gnomAD annotation fetch",
            gene_id=gene.id,
            gene_symbol=gene.approved_symbol,
            hgnc_id=gene.hgnc_id,
            ensembl_id=ensembl_id,
        )

        # Try to fetch by gene symbol first
        constraint_data = None

        if gene.approved_symbol:
            await logger.debug(
                "Attempting to fetch gnomAD data by symbol", gene_symbol=gene.approved_symbol
            )
            constraint_data = await self._fetch_by_symbol(gene.approved_symbol)
            if constraint_data:
                await logger.info(
                    "Successfully fetched gnomAD data by symbol",
                    gene_symbol=gene.approved_symbol,
                    has_constraint=bool(constraint_data.get("constraint_scores")),
                )

        # Fall back to Ensembl gene ID if available from HGNC annotations
        # if not constraint_data and ensembl_id:
        #     await logger.debug(
        #         "Attempting to fetch gnomAD data by Ensembl ID",
        #         ensembl_id=ensembl_id
        #     )
        #     constraint_data = await self._fetch_by_ensembl_id(ensembl_id)

        if not constraint_data:
            await logger.warning(
                "No gnomAD gene data found",
                gene_id=gene.id,
                gene_symbol=gene.approved_symbol,
                hgnc_id=gene.hgnc_id,
            )
            return None

        # Check if this is a "no constraint available" annotation
        if constraint_data.get("constraint_not_available"):
            await logger.info(
                "Gene found in gnomAD but constraint scores not available",
                gene_id=gene.id,
                gene_symbol=gene.approved_symbol,
                hgnc_id=gene.hgnc_id,
            )

        return constraint_data

    async def _fetch_by_symbol(self, symbol: str) -> dict | None:
        """Fetch gnomAD data by gene symbol."""
        await logger.debug(
            "Preparing gnomAD GraphQL query",
            gene_symbol=symbol,
            reference_genome=self.reference_genome,
        )

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
            gene_data = result["gene"]
            await logger.debug(
                "gnomAD API returned gene data",
                gene_symbol=symbol,
                gene_id=gene_data.get("gene_id"),
                has_gnomad_constraint=bool(gene_data.get("gnomad_constraint")),
                has_exac_constraint=bool(gene_data.get("exac_constraint")),
            )
            return self._extract_constraint_data(gene_data)
        else:
            await logger.debug(
                "gnomAD API returned no gene data",
                gene_symbol=symbol,
                result_keys=list(result.keys()) if result else None,
            )

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

        # Clean Ensembl ID (remove version if present)
        clean_id = ensembl_id.split(".")[0]

        variables = {"gene_id": clean_id, "reference_genome": self.reference_genome}

        result = await self._execute_query(query, variables)

        if result and result.get("gene"):
            return self._extract_constraint_data(result["gene"])

        return None

    @retry_with_backoff(config=RetryConfig(max_retries=5))
    async def _execute_query(self, query: str, variables: dict) -> dict | None:
        """
        Execute a GraphQL query with retry logic and rate limiting.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Query result data or None if error
        """
        # Apply rate limiting
        await self.apply_rate_limit()

        # Get configured HTTP client
        client = await self.get_http_client()

        try:
            response = await client.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                headers=self.headers,
            )

            data = response.json()

            await logger.debug(
                "gnomAD API response received",
                gene_symbol=variables.get("gene_symbol"),
                has_data=bool(data.get("data")),
                has_errors=bool(data.get("errors")),
                response_keys=list(data.keys()),
            )

            # Check for GraphQL errors
            if data.get("errors"):
                logger.sync_error(  # Keep as error
                    "GraphQL errors in gnomAD response",
                    errors=data["errors"],
                    gene_symbol=variables.get("gene_symbol"),
                )
                return None

            return data.get("data")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Parse Retry-After header if present
                retry_after = e.response.headers.get("retry-after")
                logger.sync_error(
                    "gnomAD rate limit hit",
                    status_code=429,
                    retry_after=retry_after,
                    gene_symbol=variables.get("gene_symbol"),
                )
                raise  # Let retry decorator handle it
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
        """
        Extract constraint scores from gnomAD API response.

        Args:
            gene_data: Gene data from GraphQL response

        Returns:
            Structured annotation dictionary
        """
        constraint = gene_data.get("gnomad_constraint", {})
        exac_constraint = gene_data.get("exac_constraint", {})

        logger.sync_debug(
            "Extracting constraint data",
            gene_symbol=gene_data.get("symbol"),
            has_gnomad_constraint=bool(constraint),
            has_exac_constraint=bool(exac_constraint),
            gnomad_pLI=constraint.get("pLI") if constraint else None,
            exac_pLI=exac_constraint.get("pLI") if exac_constraint else None,
        )

        if not constraint:
            # If no gnomAD v4 constraint, try ExAC constraint
            if exac_constraint:
                return {
                    "source_version": "exac",
                    "gene_id": gene_data.get("gene_id"),
                    "gene_symbol": gene_data.get("symbol"),
                    "canonical_transcript": gene_data.get("canonical_transcript_id"),
                    # ExAC constraint scores
                    "pli": exac_constraint.get("pLI"),
                    "lof_z": exac_constraint.get("lof_z"),
                    "mis_z": exac_constraint.get("mis_z"),
                    "syn_z": exac_constraint.get("syn_z"),
                    # Observed/Expected counts
                    "obs_lof": exac_constraint.get("obs_lof"),
                    "exp_lof": exac_constraint.get("exp_lof"),
                    "obs_mis": exac_constraint.get("obs_mis"),
                    "exp_mis": exac_constraint.get("exp_mis"),
                    "obs_syn": exac_constraint.get("obs_syn"),
                    "exp_syn": exac_constraint.get("exp_syn"),
                    "flags": [],
                }
            # No constraint data available in gnomAD or ExAC
            # Return a special marker annotation to indicate this gene was checked but has no data
            return {
                "source_version": "gnomad_v4",
                "gene_id": gene_data.get("gene_id"),
                "gene_symbol": gene_data.get("symbol"),
                "gene_name": gene_data.get("name"),
                "canonical_transcript": gene_data.get("canonical_transcript_id"),
                "constraint_not_available": True,
                "message": "Constraint not available for this gene",
                # Include empty constraint fields to maintain consistency
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
            # Core constraint scores
            "pli": constraint.get("pLI"),
            "lof_z": constraint.get("lof_z"),
            "mis_z": constraint.get("mis_z"),
            "syn_z": constraint.get("syn_z"),
            # Observed/Expected ratios
            "oe_lof": constraint.get("oe_lof"),
            "oe_lof_lower": constraint.get("oe_lof_lower"),
            "oe_lof_upper": constraint.get("oe_lof_upper"),
            "oe_mis": constraint.get("oe_mis"),
            "oe_mis_lower": constraint.get("oe_mis_lower"),
            "oe_mis_upper": constraint.get("oe_mis_upper"),
            "oe_syn": constraint.get("oe_syn"),
            "oe_syn_lower": constraint.get("oe_syn_lower"),
            "oe_syn_upper": constraint.get("oe_syn_upper"),
            # Raw counts
            "obs_lof": constraint.get("obs_lof"),
            "exp_lof": constraint.get("exp_lof"),
            "obs_mis": constraint.get("obs_mis"),
            "exp_mis": constraint.get("exp_mis"),
            "obs_syn": constraint.get("obs_syn"),
            "exp_syn": constraint.get("exp_syn"),
            # Flags for data quality
            "flags": constraint.get("flags", []),
        }

        # Remove None values to save space
        return {k: v for k, v in annotations.items() if v is not None}

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Fetch annotations for multiple genes with proper rate limiting.

        Note: gnomAD doesn't have a batch endpoint, so we fetch individually
        with rate limiting to avoid 429 errors.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene_id to annotation data
        """
        results = {}
        failed_genes = []

        # Process sequentially with rate limiting instead of concurrent batches
        for i, gene in enumerate(genes):
            try:
                # Show progress
                if i % 10 == 0:
                    logger.sync_info(
                        "Processing gnomAD annotations",
                        progress=f"{i}/{len(genes)}",
                        source=self.source_name,
                    )

                # Fetch with retry logic
                annotation = await self.fetch_annotation(gene)

                if annotation and self._is_valid_annotation(annotation):
                    results[gene.id] = annotation
                else:
                    failed_genes.append(gene.approved_symbol)

            except Exception as e:
                logger.sync_error(
                    f"Failed to fetch gnomAD annotation for {gene.approved_symbol}",
                    error_detail=str(e),
                )
                failed_genes.append(gene.approved_symbol)

                # If circuit breaker is open, stop processing
                if self.circuit_breaker and self.circuit_breaker.state == "open":
                    logger.sync_error(
                        "Circuit breaker open, stopping batch processing",
                        failed_count=len(failed_genes),
                    )
                    break

        if failed_genes:
            logger.sync_warning(
                "Failed to fetch gnomAD annotations",
                failed_genes=failed_genes[:10],  # Log first 10
                total_failed=len(failed_genes),
            )

        return results

    def _is_valid_annotation(self, annotation_data: dict) -> bool:
        """Validate gnomAD annotation data."""
        if not super()._is_valid_annotation(annotation_data):
            return False

        # Check if this is a "no constraint data available" annotation
        if annotation_data.get("constraint_not_available"):
            # This is a valid annotation indicating no constraint data exists
            return True

        # gnomAD specific: must have at least one constraint score
        constraint_fields = ["pli", "lof_z", "oe_lof", "mis_z", "syn_z"]
        has_constraint = any(annotation_data.get(field) is not None for field in constraint_fields)

        return has_constraint

    async def get_transcript_constraint(self, transcript_id: str) -> dict | None:
        """
        Get constraint scores for a specific transcript.

        Args:
            transcript_id: Ensembl transcript ID

        Returns:
            Transcript constraint data
        """
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
            "transcript_id": transcript_id.split(".")[0],  # Remove version
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
