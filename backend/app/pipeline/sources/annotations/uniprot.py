"""
UniProt Annotation Source

Fetches protein domain and structural feature data from the UniProt REST API.
Uses ID Mapping API for batch requests (single job for all genes) with
OR-query fallback.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.retry_utils import RetryConfig, SimpleRateLimiter, retry_with_backoff
from app.models.gene import Gene
from app.pipeline.sources.annotations.base import BaseAnnotationSource

logger = get_logger(__name__)

# Fields requested from UniProt search and ID Mapping endpoints
_UNIPROT_FIELDS = (
    "accession,id,gene_names,protein_name,length,organism_name,"
    "cc_function,cc_subcellular_location,ft_domain,ft_region,"
    "ft_motif,ft_transmem,ft_signal,ft_propep,ft_chain,"
    "xref_pfam,xref_interpro"
)

# ID Mapping polling configuration
_ID_MAPPING_POLL_INTERVAL = 3.0  # seconds between status checks
_ID_MAPPING_TIMEOUT = 120.0  # max seconds to wait for job completion


def _escape_uniprot_query(symbol: str) -> str:
    """Escape special characters for UniProt search query.

    UniProt uses Lucene query syntax, so special characters like colons,
    parentheses, and brackets need to be escaped to prevent query injection.
    """
    return symbol.replace(":", "\\:").replace("(", "\\(").replace(")", "\\)")


class UniProtAnnotationSource(BaseAnnotationSource):
    """
    UniProt protein domain annotation source.

    Fetches protein domains, families, and structural features for visualization.
    Uses ID Mapping API for batch requests (single job) with OR-query fallback.
    """

    source_name = "uniprot"
    display_name = "UniProt"
    version = "1.0"

    # Base configuration
    base_url = "https://rest.uniprot.org"

    # Default values (overridden by config)
    batch_size = 100  # OR-query fallback limit

    def __init__(self, session: Session) -> None:
        """Initialize the UniProt annotation source."""
        super().__init__(session)

        # Load configuration
        from app.core.datasource_config import get_annotation_config

        config = get_annotation_config("uniprot") or {}

        # Apply UniProt-specific configuration
        self.batch_size = config.get("batch_size", 100)

        # Initialize rate limiter (5 req/s for UniProt)
        self.rate_limiter = SimpleRateLimiter(requests_per_second=self.requests_per_second)

        # Update source configuration
        if self.source_record:
            self.source_record.update_frequency = "monthly"
            self.source_record.description = (
                "Protein domain and structural feature data from UniProt"
            )
            self.source_record.base_url = self.base_url
            self.session.commit()

    def _is_valid_annotation(self, annotation_data: dict) -> bool:
        """Validate UniProt annotation data."""
        if not super()._is_valid_annotation(annotation_data):
            return False

        # UniProt specific: must have accession and gene_symbol
        required_fields = ["accession", "gene_symbol"]
        has_required = all(field in annotation_data for field in required_fields)

        return has_required

    @retry_with_backoff(config=RetryConfig(max_retries=5))
    async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
        """
        Fetch UniProt annotation for a single gene.

        Args:
            gene: Gene object to fetch annotations for

        Returns:
            Dictionary with annotation data or None if not found
        """
        await self.rate_limiter.wait()

        try:
            client = await self.get_http_client()

            # Search for reviewed human protein by gene name
            # Escape special characters to prevent query injection
            escaped_symbol = _escape_uniprot_query(gene.approved_symbol)
            query = f"(gene_exact:{escaped_symbol}) AND (organism_id:9606) AND (reviewed:true)"
            url = f"{self.base_url}/uniprotkb/search"
            params = {
                "query": query,
                "format": "json",
                "fields": _UNIPROT_FIELDS,
                "size": "1",
            }

            response = await client.get(
                url,
                params=params,
                headers={
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                logger.sync_warning(
                    "Unexpected status from UniProt",
                    gene_symbol=gene.approved_symbol,
                    status_code=response.status_code,
                )
                return None

            data = response.json()
            results = data.get("results", [])

            if not results:
                logger.sync_debug("Gene not found in UniProt", gene_symbol=gene.approved_symbol)
                return None

            return self._parse_protein_data(gene.approved_symbol, results[0])

        except httpx.HTTPStatusError as e:
            logger.sync_error(
                "HTTP error fetching UniProt data",
                gene_symbol=gene.approved_symbol,
                status_code=e.response.status_code,
            )
            raise

        except Exception as e:
            logger.sync_error(
                "Error fetching UniProt annotation",
                gene_symbol=gene.approved_symbol,
                error_detail=str(e),
            )
            return None

    def _parse_protein_data(self, gene_symbol: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """
        Parse UniProt API response into annotation format.

        Args:
            gene_symbol: Gene symbol for reference
            data: Raw API response for single protein

        Returns:
            Parsed annotation dictionary
        """
        if not data:
            return None

        # Extract primary accession
        accession = data.get("primaryAccession")
        if not accession:
            return None

        # Parse domains from features
        domains = self._parse_domains(data)

        # Parse Pfam and InterPro references
        pfam_refs = self._parse_database_refs(data, "Pfam")
        interpro_refs = self._parse_database_refs(data, "InterPro")

        # Extract protein name
        protein_name = ""
        protein_desc = data.get("proteinDescription", {})
        if protein_desc:
            recommended = protein_desc.get("recommendedName", {})
            if recommended:
                full_name = recommended.get("fullName", {})
                protein_name = full_name.get("value", "")

        # Extract function from comments
        function_text = ""
        comments = data.get("comments", [])
        for comment in comments:
            if comment.get("commentType") == "FUNCTION":
                texts = comment.get("texts", [])
                if texts:
                    function_text = texts[0].get("value", "")
                    break

        annotation = {
            "accession": accession,
            "entry_name": data.get("uniProtkbId"),
            "gene_symbol": gene_symbol,
            "protein_name": protein_name,
            "length": data.get("sequence", {}).get("length", 0),
            "organism": data.get("organism", {}).get("scientificName", ""),
            "function": function_text,
            "domains": domains,
            "domain_count": len(domains),
            "pfam_refs": pfam_refs,
            "interpro_refs": interpro_refs,
            "has_transmembrane": any(d["type"] == "Transmembrane" for d in domains),
            "has_signal_peptide": any(d["type"] == "Signal" for d in domains),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        logger.sync_debug(
            "Successfully parsed UniProt data",
            gene_symbol=gene_symbol,
            accession=accession,
            domain_count=len(domains),
        )

        return annotation

    def _parse_domains(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parse domain and feature data from UniProt response.

        Args:
            data: UniProt protein entry data

        Returns:
            List of domain dictionaries
        """
        domains = []
        features = data.get("features", [])

        # Feature types to extract
        domain_types = {
            "Domain": "Domain",
            "Region": "Region",
            "Motif": "Motif",
            "Transmembrane": "Transmembrane",
            "Signal peptide": "Signal",
            "Propeptide": "Propeptide",
            "Chain": "Chain",
        }

        for feature in features:
            feature_type = feature.get("type")
            if feature_type not in domain_types:
                continue

            location = feature.get("location", {})
            start_pos = location.get("start", {}).get("value")
            end_pos = location.get("end", {}).get("value")

            if start_pos is None or end_pos is None:
                continue

            domain = {
                "type": domain_types[feature_type],
                "description": feature.get("description", ""),
                "start": start_pos,
                "end": end_pos,
                "length": end_pos - start_pos + 1,
            }

            # Add evidence if available
            evidences = feature.get("evidences", [])
            if evidences:
                domain["evidence_code"] = evidences[0].get("evidenceCode", "")

            domains.append(domain)

        # Sort by start position
        domains.sort(key=lambda x: x["start"])

        return domains

    def _parse_database_refs(self, data: dict[str, Any], db_name: str) -> list[dict[str, str]]:
        """
        Parse external database references.

        Args:
            data: UniProt protein entry data
            db_name: Database name to extract (Pfam, InterPro, etc.)

        Returns:
            List of database reference dictionaries
        """
        refs = []
        db_references = data.get("uniProtKBCrossReferences", [])

        for ref in db_references:
            if ref.get("database") == db_name:
                ref_data = {
                    "id": ref.get("id"),
                    "database": db_name,
                }

                # Extract properties
                properties = ref.get("properties", [])
                for prop in properties:
                    key = prop.get("key", "").lower().replace(" ", "_")
                    if key:
                        ref_data[key] = prop.get("value")

                refs.append(ref_data)

        return refs

    # ------------------------------------------------------------------
    # ID Mapping API (batch optimization)
    # ------------------------------------------------------------------

    def _parse_id_mapping_results(
        self, response_data: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """Parse ID Mapping results into a gene-symbol-keyed dict.

        Each result has ``{"from": "PKD1", "to": {UniProtKB entry}}``.
        The ``from`` field unambiguously maps back to the queried gene symbol,
        which fixes the PKD1/PRKD1 disambiguation issue present in OR-query
        batch searches.

        Args:
            response_data: JSON response from the ID Mapping results endpoint.

        Returns:
            Mapping of gene symbol → parsed annotation dict.
        """
        parsed: dict[str, dict[str, Any]] = {}

        for item in response_data.get("results", []):
            gene_symbol = item.get("from", "")
            entry = item.get("to", {})

            if not gene_symbol or not entry:
                continue

            annotation = self._parse_protein_data(gene_symbol, entry)
            if annotation:
                parsed[gene_symbol] = annotation

        return parsed

    def _map_parsed_to_gene_ids(
        self,
        parsed: dict[str, dict[str, Any]],
        genes: list[Gene],
    ) -> dict[int, dict[str, Any]]:
        """Map symbol-keyed parsed results to gene-ID-keyed results.

        Args:
            parsed: Symbol → annotation dict from _parse_id_mapping_results.
            genes: Gene objects to map against.

        Returns:
            Mapping of gene.id → annotation dict.
        """
        symbol_to_gene = {g.approved_symbol.upper(): g for g in genes}
        results: dict[int, dict[str, Any]] = {}

        for symbol, annotation in parsed.items():
            gene = symbol_to_gene.get(symbol.upper())
            if gene:
                results[gene.id] = annotation

        return results

    async def _fetch_via_id_mapping(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """Fetch annotations for all genes using the UniProt ID Mapping API.

        Workflow:
          1. POST /idmapping/run  — submit all gene symbols in one job
          2. Poll /idmapping/status/{jobId} until complete
          3. GET /idmapping/uniprotkb/results/{jobId} — fetch results

        Args:
            genes: List of Gene objects.

        Returns:
            Mapping of gene.id → annotation dict.

        Raises:
            Exception: On submission, polling timeout, or fetch errors.
        """
        symbols = [g.approved_symbol for g in genes]

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0), follow_redirects=True
        ) as client:
            # Step 1: Submit ID mapping job
            submit_response = await client.post(
                f"{self.base_url}/idmapping/run",
                data={
                    "from": "Gene_Name",
                    "to": "UniProtKB",
                    "ids": ",".join(symbols),
                    "taxId": "9606",
                },
            )
            submit_response.raise_for_status()
            job_id = submit_response.json()["jobId"]

            logger.sync_info(
                "ID Mapping job submitted",
                job_id=job_id,
                gene_count=len(symbols),
            )

            # Step 2: Poll for completion
            elapsed = 0.0
            while elapsed < _ID_MAPPING_TIMEOUT:
                await asyncio.sleep(_ID_MAPPING_POLL_INTERVAL)
                elapsed += _ID_MAPPING_POLL_INTERVAL

                status_response = await client.get(
                    f"{self.base_url}/idmapping/status/{job_id}",
                )
                status_response.raise_for_status()
                status_data = status_response.json()

                job_status = status_data.get("jobStatus")
                if job_status == "RUNNING":
                    continue

                # Any status other than RUNNING means the job is done
                # (FINISHED, or the status endpoint redirects to results)
                break
            else:
                raise TimeoutError(
                    f"ID Mapping job {job_id} did not complete within "
                    f"{_ID_MAPPING_TIMEOUT}s"
                )

            # Step 3: Fetch results
            results_url = (
                f"{self.base_url}/idmapping/uniprotkb/results/{job_id}"
            )
            results_response = await client.get(
                results_url,
                params={
                    "fields": _UNIPROT_FIELDS,
                    "query": "(reviewed:true)",
                    "format": "json",
                    "size": str(max(len(symbols), 500)),
                },
                headers={"Accept": "application/json"},
            )
            results_response.raise_for_status()
            results_data = results_response.json()

        parsed = self._parse_id_mapping_results(results_data)

        logger.sync_info(
            "ID Mapping results fetched",
            job_id=job_id,
            requested=len(symbols),
            matched=len(parsed),
        )

        return self._map_parsed_to_gene_ids(parsed, genes)

    # ------------------------------------------------------------------
    # Batch fetch (public API)
    # ------------------------------------------------------------------

    async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Fetch annotations for multiple genes.

        Tries the ID Mapping API first (single job for all genes).
        Falls back to OR-query batches on failure.

        Args:
            genes: List of Gene objects

        Returns:
            Dictionary mapping gene IDs to annotation data
        """
        if not genes:
            return {}

        # Try ID Mapping API first
        try:
            return await self._fetch_via_id_mapping(genes)
        except Exception as e:
            logger.sync_warning(
                "ID Mapping failed, falling back to OR-query batches",
                error_detail=str(e),
                gene_count=len(genes),
            )

        # Fallback: OR-query batches
        return await self._fetch_batch_or_query(genes)

    async def _fetch_batch_or_query(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """Fetch annotations using OR-query batches (fallback path).

        Args:
            genes: List of Gene objects.

        Returns:
            Dictionary mapping gene IDs to annotation data.
        """
        results: dict[int, dict[str, Any]] = {}
        semaphore = asyncio.Semaphore(3)

        for i in range(0, len(genes), self.batch_size):
            batch = genes[i : i + self.batch_size]

            async with semaphore:
                batch_results = await self._fetch_batch_chunk(batch)
                results.update(batch_results)

            if i + self.batch_size < len(genes):
                await asyncio.sleep(0.5)

        return results

    @retry_with_backoff(config=RetryConfig(max_retries=5))
    async def _fetch_batch_chunk(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
        """
        Fetch a single batch of genes using OR query.

        Args:
            genes: List of genes (max batch_size)

        Returns:
            Dictionary mapping gene IDs to annotations
        """
        await self.rate_limiter.wait()

        try:
            client = await self.get_http_client()

            # Build OR query for gene symbols
            # Escape special characters to prevent query injection
            gene_clauses = " OR ".join(
                f"(gene_exact:{_escape_uniprot_query(g.approved_symbol)})" for g in genes
            )
            query = f"({gene_clauses}) AND (organism_id:9606) AND (reviewed:true)"

            url = f"{self.base_url}/uniprotkb/search"
            params = {
                "query": query,
                "format": "json",
                "fields": _UNIPROT_FIELDS,
                "size": str(len(genes)),
            }

            response = await client.get(
                url,
                params=params,
                headers={
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                logger.sync_warning(
                    "Batch request failed",
                    status_code=response.status_code,
                    batch_size=len(genes),
                )
                return {}

            data = response.json()
            api_results = data.get("results", [])

            # Map results back to genes by gene symbol
            gene_map = {g.approved_symbol.upper(): g for g in genes}
            results: dict[int, dict[str, Any]] = {}

            for protein_data in api_results:
                # Extract gene name(s) from response
                gene_names = protein_data.get("genes", [])
                for gene_entry in gene_names:
                    gene_name = gene_entry.get("geneName", {}).get("value", "")
                    gene_upper = gene_name.upper()

                    if gene_upper in gene_map:
                        gene = gene_map[gene_upper]
                        annotation = self._parse_protein_data(gene.approved_symbol, protein_data)
                        if annotation:
                            results[gene.id] = annotation
                        break

            logger.sync_info(
                "OR-query batch fetch completed",
                requested=len(genes),
                successful=len(results),
            )

            return results

        except httpx.HTTPStatusError as e:
            logger.sync_error(
                "HTTP error in batch fetch",
                status_code=e.response.status_code,
                batch_size=len(genes),
            )
            raise

        except Exception as e:
            logger.sync_error(
                "Error in batch fetch",
                error_detail=str(e),
                batch_size=len(genes),
            )
            return {}
