"""
Simple test of HPO pipeline with very limited scope.
"""

import asyncio
import logging
from app.core.hpo.pipeline import HPOPipeline

logging.basicConfig(level=logging.WARNING)  # Reduce logging


async def test_simple():
    """Simple test with just a few terms."""
    
    print("\nTesting HPO Pipeline (Simple)")
    print("-" * 40)
    
    pipeline = HPOPipeline()
    
    # Test with just the root term (no descendants)
    pipeline.max_depth = 0  # No recursion
    pipeline.batch_size = 2
    
    # Just get annotations for the root term
    annotations = await pipeline.annotations.get_term_annotations("HP:0010935")
    
    if annotations:
        print(f"✓ Root term HP:0010935 has:")
        print(f"  - {len(annotations.genes)} genes")
        print(f"  - {len(annotations.diseases)} diseases")
        
        # Show first 3 genes
        if annotations.genes:
            print(f"\n  First 3 genes:")
            for gene in annotations.genes[:3]:
                print(f"    • {gene.name} ({gene.id})")
        
        # Test disease inheritance for first OMIM disease
        omim_diseases = [d for d in annotations.diseases if d.id.startswith("OMIM:")][:1]
        if omim_diseases:
            disease = omim_diseases[0]
            print(f"\n  Testing disease: {disease.id}")
            disease_info = await pipeline.annotations.get_disease_annotations(disease.id)
            if disease_info:
                inheritance = disease_info.get_inheritance_patterns()
                if inheritance:
                    print(f"    • Inheritance: {inheritance[0].name}")
    
    print("\n✓ Simple test completed!")


if __name__ == "__main__":
    asyncio.run(test_simple())