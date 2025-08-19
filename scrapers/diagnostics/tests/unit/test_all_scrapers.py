#!/usr/bin/env python3
"""
Test all diagnostic panel scrapers individually.
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

# Import all scrapers
from providers.ambrygen import AmbryGenScraper
from providers.cegat import CegatScraper
from providers.centogene import CentogeneScraper
from providers.color_health import ColorHealthScraper
from providers.invitae import InvitaeScraper
from providers.mayo_clinic import MayoClinicScraper
from providers.mgz_muenchen import MGZMuenchenScraper
from providers.mvz_medicover import MVZMedicoverScraper
from providers.natera import NateraScraper
from providers.prevention_genetics import PreventionGeneticsScraper

# Dictionary of scrapers with expected gene counts
SCRAPERS = {
    'AmbryGen': (AmbryGenScraper, 100),  # Estimate
    'Cegat': (CegatScraper, 336),  # Known from previous run
    'Centogene': (CentogeneScraper, 600),  # 8 panels combined
    'Color Health': (ColorHealthScraper, 40),  # Estimate
    'Invitae': (InvitaeScraper, 350),  # Estimate
    'Mayo Clinic': (MayoClinicScraper, 302),  # Documented
    'MGZ München': (MGZMuenchenScraper, 481),  # Known from previous run
    'MVZ Medicover': (MVZMedicoverScraper, 125),  # User provided
    'Natera': (NateraScraper, 400),  # 41 pages * ~10 genes per page
    'PreventionGenetics': (PreventionGeneticsScraper, 200),  # Estimate
}

def test_scraper(name, scraper_class, expected_genes):
    """Test a single scraper."""
    print(f"\n{'='*60}")
    print(f"Testing {name}...")
    print(f"{'='*60}")
    
    try:
        scraper = scraper_class()
        result = scraper.run()
        
        # Print results
        print(f"✓ Success: {result.total_unique_genes} genes found")
        print(f"  Expected: ~{expected_genes} genes")
        
        if result.total_unique_genes == 0:
            print(f"  ⚠ WARNING: No genes found!")
        elif result.total_unique_genes < expected_genes * 0.5:
            print(f"  ⚠ WARNING: Much fewer genes than expected!")
        elif result.total_unique_genes > expected_genes * 1.5:
            print(f"  ⚠ WARNING: Much more genes than expected!")
        
        # Show first 10 genes as sample
        if result.genes:
            sample_genes = [g.symbol for g in result.genes[:10]]
            print(f"  Sample genes: {', '.join(sample_genes)}")
        
        if result.errors:
            print(f"  Errors: {result.errors}")
        
        return True, result.total_unique_genes
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        logger.error(f"Error testing {name}: {e}", exc_info=True)
        return False, 0

def main():
    """Run all scrapers and show summary."""
    print("\nDiagnostic Panel Scrapers Test")
    print("================================\n")
    
    results = {}
    total_success = 0
    total_failed = 0
    
    for name, (scraper_class, expected) in SCRAPERS.items():
        success, gene_count = test_scraper(name, scraper_class, expected)
        results[name] = {
            'success': success,
            'gene_count': gene_count,
            'expected': expected
        }
        
        if success:
            total_success += 1
        else:
            total_failed += 1
    
    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total scrapers: {len(SCRAPERS)}")
    print(f"Successful: {total_success}")
    print(f"Failed: {total_failed}")
    print(f"\nDetailed Results:")
    print(f"{'Provider':<20} {'Status':<10} {'Genes Found':<15} {'Expected':<10}")
    print("-" * 60)
    
    for name, data in results.items():
        status = "✓ OK" if data['success'] else "✗ FAIL"
        genes = str(data['gene_count']) if data['success'] else "N/A"
        print(f"{name:<20} {status:<10} {genes:<15} {data['expected']:<10}")
    
    # Show problem scrapers
    problem_scrapers = [name for name, data in results.items() 
                       if not data['success'] or data['gene_count'] == 0]
    
    if problem_scrapers:
        print(f"\n⚠ Problem scrapers that need attention:")
        for name in problem_scrapers:
            print(f"  - {name}")

if __name__ == "__main__":
    main()