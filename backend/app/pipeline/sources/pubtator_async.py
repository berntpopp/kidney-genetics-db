"""
Async PubTator implementation with unified cache system integration
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.progress_tracker import ProgressTracker
from app.pipeline.sources.pubtator_cached import get_pubtator_client_cached

logger = logging.getLogger(__name__)


async def update_pubtator_async(db: Session, tracker: ProgressTracker) -> dict[str, Any]:
    """
    Enhanced async PubTator update using the unified cache system.
    
    This version provides true async processing with intelligent caching,
    replacing the thread-pool delegation approach.
    """
    from app.core.config import settings
    from app.core.gene_normalization import normalize_genes_batch
    from app.crud.gene import gene_crud
    from app.models.gene import GeneEvidence
    from app.schemas.gene import GeneCreate

    stats = {
        "source": "PubTator",
        "queries_processed": 0,
        "genes_processed": 0,
        "genes_created": 0,
        "evidence_created": 0,
        "evidence_updated": 0,
        "errors": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        # Initialize cached PubTator client
        client = get_pubtator_client_cached(db_session=db)

        # Start tracking
        tracker.start("Initializing PubTator search with cached client")

        # Get configured number of pages from settings
        max_pages = settings.PUBTATOR_MAX_PAGES
        logger.info(f"Searching PubTator with comprehensive kidney disease query for {max_pages} pages")
        tracker.update(operation="Fetching PubTator data", total_pages=max_pages, current_page=0)

        # Use cached client for data retrieval
        all_gene_data = await client.get_annotations_by_search(
            client.kidney_query,
            max_pages=max_pages,
            tracker=tracker
        )
        stats["queries_processed"] = 1

        if not all_gene_data:
            logger.warning("No gene data found from PubTator search")
            tracker.complete("No data found")
            return stats

        logger.info(f"Found {len(all_gene_data)} unique genes from PubTator search")

        # Filter genes by minimum publication threshold
        filtered_genes = {
            symbol: data for symbol, data in all_gene_data.items()
            if len(data.get("pmids", [])) >= settings.PUBTATOR_MIN_PUBLICATIONS
        }

        logger.info(f"Filtered to {len(filtered_genes)} genes with >= {settings.PUBTATOR_MIN_PUBLICATIONS} publications")

        if not filtered_genes:
            logger.warning("No genes met the minimum publication threshold")
            tracker.complete("No genes met publication threshold")
            return stats

        # Process genes for normalization
        tracker.update(operation="Starting batch normalization")
        logger.info(f"Starting batch normalization of {len(filtered_genes)} genes")

        # Prepare gene symbols for batch normalization
        gene_symbols = list(filtered_genes.keys())

        # Use batch normalization for efficient processing
        batch_size = 50  # Process in smaller batches for progress tracking
        total_batches = (len(gene_symbols) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(gene_symbols))
            batch_symbols = gene_symbols[start_idx:end_idx]

            logger.info(f"Normalizing batch {batch_num + 1}/{total_batches} ({len(batch_symbols)} genes)")
            tracker.update(operation=f"Normalizing batch {batch_num + 1}/{total_batches}")

            # Use the enhanced gene normalization with async support
            normalization_results = normalize_genes_batch(
                db, batch_symbols, "PubTator"
            )

            # Process normalization results and create/update genes
            for symbol in batch_symbols:
                try:
                    result = normalization_results.get(symbol)
                    gene_data = filtered_genes[symbol]

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
                            logger.info(f"Created new gene: {approved_symbol}")

                            target_gene = new_gene
                        else:
                            target_gene = existing_gene

                        # Process evidence records
                        pmids = gene_data.get("pmids", [])
                        for pmid in pmids:
                            # Check if evidence already exists
                            existing_evidence = db.query(GeneEvidence).filter(
                                GeneEvidence.gene_symbol == approved_symbol,
                                GeneEvidence.source == "PubTator",
                                GeneEvidence.reference_id == pmid
                            ).first()

                            if not existing_evidence:
                                # Create new evidence
                                evidence = GeneEvidence(
                                    gene_symbol=approved_symbol,
                                    source="PubTator",
                                    evidence_type="literature",
                                    strength="supporting",
                                    description=f"Gene mentioned in PubMed article {pmid}",
                                    reference_id=pmid,
                                    metadata={
                                        "ncbi_gene_ids": gene_data.get("ncbi_gene_ids", []),
                                        "mentions": gene_data.get("mentions", 1),
                                        "search_query": client.kidney_query
                                    }
                                )
                                db.add(evidence)
                                stats["evidence_created"] += 1
                            else:
                                # Update existing evidence metadata
                                existing_evidence.metadata = {
                                    "ncbi_gene_ids": gene_data.get("ncbi_gene_ids", []),
                                    "mentions": gene_data.get("mentions", 1),
                                    "search_query": client.kidney_query
                                }
                                stats["evidence_updated"] += 1

                        stats["genes_processed"] += 1

                        # Log progress every 10 genes
                        if stats["genes_processed"] % 10 == 0:
                            logger.info(f"Storing gene {stats['genes_processed']}/{len(filtered_genes)}: {approved_symbol}")

                    elif result["status"] == "requires_manual_review":
                        logger.info(f"Gene '{symbol}' sent to staging (ID: {result['staging_id']}) for manual review")

                    else:
                        logger.error(f"Error normalizing gene '{symbol}': {result.get('error', 'Unknown error')}")
                        stats["errors"] += 1

                except Exception as e:
                    logger.error(f"Error processing gene '{symbol}': {e}")
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
            f"PubTator update complete: {stats['genes_processed']} genes processed, "
            f"{stats['genes_created']} new genes created, "
            f"{stats['evidence_created']} new evidence records, "
            f"{stats['evidence_updated']} updated evidence records, "
            f"Duration: {stats['duration']:.1f}s"
        )

        tracker.complete(
            f"PubTator processing complete: {stats['genes_processed']} genes, "
            f"{stats['genes_created']} new, {stats['evidence_created']} evidence"
        )

    except Exception as e:
        logger.error(f"PubTator update failed: {e}")
        tracker.error(str(e))
        stats["errors"] += 1
        raise

    finally:
        # Ensure database session is properly handled
        if db:
            db.close()

    return stats
