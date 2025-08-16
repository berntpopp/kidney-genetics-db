"""
HPO (Human Phenotype Ontology) data source integration

Fetches kidney-related phenotypes and associated genes from HPO
by downloading phenotype.hpoa and OMIM genemap2 files
"""

import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.gene import gene_crud
from app.models.gene import GeneEvidence
from app.schemas.gene import GeneCreate

logger = logging.getLogger(__name__)

# URLs for data files
PHENOTYPE_HPOA_URL = "http://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa"
OMIM_GENEMAP2_URL = "https://data.omim.org/downloads/Z-5l6R50RfuMa18pDNht-Q/genemap2.txt"  # Requires license - NEEDS UPDATE WITH VALID KEY


class HPOClient:
    """Client for HPO API and file processing"""

    def __init__(self):
        """Initialize HPO client"""
        self.base_url = settings.HPO_API_URL
        self.client = httpx.Client(timeout=30.0)
        self.cache_dir = Path(".cache/hpo")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Common kidney-related HPO terms
        self.kidney_hpo_terms = [
            "HP:0000083",  # Renal insufficiency
            "HP:0000112",  # Nephropathy
            "HP:0000113",  # Polycystic kidney dysplasia
            "HP:0000096",  # Glomerulonephritis
            "HP:0000097",  # Glomerulosclerosis
            "HP:0000100",  # Nephrotic syndrome
            "HP:0000103",  # Polyuria
            "HP:0000107",  # Renal cyst
            "HP:0000108",  # Renal corticomedullary cysts
            "HP:0000110",  # Renal dysplasia
            "HP:0000114",  # Proximal tubulopathy
            "HP:0000121",  # Nephrocalcinosis
            "HP:0000123",  # Nephritis
            "HP:0000793",  # Membranoproliferative glomerulonephritis
            "HP:0001919",  # Acute kidney injury
            "HP:0003073",  # Hypoalbuminemia
            "HP:0003774",  # Stage 5 chronic kidney disease
            "HP:0012211",  # Abnormal renal physiology
            "HP:0012622",  # Chronic kidney disease
        ]

    def download_file(self, url: str, file_path: Path) -> bool:
        """Download a file from URL

        Args:
            url: URL to download from
            file_path: Local path to save the file

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading {url} to {file_path}")
            response = self.client.get(url, follow_redirects=True)
            response.raise_for_status()

            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(response.content)
            logger.info(f"Successfully downloaded to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return False

    def is_cache_valid(self, file_path: Path, days: int = 30) -> bool:
        """Check if cached file is still valid

        Args:
            file_path: Path to cached file
            days: Number of days before cache expires

        Returns:
            True if cache is valid, False otherwise
        """
        if not file_path.exists():
            return False

        file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
        return file_age.days < days

    def get_descendant_terms(self, hpo_id: str, max_depth: int = 10) -> set[str]:
        """Get all descendant terms of a given HPO term recursively

        Args:
            hpo_id: HPO term ID
            max_depth: Maximum recursion depth

        Returns:
            Set of HPO term IDs including descendants
        """
        descendants = {hpo_id}

        def _collect_descendants(term_id: str, current_depth: int) -> None:
            if current_depth >= max_depth:
                return

            try:
                # Get children from API
                response = self.client.get(f"{self.base_url}/hp/terms/{term_id}/children")
                if response.status_code == 200:
                    children = response.json()
                    for child in children:
                        child_id = child.get("id") if isinstance(child, dict) else child
                        if child_id and child_id not in descendants:
                            descendants.add(child_id)
                            _collect_descendants(child_id, current_depth + 1)
            except Exception as e:
                logger.debug(f"Error getting children for {term_id}: {e}")

        _collect_descendants(hpo_id, 0)
        logger.info(f"Found {len(descendants)} descendants for {hpo_id}")
        return descendants

    def search_kidney_phenotypes(self) -> set[str]:
        """Search for kidney-related phenotypes

        Returns:
            Set of kidney-related HPO term IDs
        """
        kidney_terms = set(self.kidney_hpo_terms)

        # Also search by keyword
        for keyword in ["kidney", "renal", "nephro", "glomerul"]:
            try:
                response = self.client.get(
                    f"{self.base_url}/hp/search", params={"q": keyword, "max": 100}
                )
                if response.status_code == 200:
                    data = response.json()
                    for term in data.get("terms", []):
                        term_id = term.get("id")
                        if term_id:
                            kidney_terms.add(term_id)
            except Exception as e:
                logger.error(f"Error searching HPO for keyword '{keyword}': {e}")

        # Get descendants for all kidney terms
        all_kidney_terms = set()
        for term_id in kidney_terms:
            descendants = self.get_descendant_terms(term_id, max_depth=5)
            all_kidney_terms.update(descendants)

        logger.info(f"Found {len(all_kidney_terms)} total kidney-related HPO terms")
        return all_kidney_terms

    def parse_phenotype_hpoa(self, file_path: Path) -> pd.DataFrame:
        """Parse the phenotype.hpoa file from HPO

        Args:
            file_path: Path to phenotype.hpoa file

        Returns:
            DataFrame with parsed data
        """
        logger.info(f"Parsing phenotype.hpoa file: {file_path}")

        try:
            # Read the file, skipping comment lines
            df = pd.read_csv(
                file_path,
                sep="\t",
                comment="#",
                names=[
                    "database_id",
                    "disease_name",
                    "qualifier",
                    "hpo_id",
                    "reference",
                    "evidence",
                    "onset",
                    "frequency",
                    "sex",
                    "modifier",
                    "aspect",
                    "biocuration",
                ],
                dtype=str,
            )

            # Filter out NOT qualifiers
            df = df[df["qualifier"] != "NOT"]

            logger.info(f"Loaded {len(df)} phenotype annotations")
            return df

        except Exception as e:
            logger.error(f"Failed to parse phenotype.hpoa file: {e}")
            raise

    def parse_omim_genemap2(self, file_path: Path) -> pd.DataFrame:
        """Parse OMIM genemap2.txt file

        Args:
            file_path: Path to genemap2.txt file

        Returns:
            DataFrame with parsed data
        """
        logger.info(f"Parsing OMIM genemap2 file: {file_path}")

        try:
            # Read the file, skipping comment lines
            df = pd.read_csv(
                file_path,
                sep="\t",
                comment="#",
                names=[
                    "chromosome",
                    "genomic_position_start",
                    "genomic_position_end",
                    "cyto_location",
                    "computed_cyto_location",
                    "mim_number",
                    "gene_symbols",
                    "gene_name",
                    "approved_symbol",
                    "entrez_gene_id",
                    "ensembl_gene_id",
                    "comments",
                    "phenotypes",
                    "mouse_gene_symbol_id",
                ],
                dtype=str,
            )

            # Clean up gene symbols
            df["approved_symbol"] = df["approved_symbol"].str.strip()
            df["gene_symbols"] = df["gene_symbols"].str.strip()

            logger.info(f"Loaded {len(df)} OMIM gene entries")
            return df

        except Exception as e:
            logger.error(f"Failed to parse OMIM genemap2 file: {e}")
            raise

    def close(self):
        """Close HTTP client"""
        self.client.close()


def update_hpo_data(db: Session, use_local_omim: Path | None = None) -> dict[str, Any]:
    """Update database with HPO data

    Args:
        db: Database session
        use_local_omim: Optional path to local OMIM genemap2 file (requires license)

    Returns:
        Statistics about the update
    """
    client = HPOClient()
    stats = {
        "source": "HPO",
        "phenotypes_found": 0,
        "diseases_found": 0,
        "genes_processed": 0,
        "genes_created": 0,
        "evidence_created": 0,
        "errors": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Step 1: Get all kidney-related HPO terms
        logger.info("Finding kidney-related HPO phenotypes")
        kidney_terms = client.search_kidney_phenotypes()
        stats["phenotypes_found"] = len(kidney_terms)

        # Step 2: Download/load phenotype.hpoa file
        phenotype_hpoa_path = client.cache_dir / "phenotype.hpoa"
        if not client.is_cache_valid(phenotype_hpoa_path, days=7):
            if not client.download_file(PHENOTYPE_HPOA_URL, phenotype_hpoa_path):
                logger.error("Failed to download phenotype.hpoa")
                return stats

        # Parse phenotype.hpoa
        phenotype_df = client.parse_phenotype_hpoa(phenotype_hpoa_path)

        # Step 3: Filter for kidney HPO terms
        kidney_phenotypes = phenotype_df[phenotype_df["hpo_id"].isin(kidney_terms)]
        logger.info(f"Found {len(kidney_phenotypes)} kidney phenotype annotations")

        # Extract unique disease IDs (OMIM IDs)
        omim_diseases = kidney_phenotypes[
            kidney_phenotypes["database_id"].str.startswith("OMIM:", na=False)
        ]
        unique_omim_ids = omim_diseases["database_id"].str.extract(r"OMIM:(\d+)")[0].unique()
        stats["diseases_found"] = len(unique_omim_ids)
        logger.info(f"Found {len(unique_omim_ids)} unique OMIM disease IDs")

        # Step 4: Load OMIM genemap2 data
        if use_local_omim and use_local_omim.exists():
            # Use provided local file
            omim_df = client.parse_omim_genemap2(use_local_omim)
        else:
            # Try to use cached/download (requires OMIM license key in URL)
            omim_path = client.cache_dir / "genemap2.txt"
            if omim_path.exists():
                logger.info("Using cached OMIM genemap2 file")
                omim_df = client.parse_omim_genemap2(omim_path)
            else:
                # TODO: Once valid OMIM API key is available, implement download:
                # client.download_file(OMIM_GENEMAP2_URL, omim_path)
                logger.warning("OMIM genemap2 file not available. Requires license from OMIM.")
                logger.info("Skipping gene associations. Download from OMIM with license key.")
                logger.info(
                    "To enable: Get OMIM license and update OMIM_GENEMAP2_URL with valid key"
                )
                return stats

        # Step 5: Map OMIM diseases to genes
        gene_disease_map = {}  # symbol -> {diseases: set, phenotypes: set}

        for omim_id in unique_omim_ids:
            # Find genes associated with this OMIM disease
            disease_genes = omim_df[omim_df["phenotypes"].str.contains(omim_id, na=False)]

            for _, gene_row in disease_genes.iterrows():
                symbol = gene_row["approved_symbol"]
                if pd.isna(symbol) or not symbol:
                    continue

                if symbol not in gene_disease_map:
                    gene_disease_map[symbol] = {
                        "diseases": set(),
                        "phenotypes": set(),
                        "omim_ids": set(),
                    }

                # Get disease info
                disease_info = kidney_phenotypes[
                    kidney_phenotypes["database_id"].str.contains(omim_id, na=False)
                ]

                for _, disease_row in disease_info.iterrows():
                    gene_disease_map[symbol]["diseases"].add(disease_row["disease_name"])
                    gene_disease_map[symbol]["phenotypes"].add(disease_row["hpo_id"])
                    gene_disease_map[symbol]["omim_ids"].add(omim_id)

        # Step 6: Store in database
        for symbol, data in gene_disease_map.items():
            stats["genes_processed"] += 1

            # Get or create gene
            gene = gene_crud.get_by_symbol(db, symbol)
            if not gene:
                # Create new gene
                try:
                    gene_create = GeneCreate(
                        approved_symbol=symbol,
                        hgnc_id=None,  # Would need HGNC lookup
                        aliases=[],
                    )
                    gene = gene_crud.create(db, gene_create)
                    stats["genes_created"] += 1
                    logger.info(f"Created new gene from HPO: {symbol}")
                except Exception as e:
                    logger.error(f"Error creating gene {symbol}: {e}")
                    stats["errors"] += 1
                    continue

            # Create or update evidence
            try:
                # Check if HPO evidence already exists
                existing = (
                    db.query(GeneEvidence)
                    .filter(
                        GeneEvidence.gene_id == gene.id,  # type: ignore[arg-type]
                        GeneEvidence.source_name == "HPO",
                    )
                    .first()
                )

                evidence_data = {
                    "phenotypes": list(data["phenotypes"])[:50],  # Limit to 50
                    "diseases": list(data["diseases"])[:20],  # Limit to 20
                    "omim_ids": list(data["omim_ids"])[:20],
                    "phenotype_count": len(data["phenotypes"]),
                    "disease_count": len(data["diseases"]),
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
                        source_name="HPO",
                        source_detail=f"{len(data['phenotypes'])} phenotypes, {len(data['diseases'])} diseases",
                        evidence_data=evidence_data,
                        evidence_date=date.today(),
                    )
                    db.add(evidence)
                    stats["evidence_created"] += 1

                db.commit()
                logger.debug(f"Saved HPO evidence for gene: {symbol}")

            except Exception as e:
                logger.error(f"Error saving HPO evidence for gene {symbol}: {e}")
                db.rollback()
                stats["errors"] += 1

    finally:
        client.close()

    stats["completed_at"] = datetime.now(timezone.utc).isoformat()
    stats["duration"] = (
        datetime.fromisoformat(stats["completed_at"]) - datetime.fromisoformat(stats["started_at"])
    ).total_seconds()

    logger.info(
        f"HPO update complete: {stats['genes_processed']} genes, "
        f"{stats['genes_created']} created, {stats['evidence_created']} evidence records"
    )

    return stats
