"""
gnomAD annotation source for gene constraint scores.
"""

from typing import Any

import httpx

from app.core.logging import get_logger
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource

logger = get_logger(__name__)


class GnomADAnnotationSource(BaseAnnotationSource):
    """
    gnomAD (Genome Aggregation Database) annotation source.

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
    cache_ttl_days = 30  # gnomAD data updates less frequently

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
        # Try to fetch by gene symbol first
        constraint_data = None

        if gene.approved_symbol:
            constraint_data = await self._fetch_by_symbol(gene.approved_symbol)

        # Fall back to Ensembl gene ID
        # if not constraint_data and gene.ensembl_gene_id:
        #     constraint_data = await self._fetch_by_ensembl_id(gene.ensembl_gene_id)

        if not constraint_data:
            logger.sync_warning(
                "No gnomAD constraint data found for gene", gene_symbol=gene.approved_symbol
            )
            return None

        return constraint_data

    async def _fetch_by_symbol(self, symbol: str) -> dict | None:
        """Fetch gnomAD data by gene symbol."""
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

        # Clean Ensembl ID (remove version if present)
        clean_id = ensembl_id.split(".")[0]

        variables = {"gene_id": clean_id, "reference_genome": self.reference_genome}

        result = await self._execute_query(query, variables)

        if result and result.get("gene"):
            return self._extract_constraint_data(result["gene"])

        return None

    async def _execute_query(self, query: str, variables: dict) -> dict | None:
        """
        Execute a GraphQL query against the gnomAD API.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Query result data or None if error
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.graphql_url,
                    json={"query": query, "variables": variables},
                    headers=self.headers,
                    timeout=60.0,  # Longer timeout for GraphQL
                )

                if response.status_code == 200:
                    data = response.json()

                    # Check for GraphQL errors
                    if data.get("errors"):
                        logger.sync_error(
                            "GraphQL errors in gnomAD response", errors=data["errors"]
                        )
                        return None

                    return data.get("data")
                else:
                    logger.sync_error(
                        "gnomAD API error",
                        status_code=response.status_code,
                        response=response.text[:500],
                    )

            except Exception as e:
                logger.sync_error(f"Error querying gnomAD API: {str(e)}", variables=variables)

        return None

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
            return None

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
        Fetch annotations for multiple genes.

        Note: gnomAD doesn't have a batch endpoint, so we fetch individually
        but use async to parallelize requests.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene_id to annotation data
        """
        import asyncio

        results = {}

        # Create tasks for all genes
        tasks = []
        for gene in genes:
            tasks.append(self.fetch_annotation(gene))

        # Execute all tasks concurrently (limit concurrency to avoid rate limiting)
        # Process in smaller batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch_tasks = tasks[i : i + batch_size]
            batch_genes = genes[i : i + batch_size]

            annotations = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Map results back to gene IDs
            for gene, annotation in zip(batch_genes, annotations, strict=False):
                if annotation and not isinstance(annotation, Exception):
                    results[gene.id] = annotation
                elif isinstance(annotation, Exception):
                    logger.sync_error(
                        "Error fetching annotation for gene",
                        gene_symbol=gene.approved_symbol,
                        error=str(annotation),
                    )

            # Small delay between batches to be respectful to the API
            if i + batch_size < len(tasks):
                await asyncio.sleep(1)

        return results

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
