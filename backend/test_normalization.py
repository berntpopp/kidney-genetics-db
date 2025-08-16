#!/usr/bin/env python3
"""
Test script for the new gene normalization system
"""

from app.core.database import get_db
from app.core.gene_normalization import normalize_gene_for_database

def main():
    db = next(get_db())
    
    # Test cases representing various gene text formats from PubTator
    test_cases = [
        "PKD1",           # Should normalize successfully
        "ABCA4",          # Should normalize successfully  
        "ALBUMIN",        # Generic term - should require manual review
        "APOLIPOPROTEIN L1",  # Long form - should normalize to APOL1
        "COMPLEMENT 3",   # Protein name - should normalize to C3
        "TGF-BETA",       # Common variation - should normalize to TGFB1
        "INVALID123",     # Invalid gene - should require manual review
    ]
    
    print("=== Testing Gene Normalization System ===\n")
    
    for gene_text in test_cases:
        print(f"Testing: '{gene_text}'")
        
        try:
            result = normalize_gene_for_database(
                db=db,
                gene_text=gene_text,
                source_name="Test",
                original_data={"test": True}
            )
            
            print(f"  Status: {result['status']}")
            
            if result["status"] == "normalized":
                print(f"  ✅ Normalized to: {result['approved_symbol']} ({result['hgnc_id']})")
            elif result["status"] == "requires_manual_review":
                print(f"  ⚠️  Requires manual review (Staging ID: {result['staging_id']})")
            else:
                print(f"  ❌ Error: {result.get('error', 'Unknown')}")
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")
            
        print()
    
    db.close()
    print("Test completed!")

if __name__ == "__main__":
    main()