"""
GenCC data source integration with unified cache system integration
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.progress_tracker import ProgressTracker
from app.pipeline.sources.gencc_cached import get_gencc_client_cached

logger = logging.getLogger(__name__)


async def update_gencc_async(db: Session, tracker: ProgressTracker) -> dict[str, Any]:
    """
    Enhanced async GenCC update using the unified cache system.

    This version provides true async processing with intelligent caching,
    replacing the thread-pool delegation approach.
    """
    source_name = "GenCC"
    logger.info(f"🚀 [ENTRY] update_gencc_async called - Starting {source_name} data update with cached client...")
    print(f"🚀 [ENTRY] update_gencc_async called - Starting {source_name} data update with cached client...")

    # Initialize stats with timestamp
    stats = {
        "source": source_name,
        "kidney_related": 0,
        "genes_processed": 0,
        "genes_created": 0,
        "evidence_created": 0,
        "errors": 0,
        "completed": False,
        "started_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        from app.core.gene_normalization_async import normalize_genes_batch_async
        from app.crud.gene import gene_crud
        from app.models.gene import GeneEvidence
        from app.schemas.gene import GeneCreate
        logger.info("🚀 [DEBUG] Imports successful")

        tracker.start("Starting GenCC async update")
        logger.info("🚀 [DEBUG] Tracker started")

        # Initialize cached GenCC client
        client = get_gencc_client_cached(db_session=db)
        logger.info("🚀 [DEBUG] Client initialized")

        # Get processed kidney gene data
        logger.info("🔄 Fetching GenCC kidney-related gene data...")
        gene_data_map = await client.get_kidney_gene_data()

        logger.info(f"🔍 GenCC returned data: {type(gene_data_map)}, length: {len(gene_data_map) if gene_data_map else 0}")

        if not gene_data_map:
            logger.warning("⚠️ No kidney-related genes found in GenCC data")
            tracker.complete("GenCC processing complete: 0 genes found")
            return stats

        stats["kidney_related"] = len(gene_data_map)

        logger.info(f"🎯 About to start normalization processing for {len(gene_data_map)} genes")
        print(f"🎯 About to start normalization processing for {len(gene_data_map)} genes")

        # Process genes for normalization
        tracker.update(operation="Starting batch normalization")
        logger.info(f"🔄 Starting batch normalization of {len(gene_data_map)} genes")
        print(f"🔄 Starting batch normalization of {len(gene_data_map)} genes")

        # Prepare gene symbols for batch normalization
        gene_symbols = list(gene_data_map.keys())

        # Use batch normalization for efficient processing
        batch_size = 50  # Process in smaller batches for progress tracking
        total_batches = (len(gene_symbols) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(gene_symbols))
            batch_symbols = gene_symbols[start_idx:end_idx]

            logger.info(f"🔄 Normalizing batch {batch_num + 1}/{total_batches} ({len(batch_symbols)} genes)")
            tracker.update(operation=f"Normalizing batch {batch_num + 1}/{total_batches}")

            # Use the enhanced async gene normalization
            normalization_results = await normalize_genes_batch_async(
                db, batch_symbols, source_name
            )

            logger.info(f"🔍 Normalization results for batch {batch_num + 1}: {len(normalization_results)} results")
            logger.info(f"   Sample results: {list(normalization_results.keys())[:3] if normalization_results else 'None'}")

            # Process normalization results and create/update genes
            for symbol in batch_symbols:
                try:
                    result = normalization_results.get(symbol)
                    gene_data = gene_data_map[symbol]

                    if not result:
                        logger.warning(f"No normalization result for gene '{symbol}'")
                        stats["errors"] += 1
                        continue

                    if result.get("status") == "normalized":
                        approved_symbol = result["approved_symbol"]
                        hgnc_id = result["hgnc_id"]

                        # Check if gene exists by HGNC ID first, then by symbol
                        existing_gene = None
                        if hgnc_id:
                            existing_gene = gene_crud.get_by_hgnc_id(db, hgnc_id)

                        if not existing_gene:
                            existing_gene = gene_crud.get_by_symbol(db, approved_symbol)

                        if not existing_gene:
                            # Create new gene
                            gene_create = GeneCreate(
                                approved_symbol=approved_symbol,
                                hgnc_id=hgnc_id,
                                aliases=result.get("aliases", [])
                            )
                            new_gene = gene_crud.create(db, obj_in=gene_create)
                            stats["genes_created"] += 1
                            logger.info(f"✅ Created new gene: {approved_symbol}")
                            target_gene = new_gene
                        else:
                            target_gene = existing_gene

                        # Create ONE aggregated evidence record per gene (not per submission)
                        source_detail = f"{approved_symbol}_aggregated_gencc_data"

                        # Check if evidence already exists for this gene
                        existing_evidence = db.query(GeneEvidence).filter(
                            GeneEvidence.gene_id == target_gene.id,
                            GeneEvidence.source_name == source_name,
                            GeneEvidence.source_detail == source_detail
                        ).first()

                        if not existing_evidence:
                            # Aggregate all submission data into a single evidence record
                            aggregated_evidence_data = {
                                "gene_symbol": approved_symbol,
                                "submitter_count": gene_data["submitter_count"],
                                "disease_count": gene_data["disease_count"],
                                "submission_count": gene_data["submission_count"],
                                "submissions": gene_data["submissions"]  # All submissions in one record
                            }

                            # Create single aggregated evidence record
                            evidence = GeneEvidence(
                                gene_id=target_gene.id,
                                source_name=source_name,
                                source_detail=source_detail,
                                evidence_data=aggregated_evidence_data
                            )
                            db.add(evidence)
                            stats["evidence_created"] += 1

                        stats["genes_processed"] += 1

                        # Log progress every 10 genes
                        if stats["genes_processed"] % 10 == 0:
                            logger.info(f"📊 Processed gene {stats['genes_processed']}/{len(gene_data_map)}: {approved_symbol}")

                    elif result.get("status") == "requires_manual_review":
                        logger.info(f"🔍 Gene '{symbol}' sent to staging (ID: {result.get('staging_id')}) for manual review")

                    elif result.get("status") == "error":
                        logger.error(f"❌ Error normalizing gene '{symbol}': {result.get('error', 'Unknown error')}")
                        stats["errors"] += 1

                    else:
                        logger.warning(f"⚠️ Unexpected normalization status for gene '{symbol}': {result.get('status', 'Unknown')}")
                        stats["errors"] += 1

                except Exception as e:
                    logger.error(f"❌ Error processing gene '{symbol}': {e}")
                    stats["errors"] += 1
                    # Rollback on error to clear bad transaction state
                    db.rollback()

            # Commit batch changes with error handling
            try:
                db.commit()
                logger.info(f"✅ Committed batch {batch_num + 1}/{total_batches}")
            except Exception as e:
                logger.error(f"❌ Error committing batch {batch_num + 1}: {e}")
                db.rollback()
                stats["errors"] += len(batch_symbols)

        # Final statistics
        stats["completed"] = True
        stats["completed_at"] = datetime.now(timezone.utc).isoformat()
        stats["duration"] = (
            datetime.fromisoformat(stats["completed_at"]) -
            datetime.fromisoformat(stats["started_at"])
        ).total_seconds()

        logger.info(
            f"✅ GenCC update complete: {stats['genes_processed']} genes processed, "
            f"{stats['genes_created']} new genes created, "
            f"{stats['evidence_created']} new evidence records, "
            f"Duration: {stats['duration']:.1f}s"
        )

        tracker.complete(
            f"GenCC processing complete: {stats['genes_processed']} genes, "
            f"{stats['genes_created']} new, {stats['evidence_created']} evidence"
        )

        return stats

    except Exception as e:
        logger.error(f"❌ GenCC update failed: {e}")
        print(f"❌ GenCC update failed: {e}")
        import traceback
        traceback.print_exc()
        tracker.error(str(e))
        raise
