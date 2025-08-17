"""
Test the HPO pipeline with kidney phenotypes.
"""

import asyncio
import logging
from app.core.hpo.pipeline import HPOPipeline
from app.core.progress_tracker import ProgressTracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleProgressTracker:
    """Simple progress tracker for testing."""
    
    def update_status(self, source: str, status: str):
        print(f"[{source}] {status}")
    
    def update_progress(self, source: str, current: int, total: int, message: str = ""):
        print(f"[{source}] Progress: {current}/{total} - {message}")


async def test_pipeline():
    """Test the HPO pipeline."""
    
    print("\n" + "="*60)
    print("Testing HPO Pipeline for Kidney Phenotypes")
    print("="*60)
    
    # Create pipeline and tracker
    pipeline = HPOPipeline()
    tracker = SimpleProgressTracker()
    
    # Override settings for testing (smaller depth)
    pipeline.max_depth = 2  # Limit depth for faster testing
    pipeline.batch_size = 5  # Smaller batches for testing
    
    # Get statistics first
    print("\n1. Getting pipeline statistics...")
    stats = await pipeline.get_statistics()
    print(f"   Root term: {stats['root_term']}")
    print(f"   Descendant terms: {stats['total_descendant_terms']}")
    print(f"   Sample genes: {stats['sample_genes']}")
    print(f"   Sample diseases: {stats['sample_diseases']}")
    
    # Process kidney phenotypes
    print("\n2. Processing kidney phenotypes (limited depth=2)...")
    gene_evidence = await pipeline.process_kidney_phenotypes(tracker)
    
    # Display results
    print(f"\n3. Results:")
    print(f"   Total genes found: {len(gene_evidence)}")
    
    # Show sample genes
    sample_genes = list(gene_evidence.keys())[:5]
    for gene_symbol in sample_genes:
        data = gene_evidence[gene_symbol]
        print(f"\n   Gene: {gene_symbol}")
        print(f"     - Entrez ID: {data['entrez_id']}")
        print(f"     - HPO terms: {len(data['hpo_terms'])}")
        print(f"     - Diseases: {len(data['diseases'])}")
        print(f"     - Inheritance: {data['inheritance_patterns'][:3] if data['inheritance_patterns'] else 'None'}")
    
    print("\n" + "="*60)
    print("Pipeline test completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_pipeline())