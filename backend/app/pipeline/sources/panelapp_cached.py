"""
PanelApp data source integration with unified cache system.

Fetches kidney-related gene panels from PanelApp UK and Australia
using enhanced caching infrastructure for improved performance.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.cache_service import CacheService, cached, get_cache_service
from app.core.cached_http_client import CachedHttpClient, get_cached_http_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class PanelAppClientCached:
    """
    Enhanced PanelApp client with unified cache system integration.
    
    Features:
    - Persistent API response caching
    - HTTP caching via Hishel for API compliance
    - Intelligent retry and fallback logic
    - Circuit breaker pattern for resilience
    - Multi-source support (UK and Australia)
    """

    NAMESPACE = "panelapp"

    def __init__(
        self,
        base_url: str,
        source_name: str,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | AsyncSession | None = None,
    ):
        """Initialize the enhanced PanelApp client."""
        self.base_url = base_url
        self.source_name = source_name
        self.cache_service = cache_service or get_cache_service(db_session)
        self.http_client = http_client or get_cached_http_client(cache_service, db_session)

        # Get TTL for PanelApp namespace
        self.ttl = settings.CACHE_TTL_PANELAPP

        logger.info(f"PanelAppClientCached ({source_name}) initialized with TTL: {self.ttl}s")

    async def search_panels(self, keywords: list[str]) -> list[dict[str, Any]]:
        """
        Search for panels matching kidney-related keywords with caching.
        
        Args:
            keywords: List of search terms
        
        Returns:
            List of panel data
        """
        cache_key = f"search_panels:{self.source_name}:{'-'.join(sorted(keywords))}"

        async def fetch_panels():
            panels = []
            for keyword in keywords:
                try:
                    url = f"{self.base_url}/panels/"
                    params = {"name": keyword, "format": "json"}

                    response = await self.http_client.get(
                        url,
                        params=params,
                        namespace=self.NAMESPACE,
                        fallback_ttl=self.ttl
                    )

                    response.raise_for_status()
                    data = response.json()

                    # Extract results
                    if "results" in data:
                        for panel in data["results"]:
                            # Only include relevant panels
                            if self._is_kidney_related(panel):
                                panels.append(panel)

                except Exception as e:
                    logger.error(f"Error searching panels for keyword '{keyword}': {e}")

            # Deduplicate by panel ID
            seen = set()
            unique_panels = []
            for panel in panels:
                if panel["id"] not in seen:
                    seen.add(panel["id"])
                    unique_panels.append(panel)

            return unique_panels

        return await cached(
            cache_key,
            fetch_panels,
            self.NAMESPACE,
            self.ttl,
            self.cache_service.db_session
        )

    async def get_panel_genes(self, panel_id: str | int) -> list[dict[str, Any]]:
        """
        Get genes from a specific panel with caching.
        
        Args:
            panel_id: Panel identifier
        
        Returns:
            List of gene data from panel
        """
        cache_key = f"panel_genes:{self.source_name}:{panel_id}"

        async def fetch_panel_genes():
            try:
                url = f"{self.base_url}/panels/{panel_id}/"
                params = {"format": "json"}

                response = await self.http_client.get(
                    url,
                    params=params,
                    namespace=self.NAMESPACE,
                    fallback_ttl=self.ttl
                )

                response.raise_for_status()
                data = response.json()

                genes = []
                if "genes" in data:
                    for gene in data["genes"]:
                        # Only include high-confidence genes (green list)
                        if gene.get("confidence_level") in ["3", "4"]:
                            genes.append({
                                "symbol": gene.get("gene_data", {}).get("gene_symbol"),
                                "hgnc_id": gene.get("gene_data", {}).get("hgnc_id"),
                                "panel_id": panel_id,
                                "panel_name": data.get("name"),
                                "panel_version": data.get("version"),
                                "confidence_level": gene.get("confidence_level"),
                                "mode_of_inheritance": gene.get("mode_of_inheritance"),
                                "phenotypes": gene.get("phenotypes", []),
                                "evidence": gene.get("evidence", []),
                            })
                return genes

            except Exception as e:
                logger.error(f"Error fetching genes for panel {panel_id}: {e}")
                return []

        return await cached(
            cache_key,
            fetch_panel_genes,
            self.NAMESPACE,
            self.ttl,
            self.cache_service.db_session
        )

    def _is_kidney_related(self, panel: dict[str, Any]) -> bool:
        """Check if panel is kidney-related using regex filter"""
        # Use regex filter from kidney-genetics-v1 config
        # Pattern: ((?=.*[Kk]idney)|(?=.*[Rr]enal)|(?=.*[Nn]ephro))(^((?!adrenal).)*$)
        # This matches panels with kidney/renal/nephro but excludes "adrenal"
        pattern = r'((?=.*[Kk]idney)|(?=.*[Rr]enal)|(?=.*[Nn]ephro))(^((?!adrenal).)*$)'

        # Check panel name
        name = panel.get("name", "")
        if re.match(pattern, name):
            return True

        # Also check relevant disorders
        relevant_conditions = panel.get("relevant_disorders", [])
        for condition in relevant_conditions:
            if re.match(pattern, condition):
                return True

        return False

    async def get_all_kidney_panels_and_genes(self) -> dict[str, Any]:
        """
        Get all kidney-related panels and their genes with comprehensive caching.
        
        Returns:
            Dictionary with panels and aggregated gene data
        """
        cache_key = f"all_kidney_data:{self.source_name}"

        async def fetch_all_data():
            # Search for kidney panels
            panels = await self.search_panels(settings.KIDNEY_FILTER_TERMS)

            # Get genes for each panel
            all_genes = []
            for panel in panels:
                panel_genes = await self.get_panel_genes(panel["id"])
                for gene in panel_genes:
                    gene["source"] = self.source_name
                    all_genes.append(gene)

            return {
                "panels": panels,
                "genes": all_genes,
                "panel_count": len(panels),
                "gene_count": len(all_genes),
                "source": self.source_name
            }

        return await cached(
            cache_key,
            fetch_all_data,
            self.NAMESPACE,
            self.ttl,
            self.cache_service.db_session
        )


class PanelAppManagerCached:
    """
    Manager for both UK and Australia PanelApp sources with unified caching.
    """

    NAMESPACE = "panelapp"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | AsyncSession | None = None,
    ):
        """Initialize the PanelApp manager."""
        self.cache_service = cache_service or get_cache_service(db_session)
        self.http_client = http_client or get_cached_http_client(cache_service, db_session)

        # Initialize clients for both sources
        self.uk_client = PanelAppClientCached(
            settings.PANELAPP_UK_URL, "UK", cache_service, http_client, db_session
        )
        self.au_client = PanelAppClientCached(
            settings.PANELAPP_AU_URL, "AU", cache_service, http_client, db_session
        )

        # Get TTL for PanelApp namespace
        self.ttl = settings.CACHE_TTL_PANELAPP

        logger.info(f"PanelAppManagerCached initialized with TTL: {self.ttl}s")

    async def get_all_data(self) -> dict[str, Any]:
        """
        Get data from both UK and Australia PanelApp sources.
        
        Returns:
            Combined statistics and data from both sources
        """
        cache_key = "combined_panelapp_data"

        async def fetch_combined_data():
            stats = {
                "source": "PanelApp",
                "panels_found_uk": 0,
                "panels_found_au": 0,
                "genes_processed": 0,
                "errors": 0,
                "started_at": datetime.now(timezone.utc).isoformat(),
            }

            all_panels = []
            all_genes = []

            try:
                # Get UK data
                logger.info("Fetching kidney panels from PanelApp UK")
                uk_data = await self.uk_client.get_all_kidney_panels_and_genes()
                stats["panels_found_uk"] = uk_data["panel_count"]

                for panel in uk_data["panels"]:
                    panel["source"] = "UK"
                    all_panels.append(panel)

                for gene in uk_data["genes"]:
                    gene["source"] = "UK"
                    all_genes.append(gene)

                logger.info(f"Found {len(uk_data['panels'])} kidney-related panels in UK")

            except Exception as e:
                logger.error(f"Error fetching UK PanelApp data: {e}")
                stats["errors"] += 1

            try:
                # Get Australia data (may be down)
                logger.info("Fetching kidney panels from PanelApp Australia")
                au_data = await self.au_client.get_all_kidney_panels_and_genes()
                stats["panels_found_au"] = au_data["panel_count"]

                for panel in au_data["panels"]:
                    panel["source"] = "AU"
                    all_panels.append(panel)

                for gene in au_data["genes"]:
                    gene["source"] = "AU"
                    all_genes.append(gene)

                logger.info(f"Found {len(au_data['panels'])} kidney-related panels in Australia")

            except Exception as e:
                logger.warning(f"PanelApp Australia unavailable: {e}")
                stats["panels_found_au"] = 0

            # Deduplicate genes by symbol
            unique_genes = {}
            for gene in all_genes:
                symbol = gene.get("symbol")
                if symbol and symbol not in unique_genes:
                    unique_genes[symbol] = gene
                elif symbol:
                    # Merge data from multiple sources
                    existing = unique_genes[symbol]
                    if gene.get("source") != existing.get("source"):
                        existing["sources"] = existing.get("sources", [existing.get("source", "")])
                        if gene.get("source") not in existing["sources"]:
                            existing["sources"].append(gene.get("source"))

            stats["genes_processed"] = len(unique_genes)
            stats["completed_at"] = datetime.now(timezone.utc).isoformat()

            return {
                "stats": stats,
                "panels": all_panels,
                "genes": list(unique_genes.values()),
                "unique_gene_count": len(unique_genes)
            }

        return await cached(
            cache_key,
            fetch_combined_data,
            self.NAMESPACE,
            self.ttl,
            self.cache_service.db_session
        )

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for the PanelApp namespace."""
        return await self.cache_service.get_stats(self.NAMESPACE)

    async def clear_cache(self) -> int:
        """Clear all PanelApp cache entries."""
        return await self.cache_service.clear_namespace(self.NAMESPACE)

    async def warm_cache(self) -> int:
        """
        Warm the cache by preloading PanelApp data.
        
        Returns:
            Number of entries cached
        """
        logger.info("Warming PanelApp cache...")

        try:
            # Warm up both UK and AU data
            await self.get_all_data()

            logger.info("PanelApp cache warming completed")
            return 1  # Main data cache entry

        except Exception as e:
            logger.error(f"Error warming PanelApp cache: {e}")
            return 0


# Global cached manager instance
_panelapp_manager_cached: PanelAppManagerCached | None = None


def get_panelapp_manager_cached(
    cache_service: CacheService | None = None,
    db_session: Session | AsyncSession | None = None
) -> PanelAppManagerCached:
    """Get or create the global cached PanelApp manager instance."""
    global _panelapp_manager_cached

    if _panelapp_manager_cached is None:
        _panelapp_manager_cached = PanelAppManagerCached(
            cache_service=cache_service,
            db_session=db_session
        )

    return _panelapp_manager_cached


# Convenience functions for backward compatibility

async def get_panelapp_data_cached(
    db_session: Session | AsyncSession | None = None
) -> dict[str, Any]:
    """
    Convenience function to get PanelApp data using the cached manager.
    
    Args:
        db_session: Database session for cache persistence
    
    Returns:
        Combined PanelApp data from UK and Australia
    """
    manager = get_panelapp_manager_cached(db_session=db_session)
    return await manager.get_all_data()
