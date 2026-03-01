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
from sqlalchemy.orm import Session

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

    def __init__(self, session: Session) -> None:
        """Initialize the MPO/MGI annotation source."""
        super().__init__(session)

        # Load configuration from YAML
        from app.core.datasource_config import ANNOTATION_SOURCE_CONFIG

        config = ANNOTATION_SOURCE_CONFIG.get("mpo_mgi", {})

        # API endpoints from config
        self.jax_base_url = config.get("jax_base_url", "https://www.informatics.jax.org")
        self.mousemine_url = config.get(
            "mousemine_url", "https://www.mousemine.org/mousemine/service"
        )

        # Root kidney/urinary phenotype term from config
        self.kidney_root_term = config.get("kidney_root_term", "MP:0005367")
        self.kidney_root_node = config.get("kidney_root_node", 117579)

        # Cache for MPO terms (24-hour TTL)
        self._mpo_terms_cache: set[str] | None = None
        self._mpo_cache_timestamp: datetime | None = None
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
                return str(response.text.strip())
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
        async def fetch_children(term_id: str, node_id: int, depth: int = 0) -> None:
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
            zygosity_data: dict[str, list[dict[str, Any]]] = {
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

    # ── Bulk query methods ──────────────────────────────────────────────

    # Maximum genes per bulk LOOKUP query (keeps URL under safe limits)
    BULK_CHUNK_SIZE = 100

    async def _bulk_query_phenotypes(
        self, gene_symbols: list[str], mpo_terms: set[str]
    ) -> dict[str, dict[str, Any]]:
        """
        Bulk query MouseMine HGene_MPhenotype for many genes at once.

        Sends comma-separated gene symbols in the LOOKUP value1 parameter,
        chunked to stay within URL length limits.

        Args:
            gene_symbols: List of human gene symbols to query
            mpo_terms: Set of kidney-related MPO term IDs

        Returns:
            Dict mapping human_gene_symbol → per-gene phenotype result
        """
        # Accumulate results across all chunks
        # Per-gene accumulators: mouse_symbols, all_phenotypes, kidney_phenotypes
        gene_mouse_symbols: dict[str, set[str]] = {}
        gene_all_pheno: dict[str, dict[str, str]] = {}
        gene_kidney_pheno: dict[str, dict[str, str]] = {}

        for chunk_start in range(0, len(gene_symbols), self.BULK_CHUNK_SIZE):
            chunk = gene_symbols[chunk_start : chunk_start + self.BULK_CHUNK_SIZE]
            csv_value = ",".join(chunk)

            try:
                await self.apply_rate_limit()
                client = await self.get_http_client()

                url = f"{self.mousemine_url}/template/results"
                params = {
                    "name": "HGene_MPhenotype",
                    "constraint1": "Gene",
                    "op1": "LOOKUP",
                    "value1": csv_value,
                    "extra1": "H. sapiens",
                    "format": "json",
                    "size": "0",  # unlimited
                }

                response = await client.get(url, params=params, timeout=120.0)
                if response.status_code != 200:
                    logger.sync_warning(
                        f"Bulk HGene_MPhenotype failed (chunk {chunk_start}): "
                        f"{response.status_code}"
                    )
                    continue

                data = response.json()
                results = data.get("results", [])

                # Columns: [human_id, human_symbol, human_organism,
                #            mouse_id, mouse_symbol, mouse_organism, mpo_id, mpo_name]
                for row in results:
                    if len(row) < 8:
                        continue
                    human_sym = row[1]  # human gene symbol from result
                    mouse_sym = row[4]
                    mpo_id = row[6]
                    mpo_name = row[7]

                    if human_sym not in gene_mouse_symbols:
                        gene_mouse_symbols[human_sym] = set()
                        gene_all_pheno[human_sym] = {}
                        gene_kidney_pheno[human_sym] = {}

                    if mouse_sym:
                        gene_mouse_symbols[human_sym].add(mouse_sym)
                    if mpo_id and mpo_name:
                        gene_all_pheno[human_sym][mpo_id] = mpo_name
                        if mpo_id in mpo_terms:
                            gene_kidney_pheno[human_sym][mpo_id] = mpo_name

            except Exception as e:
                logger.sync_error(f"Bulk HGene_MPhenotype error (chunk {chunk_start}): {e}")
                continue

        # Build per-gene result dicts
        out: dict[str, dict[str, Any]] = {}
        for sym in gene_symbols:
            kidney = gene_kidney_pheno.get(sym, {})
            kidney_list = [
                {"term": tid, "name": name} for tid, name in sorted(kidney.items())
            ]
            out[sym] = {
                "has_kidney_phenotype": len(kidney) > 0,
                "mouse_orthologs": sorted(gene_mouse_symbols.get(sym, set())),
                "phenotypes": kidney_list,
                "phenotype_count": len(kidney),
                "total_phenotypes": len(gene_all_pheno.get(sym, {})),
            }

        logger.sync_info(
            f"Bulk HGene_MPhenotype: {len(gene_symbols)} genes, "
            f"{sum(1 for v in out.values() if v['has_kidney_phenotype'])} with kidney phenotypes"
        )
        return out

    async def _bulk_query_zygosity(
        self,
        gene_mouse_map: dict[str, list[str]],
        mpo_terms: set[str],
    ) -> dict[str, dict[str, Any]]:
        """
        Bulk query MouseMine _Genotype_Phenotype for zygosity data.

        Sends comma-separated *mouse* gene symbols in the CONTAINS value1 parameter.

        Args:
            gene_mouse_map: Mapping of human_symbol → list of mouse orthologs
            mpo_terms: Set of kidney-related MPO term IDs

        Returns:
            Dict mapping human_gene_symbol → zygosity_analysis dict
        """
        # Invert map: mouse_symbol → human_symbol(s)
        mouse_to_human: dict[str, str] = {}
        all_mouse_symbols: list[str] = []
        for human_sym, mouse_syms in gene_mouse_map.items():
            for ms in mouse_syms:
                mouse_to_human[ms] = human_sym
                all_mouse_symbols.append(ms)

        # Accumulate zygosity data per human gene
        gene_zyg: dict[str, dict[str, list[dict[str, str]]]] = {}
        for human_sym in gene_mouse_map:
            gene_zyg[human_sym] = {"hm": [], "ht": [], "cn": [], "other": []}

        for chunk_start in range(0, len(all_mouse_symbols), self.BULK_CHUNK_SIZE):
            chunk = all_mouse_symbols[chunk_start : chunk_start + self.BULK_CHUNK_SIZE]
            csv_value = ",".join(chunk)

            try:
                await self.apply_rate_limit()
                client = await self.get_http_client()

                url = f"{self.mousemine_url}/template/results"
                params = {
                    "name": "_Genotype_Phenotype",
                    "constraint1": "OntologyAnnotation.subject.symbol",
                    "op1": "CONTAINS",
                    "value1": csv_value,
                    "format": "json",
                    "size": "0",  # unlimited
                }

                response = await client.get(url, params=params, timeout=120.0)
                if response.status_code != 200:
                    logger.sync_warning(
                        f"Bulk _Genotype_Phenotype failed (chunk {chunk_start}): "
                        f"{response.status_code}"
                    )
                    continue

                data = response.json()
                results = data.get("results", [])

                # Columns: [primaryId, symbol, background, zygosity, mpo_id, mpo_name]
                for row in results:
                    if len(row) < 6:
                        continue
                    mouse_sym = row[1]
                    zygosity = row[3]
                    mpo_id = row[4]
                    mpo_name = row[5]

                    resolved_human = mouse_to_human.get(mouse_sym)
                    if not resolved_human or not mpo_id or not mpo_name:
                        continue

                    entry = {"term": mpo_id, "name": mpo_name}
                    bucket = gene_zyg[resolved_human]
                    if zygosity == "hm":
                        bucket["hm"].append(entry)
                    elif zygosity == "ht":
                        bucket["ht"].append(entry)
                    elif zygosity == "cn":
                        bucket["cn"].append(entry)
                    else:
                        bucket["other"].append(entry)

            except Exception as e:
                logger.sync_error(
                    f"Bulk _Genotype_Phenotype error (chunk {chunk_start}): {e}"
                )
                continue

        # Build per-gene zygosity analysis
        out: dict[str, dict[str, Any]] = {}
        for human_sym, zyg in gene_zyg.items():
            hm_kidney = list(
                {p["term"]: p for p in zyg["hm"] if p["term"] in mpo_terms}.values()
            )
            ht_kidney = list(
                {p["term"]: p for p in zyg["ht"] if p["term"] in mpo_terms}.values()
            )
            cn_kidney = list(
                {p["term"]: p for p in zyg["cn"] if p["term"] in mpo_terms}.values()
            )

            hm_result = "true" if hm_kidney else "false"
            ht_result = "true" if ht_kidney else "false"

            out[human_sym] = {
                "homozygous": {
                    "has_kidney_phenotype": len(hm_kidney) > 0,
                    "phenotype_count": len(hm_kidney),
                    "phenotypes": hm_kidney,
                },
                "heterozygous": {
                    "has_kidney_phenotype": len(ht_kidney) > 0,
                    "phenotype_count": len(ht_kidney),
                    "phenotypes": ht_kidney,
                },
                "conditional": {
                    "has_kidney_phenotype": len(cn_kidney) > 0,
                    "phenotype_count": len(cn_kidney),
                    "phenotypes": cn_kidney,
                },
                "summary": f"hm ({hm_result}); ht ({ht_result})",
            }

        return out

    # ── Original per-gene query methods ────────────────────────────────

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
                from app.core.datasource_config import ANNOTATION_SOURCE_CONFIG

                config = ANNOTATION_SOURCE_CONFIG.get("mpo_mgi", {})
                cache_file_relative = config.get(
                    "mpo_kidney_terms_file", "data/mpo_kidney_terms.json"
                )

                # Build absolute path relative to backend directory
                backend_dir = Path(__file__).parent.parent.parent.parent
                cache_file = backend_dir / cache_file_relative

                if cache_file.exists():
                    # Read file in thread pool (non-blocking)
                    def read_json_file(path: Path) -> set[str]:
                        """Read and parse JSON file synchronously."""
                        with open(path, encoding="utf-8") as f:
                            data = json.load(f)
                            return {str(item) for item in data}

                    loaded_terms: set[str] = await asyncio.to_thread(read_json_file, cache_file)
                    self._mpo_terms_cache = loaded_terms
                    logger.sync_info(
                        f"Loaded {len(loaded_terms)} MPO terms from cache file (non-blocking)"
                    )
                else:
                    # Fetch terms from API and create cache file
                    logger.sync_info("MPO terms cache not found, fetching from API...")
                    fetched_terms = await self.fetch_kidney_mpo_terms()
                    self._mpo_terms_cache = fetched_terms

                    # Write file in thread pool (non-blocking)
                    def write_json_file(path: Path, data: set[str]) -> None:
                        """Write JSON file synchronously."""
                        path.parent.mkdir(exist_ok=True, parents=True)
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(sorted(data), f, indent=2)

                    await asyncio.to_thread(write_json_file, cache_file, fetched_terms)
                    logger.sync_info(
                        f"Fetched {len(fetched_terms)} MPO terms and saved to cache (non-blocking)"
                    )
                self._mpo_cache_timestamp = datetime.now(timezone.utc)

            # At this point, _mpo_terms_cache is guaranteed to be set
            mpo_terms = self._mpo_terms_cache
            if mpo_terms is None:
                raise RuntimeError("MPO terms cache should be loaded at this point")

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
        Batch fetch annotations for multiple genes using bulk MouseMine queries.

        Uses comma-separated LOOKUP queries to fetch all genes in ~6 chunked
        requests instead of 1,142 individual requests.  Falls back to per-gene
        queries for any genes missing from bulk results.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene_id to annotation data
        """
        results: dict[int, dict[str, Any]] = {}

        # Pre-fetch MPO terms once for the batch
        if self._mpo_terms_cache is None or self._is_mpo_cache_expired():
            logger.sync_info("Pre-fetching MPO terms for batch processing")
            self._mpo_terms_cache = await self.fetch_kidney_mpo_terms()
            self._mpo_cache_timestamp = datetime.now(timezone.utc)

        mpo_terms = self._mpo_terms_cache
        if mpo_terms is None:
            raise RuntimeError("MPO terms cache should be loaded at this point")

        # Build symbol → gene mapping
        symbol_to_gene: dict[str, Gene] = {g.approved_symbol: g for g in genes}
        all_symbols = list(symbol_to_gene.keys())

        # Step 1: Bulk HGene_MPhenotype query (phenotypes + mouse orthologs)
        pheno_map = await self._bulk_query_phenotypes(all_symbols, mpo_terms)

        # Step 2: Bulk _Genotype_Phenotype query for genes with mouse orthologs
        gene_mouse_map: dict[str, list[str]] = {}
        for sym, pheno in pheno_map.items():
            orthologs = pheno.get("mouse_orthologs", [])
            if orthologs:
                gene_mouse_map[sym] = orthologs

        zyg_map: dict[str, dict[str, Any]] = {}
        if gene_mouse_map:
            zyg_map = await self._bulk_query_zygosity(gene_mouse_map, mpo_terms)

        # Step 3: Assemble final per-gene results
        for sym, gene in symbol_to_gene.items():
            gene_pheno = pheno_map.get(sym)
            if gene_pheno is None:
                # Gene wasn't in bulk results at all — skip (will be caught by fallback)
                continue

            # Merge zygosity data
            zyg = zyg_map.get(sym)
            if zyg is None:
                zyg = {
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
                    "summary": "hm (false); ht (false)",
                }

            # Combine into the full result structure
            # Use zygosity phenotypes for has_kidney_phenotype and counts
            # when zygosity data is available (more detailed)
            all_kidney = list(
                {
                    p["term"]: p
                    for cat in ["homozygous", "heterozygous", "conditional"]
                    for p in zyg[cat]["phenotypes"]
                }.values()
            )

            # Prefer zygosity-derived phenotypes if available, else use pheno_map
            if all_kidney or not gene_pheno.get("has_kidney_phenotype"):
                kidney_phenotypes = all_kidney
                has_kidney = len(all_kidney) > 0
            else:
                kidney_phenotypes = gene_pheno.get("phenotypes", [])
                has_kidney = gene_pheno.get("has_kidney_phenotype", False)

            results[gene.id] = {
                "gene_symbol": sym,
                "has_kidney_phenotype": has_kidney,
                "mouse_orthologs": gene_pheno.get("mouse_orthologs", []),
                "phenotypes": kidney_phenotypes,
                "phenotype_count": len(kidney_phenotypes),
                "mpo_terms_searched": len(mpo_terms),
                "zygosity_analysis": zyg,
            }

        # Step 4: Fallback — per-gene query for any genes not in bulk results
        missing_genes = [g for g in genes if g.id not in results]
        if missing_genes:
            logger.sync_info(
                f"Falling back to per-gene queries for {len(missing_genes)} genes"
            )
            for gene in missing_genes:
                try:
                    result = await self.fetch_annotation(gene)
                    if isinstance(result, dict):
                        results[gene.id] = result
                except Exception as e:
                    logger.sync_error(
                        f"Per-gene fallback failed for {gene.approved_symbol}: {e}"
                    )

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
