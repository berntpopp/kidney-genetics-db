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
    
    # Simplified for debugging - just return basic stats
    stats = {
        "source": source_name,
        "kidney_related": 0,
        "genes_processed": 0,
        "genes_created": 0,
        "evidence_created": 0,
        "errors": 0,
        "completed": True
    }
    
    try:
        from app.core.gene_normalization_async import normalize_genes_batch_async
        from app.crud.gene import gene_crud
        from app.models.gene import GeneEvidence
        from app.schemas.gene import GeneCreate
        logger.info("🚀 [DEBUG] Imports successful")
        print("🚀 [DEBUG] Imports successful")
        
        tracker.start("Starting GenCC async update")
        logger.info("🚀 [DEBUG] Tracker started")
        print("🚀 [DEBUG] Tracker started")
        
        # Initialize cached GenCC client
        client = get_gencc_client_cached(db_session=db)
        logger.info("🚀 [DEBUG] Client initialized")
        print("🚀 [DEBUG] Client initialized")

        # Get processed kidney gene data
        logger.info("🔄 Fetching GenCC kidney-related gene data...")
        print("🔄 Fetching GenCC kidney-related gene data...")
        
        gene_data_map = await client.get_kidney_gene_data()
        
        logger.info(f"🔍 GenCC returned data: {type(gene_data_map)}, length: {len(gene_data_map) if gene_data_map else 0}")
        print(f"🔍 GenCC returned data: {type(gene_data_map)}, length: {len(gene_data_map) if gene_data_map else 0}")
        
        if gene_data_map:
            sample_keys = list(gene_data_map.keys())[:3] if gene_data_map else []
            logger.info(f"   Sample genes: {sample_keys}")
            print(f"   Sample genes: {sample_keys}")
            stats["kidney_related"] = len(gene_data_map)
            stats["genes_processed"] = len(gene_data_map)
        
        tracker.complete(f"GenCC processing complete: {stats['genes_processed']} genes processed")
        logger.info(f"✅ GenCC update completed: {stats}")
        print(f"✅ GenCC update completed: {stats}")
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ GenCC update failed: {e}")
        print(f"❌ GenCC update failed: {e}")
        import traceback
        traceback.print_exc()
        tracker.error(str(e))
        raise
