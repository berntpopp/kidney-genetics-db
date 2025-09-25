"""
MPO/MGI Mouse Phenotype Annotation Source

Identifies genes with kidney phenotypes in mouse models using:
1. JAX Mammalian Phenotype Ontology (MPO) API for term collection
2. MouseMine database for ortholog phenotype mapping
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, retry_with_backoff
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource

logger = get_logger(__name__)


class MPOMGIAnnotationSource(BaseAnnotationSource):
    """
    Mouse phenotype annotations from JAX MPO and MouseMine

    Identifies genes with kidney/urinary phenotypes in knockout mouse models
    by recursively collecting MPO terms and querying MouseMine for orthologs.
    """

    source_name = "mpo_mgi"
    display_name = "MPO/MGI Mouse Phenotypes"
    version = "1.0"  # Our implementation version

    # Cache configuration
    cache_ttl_days = 90

    # API endpoints
    jax_base_url = "https://www.informatics.jax.org"
    mousemine_url = "https://www.mousemine.org/mousemine/service"

    # Root kidney/urinary phenotype term
    kidney_root_term = "MP:0005367"  # renal/urinary system phenotype
    kidney_root_node = 117579

    def __init__(self, session):
        """Initialize the MPO/MGI annotation source."""
        super().__init__(session)

        # Cache for MPO terms (24-hour TTL)
        self._mpo_terms_cache = None
        self._mpo_cache_timestamp = None
        self.mpo_cache_ttl = timedelta(hours=24)

        # Update source configuration
        if self.source_record:
            self.source_record.update_frequency = "weekly"
            self.source_record.description = "Mouse model kidney phenotypes from JAX and MGI"
            self.source_record.base_url = self.jax_base_url
            self.session.commit()

    def _is_mpo_cache_expired(self) -> bool:
        """Check if MPO terms cache is expired"""
        if not self._mpo_cache_timestamp:
            return True
        return datetime.now(timezone.utc) - self._mpo_cache_timestamp > self.mpo_cache_ttl

    @retry_with_backoff(config=RetryConfig(max_retries=3))
    async def _get_mousemine_version(self) -> str:
        """Fetch the current MouseMine version"""
        await self.apply_rate_limit()
        client = await self.get_http_client()

        try:
            response = await client.get(f"{self.mousemine_url}/version", timeout=10.0)
            if response.status_code == 200:
                return response.text.strip()
        except Exception as e:
            logger.sync_warning(f"Failed to fetch MouseMine version: {e}")

        # Fallback to a default if API fails
        return "unknown"

    async def fetch_kidney_mpo_terms(self) -> set[str]:
        """
        Recursively fetch all descendant terms of kidney/urinary phenotype.
        Returns set of MPO term IDs.
        """
        all_terms = set()
        all_terms.add(self.kidney_root_term)  # Include root term

        @retry_with_backoff(config=RetryConfig(max_retries=3))
        async def fetch_children(term_id: str, node_id: int, depth: int = 0):
            """Recursive function to fetch all children of a term"""
            if depth > 20:  # Safety limit for recursion depth
                logger.sync_warning(f"Max recursion depth reached for term {term_id}")
                return

            try:
                # Query JAX API for children
                url = f"{self.jax_base_url}/vocab/mp_ontology/treeChildren"
                params = {"id": term_id, "nodeID": str(node_id), "edgeType": "is-a"}

                await self.apply_rate_limit()
                client = await self.get_http_client()

                response = await client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                data = response.json()

                # JAX API returns a list with the node as first element
                if isinstance(data, list) and data:
                    node_data = data[0]
                    children = node_data.get("children", []) if isinstance(node_data, dict) else []
                else:
                    children = []

                # Process each child
                for child in children:
                    if isinstance(child, dict):
                        # Extract data from nested structure
                        child_data = child.get("data", {})
                        child_term = child_data.get("accID")
                        child_node = child.get("id")

                        if child_term and child_term not in all_terms:
                            all_terms.add(child_term)

                            # Check if has children and recurse
                            # The children field can be True, False, or an array
                            has_children = child.get("children")
                            if has_children is True or isinstance(has_children, list):
                                if child_node:
                                    await fetch_children(child_term, int(child_node), depth + 1)

            except Exception as e:
                logger.sync_error(f"Error fetching children for {term_id}: {str(e)}")

        # Start recursion from root
        logger.sync_info(f"Fetching kidney MPO terms from root {self.kidney_root_term}")
        await fetch_children(self.kidney_root_term, self.kidney_root_node)

        logger.sync_info(f"Collected {len(all_terms)} kidney-related MPO terms")
        return all_terms

    async def query_mousemine_zygosity_phenotypes(
        self, human_gene_symbol: str, mpo_terms: set[str]
    ) -> dict[str, Any] | None:
        """
        Query MouseMine for mouse orthologs with zygosity-specific kidney phenotypes.
        Uses the _Genotype_Phenotype template to get real zygosity data.

        Args:
            human_gene_symbol: Human gene symbol to search
            mpo_terms: Set of MPO term IDs to filter by

        Returns:
            Dictionary with zygosity-specific phenotype information or None
        """
        try:
            # First get mouse ortholog symbol(s) using the original approach
            base_result = await self.query_mousemine_phenotypes(human_gene_symbol, mpo_terms)

            if not base_result or not base_result.get("mouse_orthologs"):
                # No mouse orthologs found
                return self._create_empty_zygosity_result(human_gene_symbol, mpo_terms)

            mouse_symbols = base_result.get("mouse_orthologs", [])
            if not mouse_symbols:
                return self._create_empty_zygosity_result(human_gene_symbol, mpo_terms)

            # Use the first mouse ortholog symbol to query genotype/phenotype data
            mouse_symbol = mouse_symbols[0]

            async with httpx.AsyncClient() as client:
                # Query the _Genotype_Phenotype template for zygosity-specific phenotypes
                logger.sync_debug(f"Querying MouseMine for zygosity phenotypes of {mouse_symbol}")
                url = f"{self.mousemine_url}/template/results"
                params = {
                    "name": "_Genotype_Phenotype",
                    "constraint1": "OntologyAnnotation.subject.symbol",
                    "op1": "CONTAINS",
                    "value1": mouse_symbol,
                    "format": "json",
                    "size": "10000",  # Get all genotype phenotypes
                }

                response = await client.get(url, params=params, timeout=30.0)

                if response.status_code != 200:
                    logger.sync_warning(
                        f"Genotype phenotype query failed for {mouse_symbol}: {response.status_code}"
                    )
                    return self._create_empty_zygosity_result(human_gene_symbol, mpo_terms)

                data = response.json()
                results = data.get("results", [])

            if not results:
                return self._create_empty_zygosity_result(human_gene_symbol, mpo_terms)

            # Process results by zygosity
            # Column indices: 0=primaryId, 1=symbol, 2=background, 3=zygosity, 4=mpo_id, 5=mpo_name
            zygosity_data = {
                "hm": [],  # homozygous
                "ht": [],  # heterozygous
                "cn": [],  # conditional
                "other": [],  # other zygosity types
            }

            for row in results:
                if len(row) >= 6:
                    zygosity = row[3]  # Zygosity column
                    mpo_id = row[4]  # MPO term ID
                    mpo_name = row[5]  # MPO term name

                    if mpo_id and mpo_name:
                        phenotype_entry = {"term": mpo_id, "name": mpo_name}

                        if zygosity == "hm":
                            zygosity_data["hm"].append(phenotype_entry)
                        elif zygosity == "ht":
                            zygosity_data["ht"].append(phenotype_entry)
                        elif zygosity == "cn":
                            zygosity_data["cn"].append(phenotype_entry)
                        else:
                            zygosity_data["other"].append(phenotype_entry)

            # Filter by kidney-related MPO terms and create analysis
            hm_kidney_phenotypes = [p for p in zygosity_data["hm"] if p["term"] in mpo_terms]
            ht_kidney_phenotypes = [p for p in zygosity_data["ht"] if p["term"] in mpo_terms]
            cn_kidney_phenotypes = [p for p in zygosity_data["cn"] if p["term"] in mpo_terms]

            # Remove duplicates while preserving order
            hm_kidney_phenotypes = list({p["term"]: p for p in hm_kidney_phenotypes}.values())
            ht_kidney_phenotypes = list({p["term"]: p for p in ht_kidney_phenotypes}.values())
            cn_kidney_phenotypes = list({p["term"]: p for p in cn_kidney_phenotypes}.values())

            # Create summary in R-compatible format (matching original R implementation)
            hm_result = "true" if hm_kidney_phenotypes else "false"
            ht_result = "true" if ht_kidney_phenotypes else "false"
            summary = f"hm ({hm_result}); ht ({ht_result})"

            # Build complete result - include all zygosity types in total
            all_kidney_phenotypes = (
                hm_kidney_phenotypes + ht_kidney_phenotypes + cn_kidney_phenotypes
            )
            # Remove duplicates from combined list
            all_kidney_phenotypes = list({p["term"]: p for p in all_kidney_phenotypes}.values())

            return {
                "gene_symbol": human_gene_symbol,
                "has_kidney_phenotype": len(all_kidney_phenotypes) > 0,
                "mouse_orthologs": mouse_symbols,
                "phenotypes": all_kidney_phenotypes,
                "phenotype_count": len(all_kidney_phenotypes),
                "mpo_terms_searched": len(mpo_terms),
                "zygosity_analysis": {
                    "homozygous": {
                        "has_kidney_phenotype": len(hm_kidney_phenotypes) > 0,
                        "phenotype_count": len(hm_kidney_phenotypes),
                        "phenotypes": hm_kidney_phenotypes,
                    },
                    "heterozygous": {
                        "has_kidney_phenotype": len(ht_kidney_phenotypes) > 0,
                        "phenotype_count": len(ht_kidney_phenotypes),
                        "phenotypes": ht_kidney_phenotypes,
                    },
                    "conditional": {
                        "has_kidney_phenotype": len(cn_kidney_phenotypes) > 0,
                        "phenotype_count": len(cn_kidney_phenotypes),
                        "phenotypes": cn_kidney_phenotypes,
                    },
                    "summary": summary,
                },
            }

        except Exception as e:
            logger.sync_error(
                f"Error querying MouseMine zygosity phenotypes for {human_gene_symbol}: {str(e)}"
            )
            return None

    def _create_empty_zygosity_result(
        self, human_gene_symbol: str, mpo_terms: set[str]
    ) -> dict[str, Any]:
        """Create an empty result structure with zygosity analysis"""
        return {
            "gene_symbol": human_gene_symbol,
            "has_kidney_phenotype": False,
            "mouse_orthologs": [],
            "phenotypes": [],
            "phenotype_count": 0,
            "mpo_terms_searched": len(mpo_terms),
            "zygosity_analysis": {
                "homozygous": {
                    "has_kidney_phenotype": False,
                    "phenotype_count": 0,
                    "phenotypes": [],
                },
                "heterozygous": {
                    "has_kidney_phenotype": False,
                    "phenotype_count": 0,
                    "phenotypes": [],
                },
                "conditional": {
                    "has_kidney_phenotype": False,
                    "phenotype_count": 0,
                    "phenotypes": [],
                },
                "summary": "hm (NA); ht (NA)",
            },
        }

    async def query_mousemine_phenotypes(
        self, human_gene_symbol: str, mpo_terms: set[str]
    ) -> dict[str, Any] | None:
        """
        Query MouseMine for mouse orthologs with kidney phenotypes.
        Uses the HGene_MPhenotype template like the original R implementation.

        Args:
            human_gene_symbol: Human gene symbol to search
            mpo_terms: Set of MPO term IDs to filter by (for comparison)

        Returns:
            Dictionary with phenotype information or None
        """
        try:
            # Use the HGene_MPhenotype template via REST API
            await self.apply_rate_limit()
            client = await self.get_http_client()

            # Query for all phenotypes of the human gene's mouse ortholog
            url = f"{self.mousemine_url}/template/results"
            params = {
                "name": "HGene_MPhenotype",
                "constraint1": "Gene",
                "op1": "LOOKUP",
                "value1": human_gene_symbol,
                "extra1": "H. sapiens",
                "format": "json",
                "size": "10000",  # Get all phenotypes
            }

            response = await client.get(url, params=params, timeout=30.0)

            if response.status_code != 200:
                logger.sync_warning(
                    f"MouseMine template query failed for {human_gene_symbol}: {response.status_code}"
                )
                return {
                    "has_kidney_phenotype": False,
                    "mouse_orthologs": [],
                    "phenotypes": [],
                    "phenotype_count": 0,
                }

            data = response.json()
            results = data.get("results", [])

            if not results:
                # No mouse ortholog or no phenotypes
                return {
                    "has_kidney_phenotype": False,
                    "mouse_orthologs": [],
                    "phenotypes": [],
                    "phenotype_count": 0,
                }

            # Parse results
            # Columns: [human_id, human_symbol, human_organism, mouse_id, mouse_symbol, mouse_organism, mpo_id, mpo_name]
            mouse_symbols = set()
            all_phenotypes = {}
            kidney_phenotypes = {}

            for row in results:
                if len(row) >= 8:
                    mouse_symbol = row[4]  # Mouse gene symbol
                    mpo_id = row[6]  # MPO term ID
                    mpo_name = row[7]  # MPO term name

                    if mouse_symbol:
                        mouse_symbols.add(mouse_symbol)

                    if mpo_id and mpo_name:
                        all_phenotypes[mpo_id] = mpo_name

                        # Check if it's a kidney phenotype
                        # ONLY use MPO term matching (no keyword matching)
                        if mpo_id in mpo_terms:
                            kidney_phenotypes[mpo_id] = mpo_name

            # Format phenotypes as list of objects with term and name separated
            # Include ALL matched phenotypes, no truncation
            kidney_phenotype_list = [
                {"term": term_id, "name": name}
                for term_id, name in sorted(kidney_phenotypes.items())
            ]  # NO LIMIT - return all matches

            return {
                "has_kidney_phenotype": len(kidney_phenotypes) > 0,
                "mouse_orthologs": list(mouse_symbols),
                "phenotypes": kidney_phenotype_list,
                "phenotype_count": len(kidney_phenotypes),
                "total_phenotypes": len(all_phenotypes),
            }

        except Exception as e:
            logger.sync_error(f"Error querying MouseMine for {human_gene_symbol}: {str(e)}")
            return None

    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """
        Fetch MPO/MGI annotation for a gene.

        Args:
            gene: Gene object to fetch annotations for

        Returns:
            Dictionary with annotation data or None if not found
        """
        try:
            # Get MPO terms (with caching)
            if self._mpo_terms_cache is None or self._is_mpo_cache_expired():
                logger.sync_info("Loading MPO terms from cache or fetching")
                # Try to load from file first
                import json
                from pathlib import Path

                # Get cache file path from config
                from app.core.datasource_config import get_annotation_source_config
                config = get_annotation_source_config("mpo_mgi") or {}
                cache_file_relative = config.get("mpo_kidney_terms_file", "data/mpo_kidney_terms.json")

                # Build absolute path relative to backend directory
                backend_dir = Path(__file__).parent.parent.parent.parent
                cache_file = backend_dir / cache_file_relative

                if cache_file.exists():
                    with open(cache_file) as f:
                        self._mpo_terms_cache = set(json.load(f))
                    logger.sync_info(
                        f"Loaded {len(self._mpo_terms_cache)} MPO terms from cache file"
                    )
                else:
                    # If no file, just use empty set to avoid timeout
                    logger.sync_warning("MPO terms file not found, using empty set")
                    self._mpo_terms_cache = set()
                self._mpo_cache_timestamp = datetime.now(timezone.utc)

            mpo_terms = self._mpo_terms_cache

            # Query MouseMine for this gene with zygosity information
            result = await self.query_mousemine_zygosity_phenotypes(gene.approved_symbol, mpo_terms)

            if result is None:
                # Query failed, return minimal data with zygosity structure
                return {
                    "gene_symbol": gene.approved_symbol,
                    "has_kidney_phenotype": False,
                    "mouse_orthologs": [],
                    "phenotypes": [],
                    "phenotype_count": 0,
                    "mpo_terms_searched": len(mpo_terms),
                    "zygosity_analysis": {
                        "homozygous": {
                            "has_kidney_phenotype": False,
                            "phenotype_count": 0,
                            "phenotypes": [],
                        },
                        "heterozygous": {
                            "has_kidney_phenotype": False,
                            "phenotype_count": 0,
                            "phenotypes": [],
                        },
                        "conditional": {
                            "has_kidney_phenotype": False,
                            "phenotype_count": 0,
                            "phenotypes": [],
                        },
                        "summary": "hm (NA); ht (NA)",
                    },
                }

            # Add metadata to result
            result.update(
                {"gene_symbol": gene.approved_symbol, "mpo_terms_searched": len(mpo_terms)}
            )

            return result

        except Exception as e:
            logger.sync_error(
                f"Error fetching MPO/MGI annotation for {gene.approved_symbol}: {str(e)}"
            )
            return None

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Batch fetch annotations for multiple genes.

        Pre-fetches MPO terms once then queries genes in parallel.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene_id to annotation data
        """
        results = {}

        # Pre-fetch MPO terms once for the batch
        if self._mpo_terms_cache is None or self._is_mpo_cache_expired():
            logger.sync_info("Pre-fetching MPO terms for batch processing")
            self._mpo_terms_cache = await self.fetch_kidney_mpo_terms()
            self._mpo_cache_timestamp = datetime.now(timezone.utc)

        # Process genes in parallel (limit concurrency)
        batch_size = 5  # MouseMine can be slow, limit concurrent requests

        for i in range(0, len(genes), batch_size):
            batch = genes[i : i + batch_size]

            # Create tasks for this batch
            tasks = [self.fetch_annotation(gene) for gene in batch]

            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for gene, result in zip(batch, batch_results, strict=False):
                if isinstance(result, Exception):
                    logger.sync_error(
                        f"Failed to fetch MPO/MGI for {gene.approved_symbol}: {result}"
                    )
                    results[gene.id] = None
                else:
                    results[gene.id] = result

            # Small delay between batches to avoid overwhelming MouseMine
            if i + batch_size < len(genes):
                await asyncio.sleep(0.5)

        return results

    async def update_gene(self, gene: Gene) -> bool:
        """
        Update annotations for a single gene.

        Args:
            gene: Gene object to update

        Returns:
            True if successful, False otherwise
        """
        try:
            annotation_data = await self.fetch_annotation(gene)

            if annotation_data:
                self.store_annotation(
                    gene,
                    annotation_data,
                    metadata={
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "mousemine_version": await self._get_mousemine_version(),
                    },
                )
                return True

            return False

        except Exception as e:
            logger.sync_error(f"Failed to update MPO/MGI for {gene.approved_symbol}: {str(e)}")
            return False

    def validate_annotation(self, annotation_data: dict[str, Any]) -> bool:
        """Validate that annotation data has required fields"""
        required_fields = [
            "has_kidney_phenotype",
            "mouse_orthologs",
            "phenotypes",
            "phenotype_count",
        ]
        return all(field in annotation_data for field in required_fields)

    def get_summary_fields(self) -> dict[str, str]:
        """
        Get fields to include in materialized view.
        Returns mapping of JSONB paths to column names.
        """
        return {
            "has_mouse_kidney_phenotype": "(annotations->>'has_kidney_phenotype')::BOOLEAN",
            "mouse_phenotype_count": "(annotations->>'phenotype_count')::INTEGER",
            "mouse_orthologs": "annotations->'mouse_orthologs'",
        }
