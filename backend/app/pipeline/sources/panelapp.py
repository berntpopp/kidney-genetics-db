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
        """Check if panel is kidney-related

        Args:
            panel: Panel data

        Returns:
            True if panel is kidney-related
        """
        name = panel.get("name", "").lower()
        relevant_conditions = panel.get("relevant_disorders", [])

        # Check name
        for term in settings.KIDNEY_FILTER_TERMS:
            if term.lower() in name:
                return True

        # Check relevant disorders
        for condition in relevant_conditions:
            for term in settings.KIDNEY_FILTER_TERMS:
                if term.lower() in condition.lower():
                    return True

        return False

    def close(self):
        """Close HTTP client"""
        self.client.close()


def update_panelapp_data(db: Session, source: str = "uk") -> dict[str, Any]:
    """Update database with PanelApp data

    Args:
        db: Database session
        source: Which PanelApp instance to use ("uk" or "au")

    Returns:
        Statistics about the update
    """
    # Select API endpoint
    if source == "uk":
        base_url = settings.PANELAPP_UK_URL
        source_name = "PanelApp_UK"
    else:
        base_url = settings.PANELAPP_AU_URL
        source_name = "PanelApp_AU"

    client = PanelAppClient(base_url, source_name)
    stats = {
        "source": source_name,
        "panels_found": 0,
        "genes_processed": 0,
        "genes_created": 0,
        "evidence_created": 0,
        "errors": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Search for kidney-related panels
        logger.info(f"Searching for kidney panels in {source_name}")
        panels = client.search_panels(settings.KIDNEY_FILTER_TERMS)
        stats["panels_found"] = len(panels)
        logger.info(f"Found {len(panels)} kidney-related panels")

        # Process each panel
        gene_data_map = {}  # symbol -> gene data
        for panel in panels:
            panel_id = panel["id"]
            panel_name = panel["name"]
            logger.info(f"Processing panel: {panel_name} (ID: {panel_id})")

            # Get genes from panel
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
        client.close()

    stats["completed_at"] = datetime.now(timezone.utc).isoformat()
    stats["duration"] = (
        datetime.fromisoformat(stats["completed_at"]) - datetime.fromisoformat(stats["started_at"])
    ).total_seconds()

    logger.info(
        f"PanelApp update complete: {stats['genes_processed']} genes, "
        f"{stats['genes_created']} created, {stats['evidence_created']} evidence records"
    )

    return stats


def update_all_panelapp(db: Session) -> list[dict[str, Any]]:
    """Update data from all PanelApp sources

    Args:
        db: Database session

    Returns:
        List of statistics for each source
    """
    results = []

    # Update UK PanelApp
    logger.info("Updating PanelApp UK data")
    uk_stats = update_panelapp_data(db, "uk")
    results.append(uk_stats)

    # Update Australian PanelApp
    logger.info("Updating PanelApp Australia data")
    au_stats = update_panelapp_data(db, "au")
    results.append(au_stats)

    return results
