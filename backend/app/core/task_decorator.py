"""
Task decorator pattern for background tasks with common setup/teardown.

This module provides decorators and mixins to eliminate boilerplate code
in background task management, following DRY principles.
"""

import asyncio
import logging
from functools import wraps
from typing import Callable, Any, Dict

from app.core.database import get_db
from app.core.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


def managed_task(source_name: str):
    """
    Decorator for background tasks with common setup/teardown.
    
    Args:
        source_name: Name of the data source for tracking
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, resume: bool = False) -> Dict[str, Any]:
            """Wrapper with common task management logic."""
            db = None
            tracker = None
            
            try:
                # Setup
                db = next(get_db())
                tracker = ProgressTracker(db, source_name, self.broadcast_callback)
                
                logger.info(f"Starting {source_name} update (resume={resume})")
                
                # Execute the actual task
                result = await func(self, db, tracker, resume)
                
                logger.info(f"{source_name} update completed: {result}")
                return result
                
            except Exception as e:
                logger.error(f"{source_name} update failed: {e}")
                if tracker:
                    tracker.error(str(e))
                raise
                
            finally:
                # Cleanup
                if db:
                    try:
                        db.close()
                    except Exception as e:
                        logger.error(f"Failed to close database session: {e}")
                        
        return wrapper
    return decorator


def executor_task(source_name: str):
    """
    Decorator for background tasks that need to run in thread executor.
    
    Args:
        source_name: Name of the data source for tracking
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, resume: bool = False) -> Dict[str, Any]:
            """Wrapper with executor and common task management logic."""
            db = None
            tracker = None
            
            try:
                # Setup
                db = next(get_db())
                tracker = ProgressTracker(db, source_name, self.broadcast_callback)
                
                logger.info(f"Starting {source_name} update (resume={resume})")
                
                # Execute the actual task in thread executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    func,
                    self,
                    db,
                    tracker,
                    resume
                )
                
                logger.info(f"{source_name} update completed: {result}")
                return result
                
            except Exception as e:
                logger.error(f"{source_name} update failed: {e}")
                if tracker:
                    tracker.error(str(e))
                raise
                
            finally:
                # Cleanup
                if db:
                    try:
                        db.close()
                    except Exception as e:
                        logger.error(f"Failed to close database session: {e}")
                        
        return wrapper
    return decorator


class TaskMixin:
    """Mixin providing common task functionality with unified client architecture."""
    
    @managed_task("PubTator")
    async def _run_pubtator(self, db, tracker, resume: bool = False):
        """Run PubTator update with managed lifecycle."""
        from app.pipeline.sources.pubtator_async import update_pubtator_async
        return await update_pubtator_async(db, tracker)
    
    @managed_task("GenCC") 
    async def _run_gencc(self, db, tracker, resume: bool = False):
        """Run GenCC update with managed lifecycle."""
        from app.pipeline.sources.gencc_unified import get_gencc_client
        client = get_gencc_client(db_session=db)
        return await client.update_data(db, tracker)
        
    @executor_task("PanelApp")
    def _run_panelapp(self, db, tracker, resume: bool = False):
        """Run PanelApp update with managed lifecycle."""
        from app.pipeline.sources.update_all_with_progress import update_panelapp_with_progress
        return update_panelapp_with_progress(db, tracker)

    @managed_task("HPO")
    async def _run_hpo(self, db, tracker, resume: bool = False):
        """Run HPO update with managed lifecycle."""
        from app.pipeline.sources.hpo_async import update_hpo_async
        return await update_hpo_async(db, tracker)

    @executor_task("ClinGen")
    def _run_clingen(self, db, tracker, resume: bool = False):
        """Run ClinGen update with managed lifecycle."""
        from app.pipeline.sources.update_all_with_progress import update_clingen_with_progress
        return update_clingen_with_progress(db, tracker)

    @executor_task("HGNC_Normalization")
    def _run_hgnc_normalization(self, db, tracker, resume: bool = False):
        """Run HGNC normalization with managed lifecycle."""
        from app.pipeline.normalize import normalize_all_genes
        
        with tracker.track_operation("Normalizing gene symbols"):
            result = normalize_all_genes(db)
            
            tracker.update(
                items_added=result.get("normalized", 0),
                items_updated=result.get("updated", 0),
                items_failed=result.get("failed", 0)
            )
            
            return result

    @managed_task("Evidence_Aggregation")
    async def _run_evidence_aggregation(self, db, tracker, resume: bool = False):
        """Run evidence aggregation with managed lifecycle."""
        from app.pipeline.aggregate import update_all_curations
        
        tracker.start("Starting evidence aggregation")
        
        # Run synchronous code in executor with its own DB session
        loop = asyncio.get_event_loop()

        def run_aggregation():
            """Run aggregation with its own DB session"""
            agg_db = next(get_db())
            try:
                result = update_all_curations(agg_db)
                return result
            finally:
                agg_db.close()

        result = await loop.run_in_executor(
            self.executor,
            run_aggregation
        )

        tracker.update(
            items_updated=result.get("curations_updated", 0),
            items_added=result.get("curations_created", 0)
        )
        tracker.complete(f"Aggregated evidence for {result.get('genes_processed', 0)} genes")
        
        return result