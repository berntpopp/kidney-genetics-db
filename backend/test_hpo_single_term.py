#!/usr/bin/env python3
"""Test a single HPO term to see what's happening"""

import asyncio
import time
from app.core.cache_service import get_cache_service
from app.core.cached_http_client import CachedHttpClient
from app.core.hpo.pipeline import HPOPipeline
from app.core.hpo.annotations import HPOAnnotations
from app.api.deps import get_db

async def test_single_term():
    """Test processing of HP:0000077 specifically"""
    
    db = next(get_db())
    cache_service = get_cache_service(db)
    http_client = CachedHttpClient(cache_service)
    
    # Create annotations client
    annotations = HPOAnnotations(cache_service, http_client)
    
    print("Testing HP:0000077 (Abnormality of the kidney)...")
    start = time.time()
    
    try:
        # Get annotations for this term
        result = await annotations.get_term_annotations("HP:0000077")
        
        if result:
            print(f"✓ Got response in {time.time() - start:.2f} seconds")
            print(f"  - Genes: {len(result.genes)}")
            print(f"  - Diseases: {len(result.diseases)}")
            
            # Show first few genes
            if result.genes:
                print(f"  - First 5 genes: {[g.name for g in result.genes[:5]]}")
        else:
            print(f"✗ No response after {time.time() - start:.2f} seconds")
            
    except Exception as e:
        print(f"✗ Error after {time.time() - start:.2f} seconds: {e}")
    
    # Clean up
    await http_client.http_client.aclose()

if __name__ == "__main__":
    asyncio.run(test_single_term())