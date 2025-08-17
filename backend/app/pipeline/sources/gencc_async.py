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
    from app.core.gene_normalization_async import normalize_genes_batch_async
    from app.crud.gene import gene_crud
    from app.models.gene import GeneEvidence
    from app.schemas.gene import GeneCreate

    source_name = "GenCC"
    logger.info(f"🚀 Starting {source_name} data update with cached client...")

    stats = {
        "source": source_name,
        "file_downloaded": True,  # Always true with cached client
        "total_submissions": 0,
        "kidney_related": 0,
        "genes_processed": 0,
        "genes_created": 0,
        "evidence_created": 0,
        "errors": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    tracker.start("Starting GenCC async update with cached client")

    try:
        # Initialize cached GenCC client
        client = get_gencc_client_cached(db_session=db)

        # Get processed kidney gene data (cached)
        tracker.update(operation="Fetching and processing GenCC data")
        logger.info("🔄 Fetching GenCC kidney-related gene data...")

        gene_data_map = await client.get_kidney_gene_data()

        if not gene_data_map:
            logger.warning("❌ No GenCC gene data found")
            tracker.complete("No data found")
            return stats

        stats["kidney_related"] = len(gene_data_map)
        logger.info(f"📊 Found {len(gene_data_map)} unique kidney-related genes from GenCC")

        # Process genes for normalization
        tracker.update(operation="Starting batch normalization")
        logger.info(f"🔄 Starting batch normalization of {len(gene_data_map)} genes")

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

            # Process normalization results and create/update genes
            for symbol in batch_symbols:
                try:
                    result = normalization_results.get(symbol)
                    gene_data = gene_data_map[symbol]

                    if not result:
                        logger.warning(f"No normalization result for gene '{symbol}'")
                        stats["errors"] += 1
                        continue

                    if result["status"] == "normalized":
                        approved_symbol = result["approved_symbol"]
                        hgnc_id = result["hgnc_id"]

                        # Check if gene exists
                        existing_gene = gene_crud.get_gene_by_symbol(db, approved_symbol)

                        if not existing_gene:
                            # Create new gene
                            gene_create = GeneCreate(
                                symbol=approved_symbol,
                                approved_symbol=approved_symbol,
                                hgnc_id=hgnc_id,
                                status="active"
                            )
                            new_gene = gene_crud.create(db, obj_in=gene_create)
                            stats["genes_created"] += 1
                            logger.info(f"✅ Created new gene: {approved_symbol}")

                            target_gene = new_gene
                        else:
                            target_gene = existing_gene

                        # Process evidence records from GenCC submissions
                        for submission in gene_data["submissions"]:
                            # Create unique reference ID for this submission
                            reference_id = f"gencc_{submission['submitter']}_{submission['disease_name'][:50]}"

                            # Check if evidence already exists
                            existing_evidence = db.query(GeneEvidence).filter(
                                GeneEvidence.gene_symbol == approved_symbol,
                                GeneEvidence.source == source_name,
                                GeneEvidence.reference_id == reference_id
                            ).first()

                            if not existing_evidence:
                                # Determine evidence strength from classification
                                classification = submission["classification"]
                                if classification in ["Definitive", "Strong"]:
                                    strength = "strong"
                                elif classification in ["Moderate", "Supportive"]:
                                    strength = "supporting"
                                elif classification == "Limited":
                                    strength = "weak"
                                else:
                                    strength = "conflicting"

                                # Create new evidence
                                evidence = GeneEvidence(
                                    gene_symbol=approved_symbol,
                                    source=source_name,
                                    evidence_type="gene_disease_association",
                                    strength=strength,
                                    description=f"Gene-disease association: {submission['disease_name']} (Classification: {classification})",
                                    reference_id=reference_id,
                                    metadata={
                                        "classification": classification,
                                        "disease_name": submission["disease_name"],
                                        "submitter": submission["submitter"],
                                        "mode_of_inheritance": submission["mode_of_inheritance"],
                                        "submission_date": submission["submission_date"],
                                        "hgnc_id": submission["hgnc_id"],
                                        "submitter_count": gene_data["submitter_count"],
                                        "disease_count": gene_data["disease_count"],
                                        "submission_count": gene_data["submission_count"]
                                    }
                                )
                                db.add(evidence)
                                stats["evidence_created"] += 1
                            else:
                                # Update existing evidence metadata
                                existing_evidence.metadata.update({
                                    "classification": classification,
                                    "disease_name": submission["disease_name"],
                                    "submitter": submission["submitter"],
                                    "mode_of_inheritance": submission["mode_of_inheritance"],
                                    "submission_date": submission["submission_date"],
                                    "hgnc_id": submission["hgnc_id"],
                                    "submitter_count": gene_data["submitter_count"],
                                    "disease_count": gene_data["disease_count"],
                                    "submission_count": gene_data["submission_count"]
                                })

                        stats["genes_processed"] += 1

                        # Log progress every 10 genes
                        if stats["genes_processed"] % 10 == 0:
                            logger.info(f"📊 Processed gene {stats['genes_processed']}/{len(gene_data_map)}: {approved_symbol}")

                    elif result["status"] == "requires_manual_review":
                        logger.info(f"🔍 Gene '{symbol}' sent to staging (ID: {result['staging_id']}) for manual review")

                    else:
                        logger.error(f"❌ Error normalizing gene '{symbol}': {result.get('error', 'Unknown error')}")
                        stats["errors"] += 1

                except Exception as e:
                    logger.error(f"❌ Error processing gene '{symbol}': {e}")
                    stats["errors"] += 1

            # Commit batch changes
            db.commit()

        # Final statistics
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

    except Exception as e:
        logger.error(f"❌ GenCC update failed: {e}")
        tracker.error(str(e))
        stats["errors"] += 1
        raise

    finally:
        # Ensure database session is properly handled
        if db:
            db.close()

    return stats
