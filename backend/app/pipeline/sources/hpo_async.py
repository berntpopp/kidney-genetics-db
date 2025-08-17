"""
HPO data source integration with async processing.

This module uses the new modular HPO architecture to fetch kidney-related
phenotypes and associated genes with disease information from the HPO API.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.cached_http_client import CachedHttpClient
from app.core.hpo.pipeline import HPOPipeline
from app.core.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


async def update_hpo_async(db: Session, tracker: ProgressTracker) -> dict[str, Any]:
    """
    Async HPO update using the new modular architecture.
    
    This implementation:
    - Uses HP:0010935 (Abnormality of upper urinary tract) as root term
    - Fetches all descendant terms
    - Gets gene-disease associations via HPO API
    - Extracts inheritance patterns from disease data
    - Disease information (including OMIM) obtained via HPO API
    
    Args:
        db: Database session
        tracker: Progress tracker for status updates
    
    Returns:
        Dictionary with update statistics
    """
    from app.core.cache_service import get_cache_service
    from app.core.gene_normalization_async import normalize_genes_batch_async
    from app.crud.gene import gene_crud
    from app.models.gene import GeneEvidence
    from app.schemas.gene import GeneCreate
    
    source_name = "HPO"
    logger.info(f"🚀 Starting {source_name} data update with new architecture...")
    
    stats = {
        "source": source_name,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "root_term": "HP:0010935",
        "total_hpo_terms": 0,
        "total_genes_found": 0,
        "genes_processed": 0,
        "genes_created": 0,
        "evidence_created": 0,
        "errors": 0,
        "completed": False
    }
    
    try:
        # Initialize HPO pipeline with caching
        # Create fresh HTTP client to avoid closed connection issues
        cache_service = get_cache_service(db)
        http_client = CachedHttpClient(cache_service)
        pipeline = HPOPipeline(cache_service, http_client)
        
        # Update tracker
        tracker.update(operation="Initializing HPO pipeline...")
        
        # Process kidney phenotypes
        logger.info("Starting kidney phenotype processing...")
        gene_evidence_map = await pipeline.process_kidney_phenotypes(tracker)
        
        stats["total_genes_found"] = len(gene_evidence_map)
        logger.info(f"Found {len(gene_evidence_map)} genes with kidney phenotypes")
        if gene_evidence_map:
            logger.info(f"First 5 genes: {list(gene_evidence_map.keys())[:5]}")
        
        if not gene_evidence_map:
            logger.warning("No genes found with kidney phenotypes - check HPO API responses")
            stats["completed"] = True
            return stats
        
        # Normalize gene symbols in batch
        tracker.update(operation="Normalizing gene symbols...")
        gene_symbols = list(gene_evidence_map.keys())
        normalized_genes = await normalize_genes_batch_async(db, gene_symbols, "HPO")
        
        # Process each gene
        tracker.update(operation="Creating gene records...")
        
        for i, (gene_symbol, evidence_data) in enumerate(gene_evidence_map.items()):
            tracker.update(
                current_item=i + 1,
                total_items=len(gene_evidence_map),
                operation=f"Processing {gene_symbol}"
            )
            
            # Get normalized gene info
            gene_info = normalized_genes.get(gene_symbol, {})
            if not gene_info:
                logger.warning(f"Could not normalize gene symbol: {gene_symbol}")
                stats["errors"] += 1
                continue
            
            # Get or create gene
            approved_symbol = gene_info.get("approved_symbol", gene_symbol)
            
            # Check if gene exists
            gene = gene_crud.get_by_symbol(db, approved_symbol)
            if not gene:
                # Create new gene
                gene_create = GeneCreate(
                    approved_symbol=approved_symbol,
                    hgnc_id=gene_info.get("hgnc_id"),
                    aliases=gene_info.get("alias_symbols", [])
                )
                gene = gene_crud.create(db, obj_in=gene_create)
                stats["genes_created"] += 1
            
            stats["genes_processed"] += 1
            
            # Create evidence entry
            evidence = GeneEvidence(
                gene_id=gene.id,
                source_name=source_name,
                source_detail=f"HPO kidney phenotypes",
                evidence_data={
                    "hpo_terms": evidence_data["hpo_terms"],
                    "diseases": evidence_data["diseases"],
                    "inheritance_patterns": evidence_data["inheritance_patterns"],
                    "phenotype_count": len(evidence_data["hpo_terms"]),
                    "disease_count": len(evidence_data["diseases"])
                },
                evidence_date=datetime.now(timezone.utc).date()
            )
            
            db.add(evidence)
            stats["evidence_created"] += 1
            
            # Commit periodically
            if (i + 1) % 50 == 0:
                db.commit()
                logger.info(f"Committed {i + 1} genes")
        
        # Final commit
        db.commit()
        
        # Get final statistics
        pipeline_stats = await pipeline.get_statistics()
        stats["total_hpo_terms"] = pipeline_stats["total_descendant_terms"]
        stats["completed"] = True
        stats["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        # Update tracker with final status
        tracker.update(
            operation=f"✅ Complete: {stats['genes_processed']} genes, "
            f"{stats['evidence_created']} evidence entries"
        )
        
        logger.info(f"✅ {source_name} update completed successfully")
        logger.info(f"   - HPO terms processed: {stats['total_hpo_terms']}")
        logger.info(f"   - Genes found: {stats['total_genes_found']}")
        logger.info(f"   - Genes processed: {stats['genes_processed']}")
        logger.info(f"   - Evidence created: {stats['evidence_created']}")
        
    except Exception as e:
        logger.error(f"Error during {source_name} update: {e}", exc_info=True)
        stats["error"] = str(e)
        stats["completed"] = False
        
        tracker.error(error_message=str(e))
        
        # Rollback on error
        db.rollback()
        raise
    
    finally:
        # Clean up HTTP client if needed
        if 'http_client' in locals() and hasattr(http_client, 'close'):
            await http_client.close()
    
    return stats