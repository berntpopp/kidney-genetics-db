"""
Unified PanelApp data source implementation.

This module replaces the previous implementations (panelapp.py, panelapp_cached.py)
with a single, async-first implementation using the unified data source architecture.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.core.config import settings
from app.pipeline.sources.unified.base import UnifiedDataSource

logger = logging.getLogger(__name__)


class PanelAppUnifiedSource(UnifiedDataSource):
    """
    Unified PanelApp client with intelligent caching and async processing.
    
    Features:
    - Multi-region support (UK and Australia)
    - Async-first design with batch processing
    - Persistent caching with automatic refresh
    - Kidney-specific panel filtering
    - High-confidence gene filtering (green list)
    """

    @property
    def source_name(self) -> str:
        return "PanelApp"

    @property
    def namespace(self) -> str:
        return "panelapp"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | None = None,
        regions: list[str] | None = None,
        **kwargs
    ):
        """Initialize PanelApp client with multi-region support."""
        super().__init__(cache_service, http_client, db_session, **kwargs)

        # PanelApp endpoints
        self.uk_base_url = settings.PANELAPP_UK_URL
        self.au_base_url = settings.PANELAPP_AU_URL

        # Regions to fetch from
        self.regions = regions or ["UK", "Australia"]

        # Kidney-related search terms
        self.kidney_keywords = [
            "kidney", "renal", "nephro", "glomerul",
            "tubul", "polycystic", "alport", "nephritis",
            "cystic", "ciliopathy", "complement", "cakut",
            "focal segmental", "steroid resistant", "nephrotic",
            "proteinuria", "hematuria"
        ]

        # Confidence levels (green list)
        self.green_confidence_levels = ["3", "4", "green"]

        logger.info(f"PanelAppUnifiedSource initialized for regions: {self.regions}")

    def _get_default_ttl(self) -> int:
        """Get default TTL for PanelApp data."""
        return settings.CACHE_TTL_PANELAPP

    async def fetch_raw_data(self) -> dict[str, Any]:
        """
        Fetch all kidney-related panels from configured regions.
        
        Returns:
            Dictionary with panels from each region
        """
        all_data = {}

        for region in self.regions:
            logger.info(f"📥 Fetching PanelApp data from {region}...")

            if region == "UK":
                base_url = self.uk_base_url
            elif region == "Australia":
                base_url = self.au_base_url
            else:
                logger.warning(f"Unknown region: {region}")
                continue

            # Fetch panels for this region
            panels = await self._fetch_region_panels(base_url, region)
            all_data[region] = panels

            logger.info(f"✅ Fetched {len(panels)} panels from {region}")

        return all_data

    async def _fetch_region_panels(self, base_url: str, region: str) -> list[dict]:
        """
        Fetch all kidney-related panels from a specific region.
        
        Args:
            base_url: API base URL for the region
            region: Region name for caching
            
        Returns:
            List of panel data with genes
        """
        async def _fetch_panels():
            """Internal function to fetch panels."""
            all_panels = []

            # Search for panels with each keyword
            for keyword in self.kidney_keywords:
                try:
                    url = f"{base_url}/panels/"
                    params = {"name": keyword, "format": "json"}

                    response = await self.http_client.get(url, params=params, timeout=30)

                    if response.status_code == 200:
                        data = response.json()

                        if "results" in data:
                            for panel in data["results"]:
                                if self._is_kidney_related_panel(panel):
                                    all_panels.append(panel)

                except Exception as e:
                    logger.error(f"Error searching panels for '{keyword}': {e}")

            # Deduplicate panels by ID
            seen_ids = set()
            unique_panels = []

            for panel in all_panels:
                panel_id = panel.get("id")
                if panel_id and panel_id not in seen_ids:
                    seen_ids.add(panel_id)

                    # Fetch detailed panel data with genes
                    detailed_panel = await self._fetch_panel_details(
                        base_url, panel_id, panel.get("name", "")
                    )
                    if detailed_panel:
                        unique_panels.append(detailed_panel)

            return unique_panels

        # Use unified caching
        cache_key = f"panels:{region}"
        panels = await self.fetch_with_cache(
            cache_key=cache_key,
            fetch_func=_fetch_panels,
            ttl=self.cache_ttl
        )

        return panels or []

    async def _fetch_panel_details(
        self, base_url: str, panel_id: str, panel_name: str
    ) -> dict | None:
        """
        Fetch detailed panel information including genes.
        
        Args:
            base_url: API base URL
            panel_id: Panel identifier
            panel_name: Panel name for logging
            
        Returns:
            Panel data with genes or None
        """
        try:
            url = f"{base_url}/panels/{panel_id}/"
            params = {"format": "json"}

            response = await self.http_client.get(url, params=params, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch panel {panel_id}: HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"Error fetching panel {panel_id} ({panel_name}): {e}")

        return None

    async def process_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process panel data into structured gene information.
        
        Args:
            raw_data: Dictionary with panels from each region
            
        Returns:
            Dictionary mapping gene symbols to aggregated data
        """
        gene_data_map = {}
        total_panels = 0
        total_genes = 0

        for region, panels in raw_data.items():
            logger.info(f"🔄 Processing {len(panels)} panels from {region}...")

            for panel in panels:
                total_panels += 1
                panel_info = {
                    "id": panel.get("id"),
                    "name": panel.get("name"),
                    "version": panel.get("version"),
                    "region": region,
                }

                # Process genes in panel
                if "genes" in panel:
                    for gene in panel["genes"]:
                        # Only include high-confidence genes
                        confidence = str(gene.get("confidence_level", ""))
                        if confidence not in self.green_confidence_levels:
                            continue

                        gene_data = gene.get("gene_data", {})
                        symbol = gene_data.get("gene_symbol")

                        if not symbol:
                            continue

                        total_genes += 1

                        # Initialize gene entry if new
                        if symbol not in gene_data_map:
                            gene_data_map[symbol] = {
                                "hgnc_id": gene_data.get("hgnc_id"),
                                "panels": [],
                                "regions": set(),
                                "phenotypes": set(),
                                "modes_of_inheritance": set(),
                                "evidence_levels": set(),
                            }

                        # Add panel information
                        gene_data_map[symbol]["panels"].append(panel_info)
                        gene_data_map[symbol]["regions"].add(region)
                        gene_data_map[symbol]["evidence_levels"].add(confidence)

                        # Add phenotypes
                        phenotypes = gene.get("phenotypes") or []
                        for phenotype in phenotypes:
                            if phenotype:
                                gene_data_map[symbol]["phenotypes"].add(phenotype)

                        # Add mode of inheritance
                        moi = gene.get("mode_of_inheritance")
                        if moi:
                            gene_data_map[symbol]["modes_of_inheritance"].add(moi)

        # Convert sets to lists for JSON serialization
        for symbol, data in gene_data_map.items():
            data["regions"] = list(data["regions"])
            data["phenotypes"] = list(data["phenotypes"])
            data["modes_of_inheritance"] = list(data["modes_of_inheritance"])
            data["evidence_levels"] = list(data["evidence_levels"])
            data["panel_count"] = len(data["panels"])
            data["last_updated"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"🎯 PanelApp processing complete: "
            f"{total_panels} panels, {total_genes} gene entries, "
            f"{len(gene_data_map)} unique genes"
        )

        return gene_data_map

    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        """
        Check if a gene record is kidney-related.
        
        Always returns True as we pre-filter panels.
        """
        return True

    def _is_kidney_related_panel(self, panel: dict) -> bool:
        """
        Check if a panel is kidney-related based on name and description.
        
        Args:
            panel: Panel data
            
        Returns:
            True if panel is kidney-related
        """
        name = (panel.get("name") or "").lower()
        description = (panel.get("description") or "").lower()

        # Check for kidney keywords
        for keyword in ["kidney", "renal", "nephro", "cakut"]:
            if keyword in name or keyword in description:
                return True

        # Check for specific kidney-related panels
        kidney_panel_patterns = [
            r"focal\s+segmental",
            r"steroid\s+resistant",
            r"nephrotic",
            r"glomerul",
            r"tubul",
            r"alport",
            r"polycystic",
            r"ciliopathy",
        ]

        combined_text = f"{name} {description}"
        for pattern in kidney_panel_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True

        return False

    def _get_source_detail(self, evidence_data: dict[str, Any]) -> str:
        """
        Generate source detail string for evidence.
        
        Args:
            evidence_data: Evidence data
            
        Returns:
            Source detail string
        """
        panel_count = evidence_data.get("panel_count", 0)
        regions = evidence_data.get("regions", [])

        if regions:
            region_str = ", ".join(regions)
            return f"PanelApp ({region_str}): {panel_count} panels"

        return f"PanelApp: {panel_count} panels"
