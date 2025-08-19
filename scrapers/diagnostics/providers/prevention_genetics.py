"""
PreventionGenetics scraper - Comprehensive Kidney Disease Panel.
"""

from bs4 import BeautifulSoup
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


class PreventionGeneticsScraper(BaseDiagnosticScraper):
    """Scraper for PreventionGenetics - Comprehensive Kidney Disease Panel"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.provider_id = "prevention_genetics"
        self.provider_name = "PreventionGenetics"
        self.provider_type = "single_panel"
        # Use the correctly encoded URL
        self.url = "https://www.preventiongenetics.com/testInfo?val=PGmaxTM-%2D-Comprehensive-Inherited-Kidney-Diseases-Panel"
        self.use_browser = False  # Try without browser first
        
    def fetch_with_custom_browser(self):
        """Custom browser fetch that waits for gene table to load."""
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to the page
            page.goto(self.url, wait_until='networkidle', timeout=60000)
            
            # Wait for the gene table to appear
            # PreventionGenetics loads content dynamically
            page.wait_for_timeout(5000)  # Wait 5 seconds for JavaScript
            
            # Try clicking on "Show Genes" or similar button if it exists
            try:
                # Look for expandable sections
                page.click('button:has-text("Gene")', timeout=2000)
                page.wait_for_timeout(2000)
            except:
                pass
            
            # Try to wait for gene table - using the exact selector user provided
            try:
                page.wait_for_selector('td.italic.geneSymbol', timeout=5000)
            except:
                # Try alternative selectors
                try:
                    page.wait_for_selector('table', timeout=5000)
                except:
                    pass
            
            content = page.content()
            browser.close()
            return content
    
    def extract_genes(self, content: str) -> List[str]:
        """Extract genes from PreventionGenetics page"""
        soup = BeautifulSoup(content, 'html.parser')
        genes = []
        
        # PreventionGenetics lists genes in a table with class="italic geneSymbol"
        # Look specifically for these table cells
        gene_cells = soup.find_all('td', class_='italic geneSymbol')
        if gene_cells:
            for cell in gene_cells:
                gene = cell.get_text().strip()
                if gene and 2 <= len(gene) <= 15:
                    cleaned = clean_gene_symbol(gene)
                    if cleaned:
                        genes.append(cleaned)
            return list(set(genes))  # Return if we found genes this way
        
        # Fallback: look for other gene formats
        selectors = [
            'td.geneSymbol',  # Gene symbol table cells
            'td.italic',      # Italic cells that might have genes
            'table.gene-list',
            'div.panel-genes',
            'table tbody tr td:first-child',  # First column often has genes
            'div[class*="gene"]',
            'ul.genes li',
            'div.test-details'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for elem in elements:
                    text = elem.get_text()
                    # Look for gene symbols
                    potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                    for gene in potential_genes:
                        if 2 <= len(gene) <= 15:
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)
        
        # Look for genes in links (often genes are linked)
        for link in soup.find_all('a'):
            text = link.get_text().strip()
            # Check if link text looks like a gene
            if re.match(r'^[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*$', text):
                cleaned = clean_gene_symbol(text)
                if cleaned and 2 <= len(cleaned) <= 15:
                    genes.append(cleaned)
        
        # Check for genes in specific containers
        for container in soup.find_all(['div', 'section', 'article']):
            # Look for containers that might have gene lists
            if container.get('class'):
                class_str = ' '.join(container.get('class', []))
                if any(keyword in class_str.lower() for keyword in ['gene', 'panel', 'test']):
                    text = container.get_text()
                    potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                    for gene in potential_genes:
                        if (2 <= len(gene) <= 15 and 
                            not gene.startswith(('HTTP', 'DNA', 'RNA', 'TEST'))):
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)
        
        # Fallback: general search
        if not genes:
            for element in soup.find_all(['p', 'div', 'span', 'li']):
                text = element.get_text()
                if 'kidney' in text.lower() or 'renal' in text.lower():
                    potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                    for gene in potential_genes:
                        if (2 <= len(gene) <= 15 and 
                            not gene.startswith(('HTTP', 'DNA', 'RNA', 'NGS', 'PDF'))):
                            cleaned = clean_gene_symbol(gene)
                            if cleaned:
                                genes.append(cleaned)
        
        return list(set(genes))
    
    def run(self) -> ProviderData:
        """Run PreventionGenetics scraper"""
        logger.info("Starting PreventionGenetics scraper")
        
        errors = []
        gene_entries = []
        
        try:
            # Use custom browser fetch for PreventionGenetics
            content = self.fetch_with_custom_browser()
            
            # Extract genes
            genes = self.extract_genes(content)
            
            if not genes:
                logger.warning("No genes found for PreventionGenetics kidney panel")
            
            # Create gene entries
            gene_entries = [
                GeneEntry(
                    symbol=gene,
                    panels=["Comprehensive Kidney Disease Panel"],
                    occurrence_count=1,
                    confidence="high"
                )
                for gene in genes
            ]
            
            # Normalize genes
            gene_entries = self.normalize_genes(gene_entries)
            
        except Exception as e:
            logger.error(f"Error scraping PreventionGenetics: {e}")
            errors.append(str(e))
        
        # Create provider data
        provider_data = ProviderData(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_type=self.provider_type,
            main_url=self.url,
            total_panels=1,
            sub_panels=None,
            total_unique_genes=len(gene_entries),
            genes=gene_entries,
            metadata={
                'panel_name': 'Comprehensive Kidney Disease Panel',
                'scraper_version': '1.0.0'
            },
            errors=errors if errors else None
        )
        
        # Save output
        self.save_output(provider_data)
        
        logger.info(f"PreventionGenetics scraping complete: {len(gene_entries)} genes")
        return provider_data


if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = PreventionGeneticsScraper()
    result = scraper.run()
    print(f"Scraped {result.total_unique_genes} genes")