"""
Mayo Clinic Labs scraper - requires Playwright for Akamai protection bypass.
"""

from playwright.sync_api import sync_playwright
import re
from typing import List, Optional, Dict
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseDiagnosticScraper
from schemas import GeneEntry, ProviderData
from utils import clean_gene_symbol

logger = logging.getLogger(__name__)


class MayoClinicScraper(BaseDiagnosticScraper):
    """Scraper for Mayo Clinic Labs - single comprehensive panel"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.provider_id = "mayo_clinic"
        self.provider_name = "Mayo Clinic Labs"
        self.provider_type = "single_panel"
        self.use_browser = True  # Requires Playwright
        self.url = "https://www.mayocliniclabs.com/test-catalog/Overview/618086"
        
    def extract_genes(self) -> List[str]:
        """Extract genes using Playwright (due to Akamai protection)"""
        genes = []
        
        try:
            with sync_playwright() as p:
                logger.info("Launching browser for Mayo Clinic scraping...")
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Navigate to the page
                logger.info(f"Navigating to {self.url}")
                page.goto(self.url, wait_until='networkidle', timeout=60000)
                
                # Wait for content to load
                page.wait_for_timeout(5000)
                
                # Try to wait for specific elements that contain genes
                try:
                    page.wait_for_selector('em', timeout=5000)
                except:
                    pass
                
                # Look for the gene list in the text
                # The genes are listed after "302 genes associated with hereditary kidney disease:"
                content = page.content()
                
                # Try multiple approaches to find genes
                
                # Approach 1: Look for emphasized elements
                gene_elements = page.query_selector_all('em')
                for elem in gene_elements:
                    text = elem.inner_text()
                    # Parse gene symbols from emphasized text
                    if ',' in text or re.search(r'[A-Z]{2,}[0-9]*', text):
                        # This might be a gene list
                        potential_genes = re.split(r'[,\s]+', text)
                        for gene in potential_genes:
                            cleaned = clean_gene_symbol(gene)
                            if cleaned and 2 <= len(cleaned) <= 15:
                                genes.append(cleaned)
                
                # Approach 2: Look for the paragraph containing the gene list
                paragraphs = page.query_selector_all('p')
                for p in paragraphs:
                    text = p.inner_text()
                    if '302 genes' in text or 'hereditary kidney disease' in text:
                        # This paragraph likely contains the gene list
                        # Get all text content
                        full_text = text
                        
                        # Look for patterns after "disease:" or in emphasized text
                        # Mayo typically lists genes separated by commas
                        if ':' in full_text:
                            # Get everything after the colon
                            parts = full_text.split(':', 1)
                            if len(parts) > 1:
                                gene_section = parts[1]
                                # Extract gene symbols
                                gene_pattern = r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b'
                                potential_genes = re.findall(gene_pattern, gene_section)
                                for gene in potential_genes:
                                    cleaned = clean_gene_symbol(gene)
                                    if cleaned and 2 <= len(cleaned) <= 15:
                                        genes.append(cleaned)
                
                # Approach 3: Look specifically in div elements that might contain gene lists
                if not genes:
                    logger.info("Looking for genes in div elements")
                    divs = page.query_selector_all('div')
                    for div in divs:
                        text = div.inner_text()
                        # Check if this div contains multiple gene-like strings
                        gene_pattern = r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b'
                        potential_genes = re.findall(gene_pattern, text)
                        
                        # If we find many potential genes in one div, it's likely the gene list
                        if len(potential_genes) > 50:
                            for gene in potential_genes:
                                if 2 <= len(gene) <= 15 and not gene.startswith(('HTTP', 'MAYO', 'TEST', 'PDF')):
                                    cleaned = clean_gene_symbol(gene)
                                    if cleaned:
                                        genes.append(cleaned)
                            if genes:
                                break  # Found the gene list
                
                # Approach 4: Check table cells
                if not genes:
                    logger.info("Looking for genes in table cells")
                    cells = page.query_selector_all('td')
                    for cell in cells:
                        text = cell.inner_text().strip()
                        # Check if this looks like a gene symbol
                        if re.match(r'^[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*$', text):
                            cleaned = clean_gene_symbol(text)
                            if cleaned and 2 <= len(cleaned) <= 15:
                                genes.append(cleaned)
                
                browser.close()
                
        except Exception as e:
            logger.error(f"Error extracting genes from Mayo Clinic: {e}")
            raise
        
        # Remove duplicates and return
        unique_genes = list(set(genes))
        logger.info(f"Extracted {len(unique_genes)} unique genes from Mayo Clinic")
        return unique_genes
    
    def run(self) -> ProviderData:
        """Run Mayo Clinic scraper"""
        logger.info("Starting Mayo Clinic scraper")
        
        errors = []
        gene_entries = []
        
        try:
            genes = self.extract_genes()
            
            # Create gene entries
            gene_entries = [
                GeneEntry(
                    symbol=gene,
                    panels=["Comprehensive Nephrology Gene Panel (NEPHP)"],
                    occurrence_count=1,
                    confidence="high"  # Mayo Clinic is a trusted source
                )
                for gene in genes
            ]
            
            # Normalize genes
            gene_entries = self.normalize_genes(gene_entries)
            
        except Exception as e:
            logger.error(f"Error scraping Mayo Clinic: {e}")
            errors.append(str(e))
        
        # Create provider data
        provider_data = ProviderData(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_type=self.provider_type,
            main_url=self.url,
            total_panels=1,
            sub_panels=None,  # Single panel, no sub-panels
            total_unique_genes=len(gene_entries),
            genes=gene_entries,
            metadata={
                'panel_name': 'Comprehensive Nephrology Gene Panel (NEPHP)',
                'test_id': '618086',
                'expected_gene_count': 302,
                'actual_gene_count': len(gene_entries),
                'scraper_version': '1.0.0'
            },
            errors=errors if errors else None
        )
        
        # Save output
        self.save_output(provider_data)
        
        logger.info(f"Mayo Clinic scraping complete: {len(gene_entries)} genes")
        return provider_data


if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = MayoClinicScraper()
    result = scraper.run()
    print(f"Scraped {result.total_unique_genes} genes (expected ~302)")