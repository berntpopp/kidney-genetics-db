"""
Test HPO update with limited scope.
"""

import asyncio
import logging
from app.core.database import SessionLocal
from app.core.progress_tracker import ProgressTracker
from app.pipeline.sources.hpo_async import update_hpo_async

logging.basicConfig(level=logging.INFO)


class SimpleProgressTracker:
    """Simple progress tracker for testing."""
    
    def update_status(self, source: str, status: str):
        print(f"[{source}] {status}")
    
    def update_progress(self, source: str, current: int, total: int, message: str = ""):
        if current % 10 == 0 or current == total:  # Only log every 10th item
            print(f"[{source}] Progress: {current}/{total} - {message}")
    
    def start(self, source: str, resume: bool = False):
        print(f"[{source}] Starting...")
    
    def complete(self, source: str):
        print(f"[{source}] Completed!")
    
    def fail(self, source: str, error: str):
        print(f"[{source}] Failed: {error}")


async def test_hpo_update():
    """Test HPO update with very limited scope."""
    
    print("\n" + "="*60)
    print("Testing HPO Update (Limited Scope)")
    print("="*60)
    
    # Create database session and tracker
    db = SessionLocal()
    tracker = SimpleProgressTracker()
    
    try:
        # Override settings for minimal testing
        from app.core.hpo.pipeline import HPOPipeline
        
        # Temporarily limit the pipeline scope
        original_max_depth = HPOPipeline.KIDNEY_ROOT_TERM
        HPOPipeline.KIDNEY_ROOT_TERM = "HP:0000113"  # Just one specific term for testing
        
        # Run the update
        stats = await update_hpo_async(db, tracker)
        
        # Restore original setting
        HPOPipeline.KIDNEY_ROOT_TERM = original_max_depth
        
        # Display results
        print("\n" + "-"*40)
        print("Update Statistics:")
        print("-"*40)
        for key, value in stats.items():
            if key not in ["started_at", "completed_at"]:
                print(f"  {key}: {value}")
        
        if stats.get("completed"):
            print("\n✅ HPO update test completed successfully!")
        else:
            print("\n❌ HPO update test failed!")
            if "error" in stats:
                print(f"   Error: {stats['error']}")
    
    finally:
        db.close()
    
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_hpo_update())