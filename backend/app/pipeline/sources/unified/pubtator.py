"""
Unified PubTator data source implementation.

This module replaces the previous implementations (pubtator.py, pubtator_async.py,
pubtator_cache.py, pubtator_cached.py) with a single, async-first implementation.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.config import settings
from app.pipeline.sources.unified.base import UnifiedDataSource

logger = logging.getLogger(__name__)


class PubTatorUnifiedSource(UnifiedDataSource):
    """
    Unified PubTator client with intelligent caching and async processing.

    Features:
    - Async-first design with batch processing
    - Literature mining from PubMed/PubTator
    - Kidney disease-specific search queries
    - Gene mention aggregation from abstracts
    - Rate limiting and pagination support
    """

    @property
    def source_name(self) -> str:
        return "PubTator"

    @property
    def namespace(self) -> str:
        return "pubtator"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | None = None,
        **kwargs,
    ):
        """Initialize PubTator client with literature mining capabilities."""
        super().__init__(cache_service, http_client, db_session, **kwargs)

        # PubTator configuration
        self.base_url = settings.PUBTATOR_API_URL
        self.pubmed_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

        # Search configuration
        self.kidney_query = settings.PUBTATOR_SEARCH_QUERY
        self.max_pages = settings.PUBTATOR_MAX_PAGES
        self.batch_size = settings.PUBTATOR_BATCH_SIZE
        self.rate_limit_delay = settings.PUBTATOR_RATE_LIMIT_DELAY
        self.min_date = settings.PUBTATOR_MIN_DATE

        # Gene annotation types to extract
        self.annotation_types = ["Gene", "GeneID"]

        logger.info(f"PubTatorUnifiedSource initialized with max pages: {self.max_pages}")

    def _get_default_ttl(self) -> int:
        """Get default TTL for PubTator data."""
        return settings.CACHE_TTL_PUBTATOR

    async def fetch_raw_data(self) -> dict[str, Any]:
        """
        Fetch kidney disease-related publications and gene annotations.

        Returns:
            Dictionary with PMIDs and gene annotations
        """
        logger.info("🧬 PUBTATOR SOURCE: fetch_raw_data() METHOD CALLED")
        logger.info(f"🧬 PUBTATOR SOURCE: kidney_query = '{self.kidney_query}'")

        # Search for relevant publications
        logger.info("🧬 PUBTATOR SOURCE: Calling _search_publications()...")
        pmids = await self._search_publications(self.kidney_query)
        logger.info(f"🧬 PUBTATOR SOURCE: Search returned {len(pmids) if pmids else 0} PMIDs")

        if not pmids:
            logger.warning("No publications found for kidney disease query")
            return {}

        logger.info(f"Found {len(pmids)} relevant publications")

        # Fetch annotations for PMIDs in batches
        all_annotations = {}
        for i in range(0, len(pmids), self.batch_size):
            batch = pmids[i : i + self.batch_size]
            annotations = await self._fetch_annotations_batch(batch)
            all_annotations.update(annotations)

            # Rate limiting
            if i + self.batch_size < len(pmids):
                await asyncio.sleep(self.rate_limit_delay)

        return {
            "pmids": pmids,
            "annotations": all_annotations,
            "query": self.kidney_query,
            "fetch_date": datetime.now(timezone.utc).isoformat(),
        }

    async def _search_publications(self, query: str) -> list[str]:
        """
        Search PubMed for relevant publications.

        Args:
            query: Search query

        Returns:
            List of PMIDs
        """

        async def _fetch_pmids():
            """Internal function to fetch PMIDs."""
            url = f"{self.pubmed_url}/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": f"{query} AND genetics[MeSH]",
                "retmax": self.max_pages * 10,  # Approximate articles per page
                "retmode": "json",
                "sort": "relevance",
                "mindate": self.min_date,
            }

            logger.info(f"PubMed search URL: {url}")
            logger.info(f"PubMed search params: {params}")

            response = await self.http_client.get(url, params=params, timeout=30)

            logger.info(f"PubMed response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                count = data.get("esearchresult", {}).get("count", "0")
                idlist = data.get("esearchresult", {}).get("idlist", [])
                logger.info(f"PubMed found {count} total results, returning {len(idlist)} PMIDs")
                return idlist

            logger.error(f"Failed to search PubMed: HTTP {response.status_code}")
            logger.error(f"Response content: {response.text[:500]}")
            return []

        # Use unified caching
        cache_key = f"search:{query}:{self.max_pages}"
        pmids = await self.fetch_with_cache(
            cache_key=cache_key, fetch_func=_fetch_pmids, ttl=self.cache_ttl
        )

        return pmids or []

    async def _fetch_annotations_batch(self, pmids: list[str]) -> dict[str, Any]:
        """
        Fetch PubTator annotations for a batch of PMIDs.

        Args:
            pmids: List of PMIDs

        Returns:
            Dictionary of annotations by PMID
        """
        if not pmids:
            return {}

        async def _fetch_batch():
            """Internal function to fetch annotations."""
            pmid_str = ",".join(pmids)
            url = f"{self.base_url}/publications/export/biocjson"
            params = {"pmids": pmid_str}

            try:
                response = await self.http_client.get(url, params=params, timeout=60)

                if response.status_code == 200:
                    return self._parse_biocjson(response.json())
                else:
                    logger.error(f"Failed to fetch annotations: HTTP {response.status_code}")
                    return {}

            except Exception as e:
                logger.error(f"Error fetching annotations for batch: {e}")
                return {}

        # Cache each batch
        cache_key = f"annotations:{','.join(sorted(pmids[:5]))}"  # Use first 5 PMIDs as key
        annotations = await self.fetch_with_cache(
            cache_key=cache_key, fetch_func=_fetch_batch, ttl=self.cache_ttl
        )

        return annotations or {}

    def _parse_biocjson(self, bioc_data: Any) -> dict[str, Any]:
        """
        Parse BioC JSON format from PubTator.

        Args:
            bioc_data: BioC JSON data

        Returns:
            Parsed annotations by PMID
        """
        annotations = {}

        if not isinstance(bioc_data, list):
            bioc_data = [bioc_data]

        for _i, doc in enumerate(bioc_data):
            if not isinstance(doc, dict):
                continue

            # Check if this is the new PubTator3 format
            if "PubTator3" in doc:
                pubtator3_data = doc["PubTator3"]

                # If PubTator3 contains a list of documents, process them
                if isinstance(pubtator3_data, list):
                    # Recursively process the PubTator3 documents
                    return self._parse_biocjson(pubtator3_data)

            pmid = doc.get("id", "")
            if not pmid:
                continue

            doc_annotations = {
                "pmid": pmid,
                "genes": [],
                "title": "",
                "abstract": "",
            }

            # Extract title and abstract
            for passage in doc.get("passages", []):
                if passage.get("infons", {}).get("type") == "title":
                    doc_annotations["title"] = passage.get("text", "")
                elif passage.get("infons", {}).get("type") == "abstract":
                    doc_annotations["abstract"] = passage.get("text", "")

                # Extract gene annotations
                for annotation in passage.get("annotations", []):
                    if annotation.get("infons", {}).get("type") in self.annotation_types:
                        gene_info = {
                            "text": annotation.get("text", ""),
                            "identifier": annotation.get("infons", {}).get("identifier", ""),
                            "type": annotation.get("infons", {}).get("type", ""),
                            "locations": annotation.get("locations", []),
                        }
                        doc_annotations["genes"].append(gene_info)

            if doc_annotations["genes"]:
                annotations[pmid] = doc_annotations
        return annotations

    async def process_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process PubTator annotations into structured gene information.

        Args:
            raw_data: Raw data with PMIDs and annotations

        Returns:
            Dictionary mapping gene symbols to aggregated data
        """
        if not raw_data or "annotations" not in raw_data:
            return {}

        gene_data_map = {}
        total_pmids = len(raw_data.get("pmids", []))
        total_annotations = 0

        logger.info(f"🔄 Processing annotations from {total_pmids} publications...")

        for pmid, doc_data in raw_data["annotations"].items():
            for gene_annotation in doc_data.get("genes", []):
                total_annotations += 1

                # Extract gene symbol (handle various formats)
                gene_text = gene_annotation.get("text", "")
                gene_id = gene_annotation.get("identifier", "")

                # Clean up gene symbol
                gene_symbol = self._normalize_gene_symbol(gene_text)
                if not gene_symbol:
                    continue

                # Initialize gene entry if new
                if gene_symbol not in gene_data_map:
                    gene_data_map[gene_symbol] = {
                        "pmids": set(),
                        "mentions": [],
                        "identifiers": set(),
                        "publication_count": 0,
                        "total_mentions": 0,
                    }

                # Add publication and mention
                gene_data_map[gene_symbol]["pmids"].add(pmid)
                gene_data_map[gene_symbol]["mentions"].append(
                    {
                        "pmid": pmid,
                        "text": gene_text,
                        "context": doc_data.get("title", "")[:200],
                    }
                )

                if gene_id:
                    gene_data_map[gene_symbol]["identifiers"].add(gene_id)

        # Convert sets to lists and calculate stats
        for _symbol, data in gene_data_map.items():
            data["pmids"] = list(data["pmids"])
            data["identifiers"] = list(data["identifiers"])
            data["publication_count"] = len(data["pmids"])
            data["total_mentions"] = len(data["mentions"])

            # Limit mentions to most recent
            data["mentions"] = data["mentions"][:10]

            # Add metadata
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            data["search_query"] = raw_data.get("query", "")

        logger.info(
            f"🎯 PubTator processing complete: "
            f"{total_pmids} publications, {total_annotations} annotations, "
            f"{len(gene_data_map)} unique genes"
        )

        return gene_data_map

    def _normalize_gene_symbol(self, text: str) -> str | None:
        """
        Normalize gene symbol from PubTator text.

        Args:
            text: Raw gene text from annotation

        Returns:
            Normalized gene symbol or None
        """
        if not text:
            return None

        # Remove special characters and normalize
        symbol = text.strip().upper()

        # Remove common suffixes/prefixes
        for suffix in [" GENE", " PROTEIN", " MRNA"]:
            if symbol.endswith(suffix):
                symbol = symbol[: -len(suffix)]

        # Basic validation
        if len(symbol) < 2 or len(symbol) > 15:
            return None

        # Must contain at least one letter
        if not any(c.isalpha() for c in symbol):
            return None

        return symbol

    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        """
        Check if a gene record is kidney-related.

        Always returns True as we pre-filter with kidney query.
        """
        return True

    def _get_source_detail(self, evidence_data: dict[str, Any]) -> str:
        """
        Generate source detail string for evidence.

        Args:
            evidence_data: Evidence data

        Returns:
            Source detail string
        """
        pub_count = evidence_data.get("publication_count", 0)
        mention_count = evidence_data.get("total_mentions", 0)

        return f"PubTator: {pub_count} publications, {mention_count} mentions"
