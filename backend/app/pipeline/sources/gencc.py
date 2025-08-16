"""
GenCC data source integration

Fetches kidney-related gene-disease relationships from Gene Curation Coalition
"""

import logging
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.crud.gene import gene_crud
from app.models.gene import Gene, GeneEvidence
from app.schemas.gene import GeneCreate

logger = logging.getLogger(__name__)


def clean_data_for_json(data: Any) -> Any:
    """Clean data by replacing NaN/None values with empty strings for JSON serialization"""
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(item) for item in data]
    elif pd.isna(data) or data is None:
        return ""
    else:
        return data


class GenCCClient:
    """Client for GenCC data integration"""

    def __init__(self):
        """Initialize GenCC client"""
        self.download_url = "https://search.thegencc.org/download/action/submissions-export-xlsx"
        # Much longer timeout for large file download (GenCC file is ~3.6MB)
        self.client = httpx.Client(timeout=httpx.Timeout(120.0, connect=30.0, read=120.0))

        # Same kidney keywords as ClinGen for consistency
        self.kidney_keywords = [
            "kidney", "renal", "nephro", "glomerul",
            "tubul", "polycystic", "alport", "nephritis",
            "cystic", "ciliopathy", "complement", "cakut"
        ]

        # GenCC classification mapping to weights
        self.classification_weights = {
            "Definitive": 1.0,
            "Strong": 0.8,
            "Moderate": 0.6,
            "Supportive": 0.5,
            "Limited": 0.3,
            "Disputed Evidence": 0.1,
            "No Known Disease Relationship": 0.0,  # Excluded
            "Refuted Evidence": 0.0,  # Excluded
        }

    def download_excel_file(self) -> Path | None:
        """Download GenCC submissions Excel file

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            logger.info(f"📥 Downloading GenCC submissions from: {self.download_url}")
            logger.info("🔄 Starting download... (this may take 30-60 seconds for ~3.6MB file)")

            with self.client.stream('GET', self.download_url) as response:
                logger.info(f"📊 GenCC download response: {response.status_code}")

                if response.status_code == 200:
                    # Save to temporary file with progress tracking
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                    total_downloaded = 0

                    for chunk in response.iter_bytes(chunk_size=8192):
                        temp_file.write(chunk)
                        total_downloaded += len(chunk)

                        # Log progress every 500KB
                        if total_downloaded % (500 * 1024) == 0 or total_downloaded < 500 * 1024:
                            logger.info(f"📊 Downloaded {total_downloaded:,} bytes...")

                    temp_file.close()
                    file_path = Path(temp_file.name)
                    logger.info(f"✅ Downloaded GenCC file: {file_path} ({total_downloaded:,} bytes)")
                    return file_path
                else:
                    logger.error(f"❌ Failed to download GenCC file: HTTP {response.status_code}")
                    logger.error(f"Response headers: {dict(response.headers)}")
                    return None

        except Exception as e:
            logger.error(f"❌ Error downloading GenCC file: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None

    def parse_excel_file(self, file_path: Path) -> pd.DataFrame:
        """Parse GenCC Excel file

        Args:
            file_path: Path to Excel file

        Returns:
            DataFrame with submissions data
        """
        try:
            # Read Excel file - usually first sheet contains the submissions
            df = pd.read_excel(file_path)
            logger.info(f"Parsed GenCC Excel file: {len(df)} total submissions")

            # Debug: Log column names to understand the structure
            logger.info(f"GenCC columns: {list(df.columns)}")

            # Debug: Show first few rows of relevant columns
            if len(df) > 0:
                # Try to find disease-related columns
                disease_cols = [col for col in df.columns if any(term in col.lower() for term in ['disease', 'condition', 'phenotype', 'disorder'])]
                if disease_cols:
                    logger.info(f"Disease-related columns found: {disease_cols}")
                    # Show some sample values
                    for col in disease_cols[:2]:  # Limit to first 2 columns
                        sample_values = df[col].dropna().head(10).tolist()
                        logger.info(f"Sample {col} values: {sample_values}")

            return df

        except Exception as e:
            logger.error(f"Error parsing GenCC Excel file: {e}")
            return pd.DataFrame()
        finally:
            # Clean up temporary file
            try:
                file_path.unlink()
            except OSError:
                pass

    def is_kidney_related(self, row: pd.Series) -> bool:
        """Check if a GenCC submission is kidney-related

        Args:
            row: DataFrame row with GenCC submission

        Returns:
            True if kidney-related
        """
        # Check disease name and description fields
        # Common GenCC columns (may vary): 'disease_name', 'disease_description', 'condition'
        text_fields = []
        used_fields = []

        # Try GenCC-specific field names for disease information
        for field in ['disease_title', 'disease_original_title', 'submitted_as_disease_name',
                      'disease_name', 'condition', 'disease', 'phenotype', 'disorder']:
            if field in row.index and pd.notna(row[field]):
                text_fields.append(str(row[field]).lower())
                used_fields.append(field)

        # Also check any description fields
        for field in row.index:
            if 'description' in field.lower() and pd.notna(row[field]):
                text_fields.append(str(row[field]).lower())
                used_fields.append(field)

        # Combine all text
        combined_text = " ".join(text_fields)

        # Look for kidney-related keywords
        is_kidney = any(keyword in combined_text for keyword in self.kidney_keywords)

        # Debug logging for first few rows to understand the filtering (disabled)
        # if hasattr(self, '_debug_count'):
        #     self._debug_count += 1
        # else:
        #     self._debug_count = 1
        #
        # if self._debug_count <= 5:  # Only log first 5 rows for debugging
        #     logger.info(f"GenCC row {self._debug_count}: fields={used_fields}, text='{combined_text[:200]}...', kidney={is_kidney}")

        return is_kidney

    def extract_gene_info(self, row: pd.Series) -> dict[str, Any] | None:
        """Extract gene information from GenCC submission

        Args:
            row: DataFrame row with GenCC submission

        Returns:
            Gene information dictionary or None if invalid
        """
        try:
            # Extract gene symbol - use GenCC-specific field names
            symbol = None
            for field in ['gene_symbol', 'submitted_as_hgnc_symbol', 'symbol', 'gene', 'hgnc_symbol']:
                if field in row.index and pd.notna(row[field]):
                    symbol = str(row[field]).strip()
                    break

            if not symbol:
                return None

            # Extract HGNC ID if available
            hgnc_id = None
            for field in ['submitted_as_hgnc_id', 'hgnc_id', 'hgnc']:
                if field in row.index and pd.notna(row[field]):
                    hgnc_id = str(row[field]).strip()
                    break

            # Extract disease information - use GenCC field names
            disease_name = ""
            for field in ['disease_title', 'disease_original_title', 'submitted_as_disease_name',
                          'disease_name', 'condition', 'disease', 'phenotype']:
                if field in row.index and pd.notna(row[field]):
                    disease_name = str(row[field]).strip()
                    break

            # Extract classification - use GenCC field names
            classification = ""
            for field in ['classification_title', 'submitted_as_classification_name',
                          'classification', 'validity', 'confidence']:
                if field in row.index and pd.notna(row[field]):
                    classification = str(row[field]).strip()
                    break

            # Extract submitter information - use GenCC field names
            submitter = ""
            for field in ['submitter_title', 'submitted_as_submitter_name',
                          'submitter', 'source', 'submitting_organization']:
                if field in row.index and pd.notna(row[field]):
                    submitter = str(row[field]).strip()
                    break

            # Extract other relevant fields - use GenCC field names
            mode_of_inheritance = ""
            for field in ['moi_title', 'submitted_as_moi_name',
                          'mode_of_inheritance', 'inheritance', 'moi']:
                if field in row.index and pd.notna(row[field]):
                    mode_of_inheritance = str(row[field]).strip()
                    break

            # Extract date information - use GenCC field names
            submission_date = ""
            for field in ['submitted_as_date', 'submitted_run_date', 'date', 'submission_date', 'last_updated']:
                if field in row.index and pd.notna(row[field]):
                    submission_date = str(row[field]).strip()
                    break

            return {
                "symbol": symbol,
                "hgnc_id": hgnc_id,
                "disease_name": disease_name,
                "classification": classification,
                "submitter": submitter,
                "mode_of_inheritance": mode_of_inheritance,
                "submission_date": submission_date,
                "raw_data": row.to_dict()  # Store full record for reference
            }

        except Exception as e:
            logger.error(f"Error extracting gene info from GenCC row: {e}")
            return None

    def close(self):
        """Close HTTP client"""
        self.client.close()


def update_gencc_data(db: Session) -> dict[str, Any]:
    """Update database with GenCC gene-disease data

    Args:
        db: Database session

    Returns:
        Statistics about the update
    """
    source_name = "GenCC"
    logger.info(f"🚀 Starting {source_name} data update...")

    stats = {
        "source": source_name,
        "file_downloaded": False,
        "total_submissions": 0,
        "kidney_related": 0,
        "genes_processed": 0,
        "genes_created": 0,
        "evidence_created": 0,
        "errors": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    client = GenCCClient()
    logger.info(f"📡 Created {source_name} client, starting download...")

    try:
        # Download Excel file
        logger.info("🔄 Downloading GenCC Excel file...")
        file_path = client.download_excel_file()
        if not file_path:
            logger.error("❌ Failed to download GenCC file")
            return stats

        stats["file_downloaded"] = True
        logger.info(f"✅ GenCC file downloaded successfully: {file_path}")

        # Parse Excel file
        logger.info("🔄 Parsing GenCC Excel file...")
        df = client.parse_excel_file(file_path)
        if df.empty:
            logger.error("❌ Failed to parse GenCC file or file is empty")
            return stats

        stats["total_submissions"] = len(df)
        logger.info(f"📊 Parsed {len(df)} total GenCC submissions")

        # Aggregate gene data
        gene_data_map = {}  # symbol -> gene data
        logger.info("🔄 Processing GenCC submissions for kidney-related genes...")

        for idx, row in df.iterrows():
            # Filter for kidney-related submissions
            if not client.is_kidney_related(row):
                continue

            stats["kidney_related"] += 1

            # Log every 10th kidney-related submission for debugging
            if stats["kidney_related"] % 10 == 1:
                logger.info(f"🔍 Found kidney-related submission #{stats['kidney_related']}")

            # Extract gene information
            gene_info = client.extract_gene_info(row)
            if not gene_info:
                logger.debug(f"⚠️ Failed to extract gene info from row {idx}")
                continue

            symbol = gene_info["symbol"]

            # Aggregate by gene symbol
            if symbol not in gene_data_map:
                gene_data_map[symbol] = {
                    "hgnc_id": gene_info["hgnc_id"],
                    "submissions": [],
                    "diseases": set(),
                    "classifications": set(),
                    "submitters": set(),
                    "modes_of_inheritance": set(),
                }

            gene_data_map[symbol]["submissions"].append(gene_info)
            gene_data_map[symbol]["diseases"].add(gene_info["disease_name"])
            gene_data_map[symbol]["classifications"].add(gene_info["classification"])
            gene_data_map[symbol]["submitters"].add(gene_info["submitter"])
            if gene_info["mode_of_inheritance"]:
                gene_data_map[symbol]["modes_of_inheritance"].add(gene_info["mode_of_inheritance"])

        # Store aggregated data in database
        logger.info(f"💾 Storing {len(gene_data_map)} unique genes in database...")
        for symbol, data in gene_data_map.items():
            stats["genes_processed"] += 1

            # Log every 5th gene for debugging
            if stats["genes_processed"] % 5 == 1:
                logger.info(f"💾 Processing gene #{stats['genes_processed']}: {symbol}")

            # Get or create gene - handle potential symbol updates
            gene = gene_crud.get_by_symbol(db, symbol)
            if not gene and data["hgnc_id"]:
                # Check if a gene exists with this HGNC ID but different symbol
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

                # Clean data before JSON serialization
                raw_evidence_data = {
                    "submissions": data["submissions"],
                    "diseases": list(data["diseases"]),
                    "classifications": list(data["classifications"]),
                    "submitters": list(data["submitters"]),
                    "modes_of_inheritance": list(data["modes_of_inheritance"]),
                    "submission_count": len(data["submissions"]),
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                }
                evidence_data = clean_data_for_json(raw_evidence_data)

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
                        source_detail=f"{len(data['submissions'])} submissions from {len(data['submitters'])} submitters",
                        evidence_data=evidence_data,
                        evidence_date=date.today(),
                    )
                    db.add(evidence)
                    stats["evidence_created"] += 1

                db.commit()
                logger.debug(f"Saved GenCC evidence for gene: {symbol}")

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
        f"GenCC update complete: {stats['total_submissions']} total submissions, "
        f"{stats['kidney_related']} kidney-related, {stats['genes_processed']} genes, "
        f"{stats['genes_created']} created, {stats['evidence_created']} evidence records"
    )

    return stats
