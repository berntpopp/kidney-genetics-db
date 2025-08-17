"""
Test script for HPO modules.
"""

import asyncio
import logging
from app.core.hpo import HPOTerms, HPOAnnotations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_hpo_modules():
    """Test the HPO module functionality."""
    
    # Initialize modules without cache for testing
    terms_client = HPOTerms()
    annotations_client = HPOAnnotations()
    
    print("\n" + "="*60)
    print("Testing HPO Modules")
    print("="*60)
    
    # Test 1: Get a specific HPO term
    print("\n1. Testing get_term for HP:0000113 (Polycystic kidney dysplasia)...")
    term = await terms_client.get_term("HP:0000113")
    if term:
        print(f"   ✓ Term: {term.name}")
        print(f"   ✓ ID: {term.id}")
        print(f"   ✓ Children: {len(term.children)} terms")
    else:
        print("   ✗ Failed to get term")
    
    # Test 2: Get children
    print("\n2. Testing get_children for HP:0010935 (Abnormality of upper urinary tract)...")
    children = await terms_client.get_children("HP:0010935")
    print(f"   ✓ Found {len(children)} direct children")
    if children:
        print(f"   ✓ First 3 children: {children[:3]}")
    
    # Test 3: Get annotations for a term
    print("\n3. Testing get_term_annotations for HP:0000113...")
    annotations = await annotations_client.get_term_annotations("HP:0000113")
    if annotations:
        print(f"   ✓ Genes: {len(annotations.genes)}")
        print(f"   ✓ Diseases: {len(annotations.diseases)}")
        if annotations.genes:
            print(f"   ✓ First 3 genes: {[g.name for g in annotations.genes[:3]]}")
        if annotations.diseases:
            print(f"   ✓ First 3 diseases: {[d.id for d in annotations.diseases[:3]]}")
    else:
        print("   ✗ Failed to get annotations")
    
    # Test 4: Get disease annotations with inheritance
    print("\n4. Testing disease annotations for OMIM:608836...")
    disease_annotations = await annotations_client.get_disease_annotations("OMIM:608836")
    if disease_annotations:
        inheritance = disease_annotations.get_inheritance_patterns()
        print(f"   ✓ Disease: {disease_annotations.disease_name}")
        print(f"   ✓ Genes: {len(disease_annotations.genes)}")
        print(f"   ✓ Inheritance patterns: {len(inheritance)}")
        if inheritance:
            print(f"   ✓ Inheritance: {[p.name for p in inheritance]}")
    else:
        print("   ✗ Failed to get disease annotations")
    
    # Test 5: Test descendants (limited depth for speed)
    print("\n5. Testing get_descendants for HP:0000113 (depth=2)...")
    descendants = await terms_client.get_descendants("HP:0000113", max_depth=2)
    print(f"   ✓ Found {len(descendants)} descendants (including self)")
    
    # Test 6: Test batch annotations
    print("\n6. Testing batch_get_annotations for 3 terms...")
    test_terms = ["HP:0000113", "HP:0000096", "HP:0000097"]
    batch_results = await annotations_client.batch_get_annotations(test_terms, batch_size=2)
    print(f"   ✓ Successfully fetched {len(batch_results)}/{len(test_terms)} annotations")
    
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_hpo_modules())