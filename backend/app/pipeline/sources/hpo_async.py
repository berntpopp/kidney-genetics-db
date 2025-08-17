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
            
            # Check if normalization was successful (has HGNC ID)
            if gene_info.get("source") == "not_found" or not gene_info.get("hgnc_id"):
                # Stage for manual review
                from app.crud.gene_staging import staging_crud
                
                logger.info(f"Gene '{gene_symbol}' requires manual review - staging for normalization")
                
                staging_record = staging_crud.create_staging_record(
                    db=db,
                    original_text=gene_symbol,
                    source_name=source_name,
                    normalization_log={
                        "reason": "HGNC ID not found",
                        "normalization_result": gene_info,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    original_data={
                        "evidence": evidence_data,
                        "hpo_terms": evidence_data["hpo_terms"],
                        "diseases": evidence_data["diseases"]
                    }
                )
                
                stats["genes_staged"] = stats.get("genes_staged", 0) + 1
                logger.info(f"Gene '{gene_symbol}' staged with ID {staging_record.id}")
                continue
            
            # Get or create gene (only if we have HGNC ID)
            approved_symbol = gene_info.get("approved_symbol", gene_symbol)
            hgnc_id = gene_info.get("hgnc_id")
            
            # CRITICAL FIX: Check if gene exists by HGNC ID first to avoid duplicates
            gene = None
            if hgnc_id:
                gene = gene_crud.get_by_hgnc_id(db, hgnc_id)
                if gene:
                    logger.debug(f"Found existing gene by HGNC ID {hgnc_id}: {gene.approved_symbol}")
            
            # If not found by HGNC ID, try by symbol
            if not gene:
                gene = gene_crud.get_by_symbol(db, approved_symbol)
                if gene:
                    logger.debug(f"Found existing gene by symbol: {approved_symbol}")
            
            # Create new gene only if it doesn't exist
            if not gene:
                # Create new gene WITH HGNC ID
                gene_create = GeneCreate(
                    approved_symbol=approved_symbol,
                    hgnc_id=hgnc_id,
                    aliases=gene_info.get("alias_symbols", [])
                )
                gene = gene_crud.create(db, obj_in=gene_create)
                stats["genes_created"] += 1
                logger.debug(f"Created new gene: {approved_symbol} with HGNC ID {hgnc_id}")
            
            stats["genes_processed"] += 1
            
            # Check if evidence already exists for this gene
            existing_evidence = db.query(GeneEvidence).filter_by(
                gene_id=gene.id,
                source_name=source_name,
                source_detail=f"HPO kidney phenotypes"
            ).first()
            
            evidence_data_dict = {
                "hpo_terms": evidence_data["hpo_terms"],
                "diseases": evidence_data["diseases"],
                "inheritance_patterns": evidence_data["inheritance_patterns"],
                "phenotype_count": len(evidence_data["hpo_terms"]),
                "disease_count": len(evidence_data["diseases"])
            }
            
            if existing_evidence:
                # Update existing evidence
                existing_evidence.evidence_data = evidence_data_dict
                existing_evidence.evidence_date = datetime.now(timezone.utc).date()
                stats["evidence_updated"] = stats.get("evidence_updated", 0) + 1
                logger.debug(f"Updated existing HPO evidence for gene {approved_symbol}")
            else:
                # Create new evidence entry
                evidence = GeneEvidence(
                    gene_id=gene.id,
                    source_name=source_name,
                    source_detail=f"HPO kidney phenotypes",
                    evidence_data=evidence_data_dict,
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
        staged_count = stats.get('genes_staged', 0)
        tracker.update(
            operation=f"✅ Complete: {stats['genes_processed']} genes, "
            f"{stats['evidence_created']} evidence entries" +
            (f", {staged_count} staged for review" if staged_count > 0 else "")
        )
        
        logger.info(f"✅ {source_name} update completed successfully")
        logger.info(f"   - HPO terms processed: {stats['total_hpo_terms']}")
        logger.info(f"   - Genes found: {stats['total_genes_found']}")
        logger.info(f"   - Genes processed: {stats['genes_processed']}")
        logger.info(f"   - Evidence created: {stats['evidence_created']}")
        if staged_count > 0:
            logger.info(f"   - Genes staged for review: {staged_count}")
        
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