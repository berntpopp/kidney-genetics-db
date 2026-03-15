"""
Initial data seeder for empty databases.

On first startup (when gene_evidence is empty), loads DiagnosticPanels
and Literature data from backend/app/data/seed/ (version-controlled).
This provides baseline evidence data before the pipeline runs.
"""

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.gene import GeneEvidence

logger = get_logger(__name__)

# Seed data lives in backend/app/data/seed/ (version-controlled)
SEED_DATA_DIR = Path(__file__).parent.parent / "data" / "seed"

SEED_CONFIGS: dict[str, dict[str, Any]] = {
    "DiagnosticPanels": {
        "dir": SEED_DATA_DIR / "diagnostic_panels",
        "id_field": "provider_name",
    },
    "Literature": {
        "dir": SEED_DATA_DIR / "literature",
        "id_field": "pmid",
    },
}


def needs_initial_seeding(db: Session) -> bool:
    """Check if the database needs initial evidence seeding.

    Returns True if neither DiagnosticPanels nor Literature evidence exists.
    """
    dp_count = (
        db.query(GeneEvidence)
        .filter(GeneEvidence.source_name == "DiagnosticPanels")
        .count()
    )
    lit_count = (
        db.query(GeneEvidence)
        .filter(GeneEvidence.source_name == "Literature")
        .count()
    )
    return dp_count == 0 and lit_count == 0


def find_latest_scraper_output(base_dir: Path) -> Path | None:
    """Find the most recent date-stamped output directory."""
    if not base_dir.exists():
        return None

    date_dirs = sorted(
        [d for d in base_dir.iterdir() if d.is_dir() and d.name[0].isdigit()],
        key=lambda d: d.name,
        reverse=True,
    )
    return date_dirs[0] if date_dirs else None


async def run_initial_seeding(db: Session) -> dict[str, Any]:
    """
    Seed database with DiagnosticPanels and Literature data from seed files.

    Uses each source's parse_uploaded_file + process_data + store_evidence
    methods — the same code path as the upload API endpoint.

    Returns summary of what was loaded.
    """
    from app.pipeline.sources.unified import get_unified_source

    results: dict[str, Any] = {}

    for source_name, config in SEED_CONFIGS.items():
        seed_dir = config["dir"]
        id_field = config["id_field"]

        if not seed_dir.exists():
            logger.sync_warning(
                "No seed directory found",
                source_name=source_name,
                seed_dir=str(seed_dir),
            )
            results[source_name] = {"status": "skipped", "reason": "no seed dir"}
            continue

        json_files = sorted(seed_dir.glob("*.json"))
        if not json_files:
            logger.sync_warning(
                "No JSON files found in seed directory",
                source_name=source_name,
                seed_dir=str(seed_dir),
            )
            results[source_name] = {"status": "skipped", "reason": "no files"}
            continue

        logger.sync_info(
            "Seeding from seed files",
            source_name=source_name,
            seed_dir=str(seed_dir),
            file_count=len(json_files),
        )

        source = get_unified_source(source_name, db_session=db)
        total_genes = 0
        file_results = []

        for json_file in json_files:
            try:
                file_content = json_file.read_bytes()
                file_data = json.loads(file_content)

                # Get the identifier for this file
                identifier = file_data.get(id_field, json_file.stem)

                # Parse using the source's parse method
                if source_name == "DiagnosticPanels":
                    raw_data = await source.parse_uploaded_file(
                        file_content, "json", identifier
                    )
                else:
                    raw_data = await source.parse_uploaded_file(
                        file_content, "json", identifier
                    )

                # Process into gene data
                processed = await source.process_data(raw_data)
                if not processed:
                    logger.sync_debug(
                        "No genes in seed file",
                        file=json_file.name,
                        source_name=source_name,
                    )
                    continue

                # Store evidence
                stats = await source.store_evidence(
                    db,
                    processed,
                    source_detail=identifier,
                    original_filename=json_file.name,
                    mode="merge",
                )

                gene_count = stats.get("created", 0) + stats.get("merged", 0)
                total_genes += gene_count
                file_results.append(
                    {"file": json_file.name, "genes": gene_count}
                )

                logger.sync_debug(
                    "Seeded file",
                    file=json_file.name,
                    source_name=source_name,
                    genes=gene_count,
                )

            except (json.JSONDecodeError, OSError) as e:
                logger.sync_warning(
                    "Failed to load seed file",
                    file=str(json_file),
                    error=str(e),
                )
            except Exception as e:
                logger.sync_error(
                    "Error seeding file",
                    file=str(json_file),
                    source_name=source_name,
                    error=str(e),
                )

        db.commit()
        results[source_name] = {
            "status": "seeded",
            "files": len(file_results),
            "total_genes": total_genes,
            "details": file_results,
        }
        logger.sync_info(
            "Seeding complete for source",
            source_name=source_name,
            total_genes=total_genes,
            files_loaded=len(file_results),
        )

    return results
