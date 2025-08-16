"""
PanelApp data source integration

Fetches kidney-related gene panels from PanelApp UK and Australia
"""

import logging
from datetime import date, datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.gene import gene_crud
from app.models.gene import GeneEvidence
from app.schemas.gene import GeneCreate

logger = logging.getLogger(__name__)


class PanelAppClient:
    """Client for PanelApp API integration"""

    def __init__(self, base_url: str, source_name: str):
        """Initialize PanelApp client

        Args:
            base_url: Base URL for PanelApp API
            source_name: Name identifier for this source (e.g., "PanelApp_UK")
        """
        self.base_url = base_url
        self.source_name = source_name
        self.client = httpx.Client(timeout=30.0)

    def search_panels(self, keywords: list[str]) -> list[dict[str, Any]]:
        """Search for panels matching kidney-related keywords

        Args:
            keywords: List of search terms

        Returns:
            List of panel data
        """
        panels = []
        for keyword in keywords:
            try:
                response = self.client.get(
                    f"{self.base_url}/panels/",
                    params={"name": keyword, "format": "json"},
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

    def get_panel_genes(self, panel_id: str | int) -> list[dict[str, Any]]:
        """Get genes from a specific panel

        Args:
            panel_id: Panel identifier

        Returns:
            List of gene data from panel
        """
        try:
            response = self.client.get(
                f"{self.base_url}/panels/{panel_id}/",
                params={"format": "json"},
            )
            response.raise_for_status()
            data = response.json()

            genes = []
            if "genes" in data:
                for gene in data["genes"]:
                    # Only include high-confidence genes (green list)
                    if gene.get("confidence_level") in ["3", "4"]:
                        genes.append(
                            {
                                "symbol": gene.get("gene_data", {}).get("gene_symbol"),
                                "hgnc_id": gene.get("gene_data", {}).get("hgnc_id"),
                                "panel_id": panel_id,
                                "panel_name": data.get("name"),
                                "panel_version": data.get("version"),
                                "confidence_level": gene.get("confidence_level"),
                                "mode_of_inheritance": gene.get("mode_of_inheritance"),
                                "phenotypes": gene.get("phenotypes", []),
                                "evidence": gene.get("evidence", []),
                            }
                        )
            return genes
        except Exception as e:
            logger.error(f"Error fetching genes for panel {panel_id}: {e}")
            return []

    def _is_kidney_related(self, panel: dict[str, Any]) -> bool:
        """Check if panel is kidney-related using regex filter from kidney-genetics-v1

        Args:
            panel: Panel data

        Returns:
            True if panel is kidney-related
        """
        import re

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

    def close(self):
        """Close HTTP client"""
        self.client.close()


def update_panelapp_data(db: Session) -> dict[str, Any]:
    """Update database with PanelApp data from both UK and Australia

    Args:
        db: Database session

    Returns:
        Statistics about the update
    """
    # Will fetch from both UK and Australia sources
    source_name = "PanelApp"  # Combined source name

    stats = {
        "source": source_name,
        "panels_found_uk": 0,
        "panels_found_au": 0,
        "genes_processed": 0,
        "genes_created": 0,
        "evidence_created": 0,
        "errors": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    all_panels = []

    try:
        # Search UK PanelApp
        uk_client = PanelAppClient(settings.PANELAPP_UK_URL, "UK")
        logger.info("Searching for kidney panels in PanelApp UK")
        uk_panels = uk_client.search_panels(settings.KIDNEY_FILTER_TERMS)
        stats["panels_found_uk"] = len(uk_panels)
        logger.info(f"Found {len(uk_panels)} kidney-related panels in UK")

        for panel in uk_panels:
            panel["source"] = "UK"
            all_panels.append(panel)

        # Try Australian PanelApp (may be down)
        try:
            au_client = PanelAppClient(settings.PANELAPP_AU_URL, "AU")
            logger.info("Searching for kidney panels in PanelApp Australia")
            au_panels = au_client.search_panels(settings.KIDNEY_FILTER_TERMS)
            stats["panels_found_au"] = len(au_panels)
            logger.info(f"Found {len(au_panels)} kidney-related panels in Australia")

            for panel in au_panels:
                panel["source"] = "AU"
                all_panels.append(panel)
        except Exception as e:
            logger.warning(f"PanelApp Australia unavailable: {e}")
            stats["panels_found_au"] = 0

        # Process each panel
        gene_data_map = {}  # symbol -> gene data
        for panel in all_panels:
            panel_id = panel["id"]
            panel_name = panel["name"]
            panel_source = panel.get("source", "UK")
            logger.info(f"Processing panel: {panel_name} (ID: {panel_id}, Source: {panel_source})")

            # Get genes from panel using appropriate client
            client = uk_client if panel_source == "UK" else au_client
            genes = client.get_panel_genes(panel_id)
            for gene_info in genes:
                symbol = gene_info["symbol"]
                if not symbol:
                    continue

                # Aggregate gene data across panels
                if symbol not in gene_data_map:
                    gene_data_map[symbol] = {
                        "hgnc_id": gene_info["hgnc_id"],
                        "panels": [],
                        "phenotypes": set(),
                        "evidence": [],
                        "modes_of_inheritance": set(),
                    }

                gene_data_map[symbol]["panels"].append(
                    {
                        "id": panel_id,
                        "name": panel_name,
                        "version": gene_info["panel_version"],
                        "confidence": gene_info["confidence_level"],
                        "source": panel_source,
                    }
                )

                # Aggregate phenotypes
                for pheno in gene_info.get("phenotypes", []):
                    gene_data_map[symbol]["phenotypes"].add(pheno)

                # Aggregate modes of inheritance
                if gene_info.get("mode_of_inheritance"):
                    gene_data_map[symbol]["modes_of_inheritance"].add(
                        gene_info["mode_of_inheritance"]
                    )

                # Aggregate evidence
                gene_data_map[symbol]["evidence"].extend(gene_info.get("evidence", []))

        # Store in database
        for symbol, data in gene_data_map.items():
            stats["genes_processed"] += 1

            # Get or create gene
            gene = gene_crud.get_by_symbol(db, symbol)
            if not gene:
                # Create new gene
                try:
                    gene_create = GeneCreate(
                        approved_symbol=symbol,
                        hgnc_id=data["hgnc_id"],
                        aliases=[],
                    )
                    gene = gene_crud.create(db, gene_create)
                    stats["genes_created"] += 1
                    logger.info(f"Created new gene: {symbol}")
                except Exception as e:
                    logger.error(f"Error creating gene {symbol}: {e}")
                    stats["errors"] += 1
                    continue

            # Create or update evidence
            try:
                # Check if evidence already exists
                existing = (
                    db.query(GeneEvidence)
                    .filter(
                        GeneEvidence.gene_id == gene.id,  # type: ignore[arg-type]
                        GeneEvidence.source_name == source_name,
                    )
                    .first()
                )

                evidence_data = {
                    "panels": data["panels"],
                    "phenotypes": list(data["phenotypes"]),
                    "modes_of_inheritance": list(data["modes_of_inheritance"]),
                    "evidence": data["evidence"],
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }

                if existing:
                    # Update existing evidence
                    existing.evidence_data = evidence_data
                    existing.evidence_date = date.today()
                    db.add(existing)
                else:
                    # Create new evidence
                    evidence = GeneEvidence(
                        gene_id=gene.id,  # type: ignore[arg-type]
                        source_name=source_name,
                        source_detail=f"{len(data['panels'])} panels",
                        evidence_data=evidence_data,
                        evidence_date=date.today(),
                    )
                    db.add(evidence)
                    stats["evidence_created"] += 1

                db.commit()
                logger.debug(f"Saved evidence for gene: {symbol}")

            except Exception as e:
                logger.error(f"Error saving evidence for gene {symbol}: {e}")
                db.rollback()
                stats["errors"] += 1

    finally:
        uk_client.close()
        if 'au_client' in locals():
            au_client.close()

    stats["completed_at"] = datetime.now(timezone.utc).isoformat()
    stats["duration"] = (
        datetime.fromisoformat(stats["completed_at"]) - datetime.fromisoformat(stats["started_at"])
    ).total_seconds()

    logger.info(
        f"PanelApp update complete: UK={stats['panels_found_uk']} panels, "
        f"AU={stats['panels_found_au']} panels, {stats['genes_processed']} genes, "
        f"{stats['genes_created']} created, {stats['evidence_created']} evidence records"
    )

    return stats


def update_all_panelapp(db: Session) -> dict[str, Any]:
    """Update data from all PanelApp sources (UK and Australia combined)

    Args:
        db: Database session

    Returns:
        Statistics for the combined update
    """
    logger.info("Updating PanelApp data (UK and Australia combined)")
    stats = update_panelapp_data(db)
    return stats
