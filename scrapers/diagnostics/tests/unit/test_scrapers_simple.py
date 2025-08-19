#!/usr/bin/env python3
"""
Test scrapers one by one.
"""

import logging
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_scraper(scraper_module, scraper_name):
    """Test a single scraper."""
    print(f"\n{'='*60}")
    print(f"Testing {scraper_name}...")
    print(f"{'='*60}")
    
    try:
        # Import the scraper module
        import importlib
        module = importlib.import_module(f"providers.{scraper_module}")
        scraper_class = getattr(module, f"{scraper_name}Scraper")
        
        scraper = scraper_class()
        result = scraper.run()
        
        # Print results
        print(f"✓ Success: {result.total_unique_genes} genes found")
        
        # Show first 10 genes as sample
        if result.genes:
            sample_genes = [g.symbol for g in result.genes[:10]]
            print(f"  Sample genes: {', '.join(sample_genes)}")
        
        if result.errors:
            print(f"  Errors: {result.errors}")
        
        return True, result.total_unique_genes
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        logger.error(f"Error testing {scraper_name}: {e}", exc_info=True)
        return False, 0

# Test scrapers one by one
scrapers_to_test = [
    # ('ambrygen', 'AmbryGen'),
    ('cegat', 'Cegat'),
    # ('centogene', 'Centogene'),
    # ('color_health', 'ColorHealth'),
    # ('invitae', 'Invitae'),
    ('mgz_muenchen', 'MGZMuenchen'),
    ('mvz_medicover', 'MVZMedicover'),
    ('natera', 'Natera'),
    # ('prevention_genetics', 'PreventionGenetics'),
    # ('mayo_clinic', 'MayoClinic'),  # Requires playwright
]

print("\nTesting Diagnostic Panel Scrapers")
print("==================================")

for module, name in scrapers_to_test:
    test_scraper(module, name)