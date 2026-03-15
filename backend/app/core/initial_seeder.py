"""
Initial data seeder for empty databases.

On first startup (when no DiagnosticPanels/Literature evidence exists),
loads seed data from backend/app/data/seed/. Mirrors the ingestion endpoint:
parse all files → merge into one dataset → normalize/create genes → store evidence.
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
    dp_count: int = (
        db.query(GeneEvidence).filter(GeneEvidence.source_name == "DiagnosticPanels").count()
    )
    lit_count: int = db.query(GeneEvidence).filter(GeneEvidence.source_name == "Literature").count()
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


async def _seed_source(db: Session, source_name: str, config: dict[str, Any]) -> dict[str, Any]:
    """
    Seed a single source by parsing all files, merging, normalizing genes,
    then storing evidence — mirrors the ingestion endpoint flow.
    """
    from app.core.gene_normalizer import normalize_genes_batch_async
    from app.pipeline.sources.unified import get_unified_source

    seed_dir = config["dir"]
    id_field = config["id_field"]

    if not seed_dir.exists():
        return {"status": "skipped", "reason": "no seed dir"}

    json_files = sorted(seed_dir.glob("*.json"))
    if not json_files:
        return {"status": "skipped", "reason": "no files"}

    logger.sync_info(
        "Seeding source",
        source_name=source_name,
        file_count=len(json_files),
    )

    source: Any = get_unified_source(source_name, db_session=db)

    # Step 1: Parse all files and merge processed data across files
    all_processed: dict[str, Any] = {}
    files_loaded = 0

    for json_file in json_files:
        try:
            file_content = json_file.read_bytes()
            file_data = json.loads(file_content)
            identifier = file_data.get(id_field, json_file.stem)

            raw_data = await source.parse_uploaded_file(file_content, "json", identifier)
            processed = await source.process_data(raw_data)

            if not processed:
                continue

            # Merge this file's processed data into the combined dataset
            # Each file's process_data returns {symbol: {...}} — we need to
            # merge panels/providers or publications across files
            for symbol, data in processed.items():
                if symbol not in all_processed:
                    all_processed[symbol] = data
                else:
                    existing = all_processed[symbol]
                    if source_name == "DiagnosticPanels":
                        # Merge panels and providers
                        existing_panels = set(existing.get("panels", []))
                        new_panels = set(data.get("panels", []))
                        existing["panels"] = sorted(existing_panels | new_panels)
                        existing_providers = set(existing.get("providers", []))
                        new_providers = set(data.get("providers", []))
                        existing["providers"] = sorted(existing_providers | new_providers)
                        existing_hgnc = set(existing.get("hgnc_ids", []))
                        new_hgnc = set(data.get("hgnc_ids", []))
                        existing["hgnc_ids"] = sorted(existing_hgnc | new_hgnc)
                        existing["panel_count"] = len(existing["panels"])
                        existing["provider_count"] = len(existing["providers"])
                    elif source_name == "Literature":
                        # Merge publications
                        existing_pubs = set(existing.get("publications", []))
                        new_pubs = set(data.get("publications", []))
                        existing["publications"] = sorted(existing_pubs | new_pubs)
                        existing_details = existing.get("publication_details", {})
                        new_details = data.get("publication_details", {})
                        existing_details.update(new_details)
                        existing["publication_details"] = existing_details
                        existing_hgnc = set(existing.get("hgnc_ids", []))
                        new_hgnc = set(data.get("hgnc_ids", []))
                        existing["hgnc_ids"] = sorted(existing_hgnc | new_hgnc)
                        existing["publication_count"] = len(existing["publications"])

            files_loaded += 1

        except (json.JSONDecodeError, OSError) as e:
            logger.sync_warning("Failed to load seed file", file=str(json_file), error=str(e))
        except Exception as e:
            logger.sync_error("Error parsing seed file", file=str(json_file), error=str(e))

    if not all_processed:
        return {"status": "skipped", "reason": "no genes after processing"}

    logger.sync_info(
        "All files parsed and merged",
        source_name=source_name,
        files_loaded=files_loaded,
        unique_genes=len(all_processed),
    )

    # Step 2: Normalize and create missing genes (same as ingestion endpoint)
    gene_symbols = list(all_processed.keys())
    batch_size = 50
    total_batches = (len(gene_symbols) + batch_size - 1) // batch_size
    genes_created = 0

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(gene_symbols))
        batch_symbols = gene_symbols[start_idx:end_idx]

        normalization_results = await normalize_genes_batch_async(db, batch_symbols, source_name)

        for symbol in batch_symbols:
            norm_result = normalization_results.get(symbol, {})
            if norm_result.get("status") == "normalized":
                gene = await source._get_or_create_gene(
                    db, norm_result, symbol, {"genes_created": 0, "genes_updated": 0}
                )
                if gene and norm_result.get("created"):
                    genes_created += 1

        db.commit()

    logger.sync_info(
        "Gene normalization complete",
        source_name=source_name,
        genes_created=genes_created,
        total_symbols=len(gene_symbols),
    )

    # Step 3: Store merged evidence in one call
    evidence_stats = await source.store_evidence(
        db,
        all_processed,
        source_detail=f"Seeded from {files_loaded} files",
        mode="merge",
    )
    db.commit()

    total_stored = evidence_stats.get("created", 0) + evidence_stats.get("merged", 0)
    logger.sync_info(
        "Seeding complete",
        source_name=source_name,
        unique_genes=len(all_processed),
        genes_created=genes_created,
        evidence_stored=total_stored,
        files_loaded=files_loaded,
    )

    return {
        "status": "seeded",
        "files": files_loaded,
        "unique_genes": len(all_processed),
        "genes_created": genes_created,
        "evidence_stored": total_stored,
        "evidence_stats": evidence_stats,
    }


async def run_initial_seeding(db: Session) -> dict[str, Any]:
    """
    Seed database with DiagnosticPanels and Literature data from seed files.

    Returns summary of what was loaded.
    """
    results: dict[str, Any] = {}

    for source_name, config in SEED_CONFIGS.items():
        try:
            results[source_name] = await _seed_source(db, source_name, config)
        except Exception as e:
            logger.sync_error(
                "Seeding failed for source",
                source_name=source_name,
                error=str(e),
            )
            results[source_name] = {"status": "failed", "error": str(e)}

    return results
