"""
ClinGen data source integration

Fetches kidney-related gene-disease validity assessments from ClinGen expert panels
"""

import logging
from datetime import date, datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.crud.gene import gene_crud
from app.models.gene import Gene, GeneEvidence
from app.schemas.gene import GeneCreate

logger = logging.getLogger(__name__)


class ClinGenClient:
    """Client for ClinGen API integration"""

    def __init__(self):
        """Initialize ClinGen client"""
        self.base_url = "https://search.clinicalgenome.org/api/"
        self.client = httpx.Client(timeout=30.0)

        # Kidney-specific affiliate endpoints (identified from ClinGen API)
        self.kidney_affiliate_ids = [
            40066,  # Kidney Cystic and Ciliopathy Disorders (69 curations)
            40068,  # Glomerulopathy (17 curations)
            40067,  # Tubulopathy (24 curations)
            40069,  # Complement-Mediated Kidney Diseases (12 curations)
            40070,  # Congenital Anomalies of the Kidney and Urinary Tract (3 curations)
        ]

        # Classification scoring weights (matches percentile approach)
        self.classification_weights = {
            "Definitive": 1.0,      # 100th percentile equivalent
            "Strong": 0.8,          # 80th percentile
            "Moderate": 0.6,        # 60th percentile
            "Limited": 0.3,         # 30th percentile
            "Disputed": 0.1,        # 10th percentile
            "Refuted": 0.0,         # Excluded
            "No Evidence": 0.0,     # Excluded
        }

        # Kidney disease keywords for additional filtering
        self.kidney_keywords = [
            "kidney", "renal", "nephro", "glomerul",
            "tubul", "polycystic", "alport", "nephritis",
            "cystic", "ciliopathy", "complement"
        ]

    def fetch_affiliate_data(self, affiliate_id: int) -> list[dict[str, Any]]:
        """Fetch gene validity data from a specific ClinGen affiliate

        Args:
            affiliate_id: ClinGen affiliate ID

        Returns:
            List of gene validity records
        """
        try:
            response = self.client.get(f"{self.base_url}affiliates/{affiliate_id}")

            if response.status_code == 200:
                data = response.json()
                validities = data.get("rows", [])
                logger.info(f"Fetched {len(validities)} validity records from affiliate {affiliate_id}")
                return validities
            else:
                logger.error(f"Failed to fetch from affiliate {affiliate_id}: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching affiliate {affiliate_id}: {e}")
            return []

    def is_kidney_related(self, validity: dict[str, Any]) -> bool:
        """Check if a gene validity assessment is kidney-related

        Args:
            validity: Gene validity record

        Returns:
            True if kidney-related
        """
        # Extract disease name from ClinGen record
        disease_name = validity.get("disease_name", "").strip()

        # Also check expert panel name - these affiliates are all kidney-related
        ep_name = validity.get("ep", "")

        # Combine text for searching
        combined_text = f"{disease_name} {ep_name}".lower()

        # Debug logging
        logger.debug(f"Checking ClinGen validity: disease='{disease_name}', ep='{ep_name}'")

        # Look for kidney-related keywords
        is_kidney = any(keyword in combined_text for keyword in self.kidney_keywords)

        # Since these are kidney-specific affiliates, we can be more permissive
        # But still filter out obviously non-kidney conditions
        if not is_kidney and disease_name:
            # For kidney-specific expert panels, assume most conditions are kidney-related
            # unless they're obviously not (e.g., "hearing loss", "intellectual disability")
            excluded_terms = ["hearing", "intellectual", "developmental", "cardiac", "retinal"]
            has_excluded = any(term in combined_text for term in excluded_terms)

            if not has_excluded:
                # This is from a kidney expert panel and doesn't have excluded terms
                is_kidney = True
                logger.debug(f"Accepting from kidney expert panel: {disease_name}")

        if is_kidney:
            logger.info(f"Found kidney-related validity: {disease_name} (from {ep_name})")

        return is_kidney

    def extract_gene_info(self, validity: dict[str, Any]) -> dict[str, Any] | None:
        """Extract gene information from validity record

        Args:
            validity: Gene validity record

        Returns:
            Gene information dictionary or None if invalid
        """
        try:
            # Extract gene information - ClinGen stores these directly
            symbol = validity.get("symbol", "").strip()
            hgnc_id = validity.get("hgnc_id", "").strip()

            if not symbol:
                return None

            # Extract disease information
            disease_name = validity.get("disease_name", "").strip()

            # Extract classification
            classification = validity.get("classification", "").strip()

            # Extract other relevant data
            mode_of_inheritance = validity.get("moi", "").strip()  # ClinGen uses 'moi'
            expert_panel = validity.get("ep", "").strip()
            mondo_id = validity.get("mondo", "").strip()
            release_date = validity.get("released", "").strip()

            return {
                "symbol": symbol,
                "hgnc_id": hgnc_id,
                "disease_name": disease_name,
                "classification": classification,
                "mode_of_inheritance": mode_of_inheritance,
                "expert_panel": expert_panel,
                "mondo_id": mondo_id,
                "release_date": release_date,
                "affiliate_id": validity.get("affiliate_id"),
                "raw_data": validity  # Store full record for reference
            }

        except Exception as e:
            logger.error(f"Error extracting gene info from validity: {e}")
            return None

    def close(self):
        """Close HTTP client"""
        self.client.close()


def update_clingen_data(db: Session) -> dict[str, Any]:
    """Update database with ClinGen gene validity data

    Args:
        db: Database session

    Returns:
        Statistics about the update
    """
    source_name = "ClinGen"

    stats = {
        "source": source_name,
        "affiliates_processed": 0,
        "validities_found": 0,
        "kidney_related": 0,
        "genes_processed": 0,
        "genes_created": 0,
        "evidence_created": 0,
        "errors": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    client = ClinGenClient()

    try:
        # Aggregate gene data across all affiliates
        gene_data_map = {}  # symbol -> gene validity data

        # Process each kidney affiliate
        for affiliate_id in client.kidney_affiliate_ids:
            logger.info(f"Processing ClinGen affiliate {affiliate_id}")
            stats["affiliates_processed"] += 1

            validities = client.fetch_affiliate_data(affiliate_id)
            stats["validities_found"] += len(validities)

            for validity in validities:
                # Filter for kidney-related validities
                if not client.is_kidney_related(validity):
                    continue

                stats["kidney_related"] += 1

                # Extract gene information
                gene_info = client.extract_gene_info(validity)
                if not gene_info:
                    continue

                symbol = gene_info["symbol"]

                # Aggregate by gene symbol
                if symbol not in gene_data_map:
                    gene_data_map[symbol] = {
                        "hgnc_id": gene_info["hgnc_id"],
                        "validities": [],
                        "diseases": set(),
                        "classifications": set(),
                        "modes_of_inheritance": set(),
                    }

                gene_data_map[symbol]["validities"].append(gene_info)
                gene_data_map[symbol]["diseases"].add(gene_info["disease_name"])
                gene_data_map[symbol]["classifications"].add(gene_info["classification"])
                if gene_info["mode_of_inheritance"]:
                    gene_data_map[symbol]["modes_of_inheritance"].add(gene_info["mode_of_inheritance"])

        # Store aggregated data in database
        for symbol, data in gene_data_map.items():
            stats["genes_processed"] += 1

            # Get or create gene - handle potential symbol updates
            gene = gene_crud.get_by_symbol(db, symbol)
            if not gene and data["hgnc_id"]:
                # Check if a gene exists with this HGNC ID but different symbol
                from sqlalchemy import text
                existing_gene = db.execute(
                    text("SELECT id, approved_symbol FROM genes WHERE hgnc_id = :hgnc_id"),
                    {"hgnc_id": data["hgnc_id"]}
                ).fetchone()

                if existing_gene:
                    # Gene exists with same HGNC ID but different symbol - likely symbol update
                    gene_id, old_symbol = existing_gene
                    logger.info(f"Found existing gene {old_symbol} with HGNC ID {data['hgnc_id']}, updating symbol to {symbol}")

                    # Update the gene symbol and add old symbol as alias
                    db.execute(
                        text("UPDATE genes SET approved_symbol = :new_symbol WHERE id = :gene_id"),
                        {"new_symbol": symbol, "gene_id": gene_id}
                    )

                    # Add old symbol to aliases if not already there
                    gene_obj = db.query(Gene).filter(Gene.id == gene_id).first()
                    if gene_obj and old_symbol not in gene_obj.aliases:
                        aliases = gene_obj.aliases or []
                        aliases.append(old_symbol)
                        gene_obj.aliases = aliases
                        db.add(gene_obj)

                    db.commit()
                    gene = gene_obj
                    logger.info(f"Updated gene symbol from {old_symbol} to {symbol}")

            if not gene:
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
                    "validities": data["validities"],
                    "diseases": list(data["diseases"]),
                    "classifications": list(data["classifications"]),
                    "modes_of_inheritance": list(data["modes_of_inheritance"]),
                    "validity_count": len(data["validities"]),
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
                        source_detail=f"{len(data['validities'])} validity assessments",
                        evidence_data=evidence_data,
                        evidence_date=date.today(),
                    )
                    db.add(evidence)
                    stats["evidence_created"] += 1

                db.commit()
                logger.debug(f"Saved ClinGen evidence for gene: {symbol}")

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
        f"ClinGen update complete: {stats['affiliates_processed']} affiliates, "
        f"{stats['validities_found']} total validities, {stats['kidney_related']} kidney-related, "
        f"{stats['genes_processed']} genes, {stats['genes_created']} created, "
        f"{stats['evidence_created']} evidence records"
    )

    return stats
