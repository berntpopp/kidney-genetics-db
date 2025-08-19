"""
Blueprint Genetics scraper - handles all 24 kidney sub-panels.
"""

from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseDiagnosticScraper
from schemas import GeneEntry, SubPanel, ProviderData
from utils import clean_gene_symbol, calculate_confidence

logger = logging.getLogger(__name__)


class BlueprintGeneticsScraper(BaseDiagnosticScraper):
    """Scraper for Blueprint Genetics - handles all 24 kidney sub-panels"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.provider_id = "blueprint_genetics"
        self.provider_name = "Blueprint Genetics"
        self.provider_type = "multi_panel"
        self.base_url = "https://blueprintgenetics.com/tests/panels/nephrology/"
        
    def get_sub_panels(self) -> List[Dict[str, str]]:
        """Return all 24 Blueprint Genetics kidney sub-panel URLs"""
        return [
            {"name": "Alport Syndrome Panel", "url": f"{self.base_url}alport-syndrome-panel"},
            {"name": "Bartter Syndrome Panel", "url": f"{self.base_url}bartter-syndrome-panel"},
            {"name": "Bardet-Biedl Syndrome Panel", "url": f"{self.base_url}bardet-biedl-syndrome-panel"},
            {"name": "Branchio-Oto-Renal Syndrome Panel", "url": f"{self.base_url}branchio-oto-renal-bor-syndrome-panel"},
            {"name": "Ciliopathy Panel", "url": f"{self.base_url}ciliopathy-panel"},
            {"name": "Cystic Kidney Disease Panel", "url": f"{self.base_url}cystic-kidney-disease-panel"},
            {"name": "Diabetes Insipidus Panel", "url": f"{self.base_url}diabetes-insipidus-panel"},
            {"name": "Hemolytic Uremic Syndrome Panel", "url": f"{self.base_url}hemolytic-uremic-syndrome-panel"},
            {"name": "Hypomagnesemia Panel", "url": f"{self.base_url}hypomagnesemia-panel"},
            {"name": "Hypophosphatemic Rickets Panel", "url": f"{self.base_url}hypophosphatemic-rickets-panel"},
            {"name": "Joubert Syndrome Panel", "url": f"{self.base_url}joubert-syndrome-panel"},
            {"name": "Liddle Syndrome Panel", "url": f"{self.base_url}liddle-syndrome-panel"},
            {"name": "Meckel Syndrome Panel", "url": f"{self.base_url}meckel-syndrome-panel"},
            {"name": "Monogenic Obesity Panel", "url": f"{self.base_url}monogenic-obesity-panel"},
            {"name": "Nephrolithiasis Panel", "url": f"{self.base_url}nephrolithiasis-panel"},
            {"name": "Nephronophthisis Panel", "url": f"{self.base_url}nephronophthisis-panel"},
            {"name": "Nephrotic Syndrome Panel", "url": f"{self.base_url}nephrotic-syndrome-panel"},
            {"name": "Polycystic Kidney Disease Panel", "url": f"{self.base_url}polycystic-kidney-disease-panel"},
            {"name": "Primary Ciliary Dyskinesia Panel", "url": f"{self.base_url}primary-ciliary-dyskinesia-panel"},
            {"name": "Primary Hyperoxaluria Panel", "url": f"{self.base_url}primary-hyperoxaluria-panel"},
            {"name": "Pseudohypoaldosteronism Panel", "url": f"{self.base_url}pseudohypoaldosteronism-panel"},
            {"name": "Renal Malformation Panel", "url": f"{self.base_url}renal-malformation-panel"},
            {"name": "Renal Tubular Acidosis Panel", "url": f"{self.base_url}renal-tubular-acidosis-panel"},
            {"name": "Senior-Loken Syndrome Panel", "url": f"{self.base_url}senior-loken-syndrome-panel"},
        ]
    
    def extract_genes_from_panel(self, content: str) -> List[str]:
        """Extract gene symbols from a single Blueprint panel page"""
        soup = BeautifulSoup(content, 'html.parser')
        genes = []
        
        # Try multiple selectors for Blueprint Genetics tables
        selectors = [
            'table.table.mb-5',
            'table.table',
            'table[class*="table"]',
            'div.gene-list table',
            'div.panel-genes table'
        ]
        
        gene_table = None
        for selector in selectors:
            gene_table = soup.select_one(selector)
            if gene_table:
                break
        
        if gene_table:
            # Find all rows in the table
            rows = gene_table.find_all('tr')
            
            for row in rows[1:]:  # Skip header row
                # Try to find gene symbol in first column
                cols = row.find_all(['td', 'th'])
                if cols and len(cols) > 0:
                    gene_text = cols[0].get_text(strip=True)
                    gene_symbol = clean_gene_symbol(gene_text)
                    if gene_symbol:
                        genes.append(gene_symbol)
        else:
            # Fallback: look for gene symbols in various contexts
            # Try to find genes in lists or divs
            for element in soup.find_all(['div', 'span', 'p']):
                text = element.get_text()
                # Look for patterns like uppercase gene symbols
                import re
                potential_genes = re.findall(r'\b[A-Z][A-Z0-9]{1,}[0-9]*[A-Z]*\b', text)
                for gene in potential_genes:
                    if 2 <= len(gene) <= 15:  # Reasonable gene symbol length
                        genes.append(gene)
        
        return list(set(genes))  # Remove duplicates
    
    def run(self) -> ProviderData:
        """Scrape all Blueprint Genetics sub-panels"""
        logger.info(f"Starting Blueprint Genetics scraper for 24 sub-panels")
        
        sub_panels_data = []
        all_genes_dict = {}  # Track genes and which panels they appear in
        errors = []
        
        panels = self.get_sub_panels()
        
        for i, panel_info in enumerate(panels, 1):
            try:
                logger.info(f"[{i}/{len(panels)}] Scraping {panel_info['name']}...")
                
                # Fetch content
                content = self.fetch_content(panel_info['url'])
                
                # Extract genes
                panel_genes = self.extract_genes_from_panel(content)
                
                if not panel_genes:
                    logger.warning(f"No genes found for {panel_info['name']}")
                
                # Create sub-panel entry
                sub_panel = SubPanel(
                    name=panel_info['name'],
                    url=panel_info['url'],
                    gene_count=len(panel_genes),
                    genes=panel_genes
                )
                sub_panels_data.append(sub_panel)
                
                # Track genes across panels
                for gene in panel_genes:
                    if gene not in all_genes_dict:
                        all_genes_dict[gene] = []
                    all_genes_dict[gene].append(panel_info['name'])
                
                logger.info(f"Found {len(panel_genes)} genes in {panel_info['name']}")
                
                # Rate limiting
                if i < len(panels):
                    self.sleep()
                
            except Exception as e:
                logger.error(f"Error scraping {panel_info['name']}: {e}")
                errors.append(f"{panel_info['name']}: {str(e)}")
        
        # Create gene entries with panel information
        gene_entries = []
        for gene_symbol, panel_names in all_genes_dict.items():
            gene_entry = GeneEntry(
                symbol=gene_symbol,
                panels=panel_names,
                occurrence_count=len(panel_names),
                confidence=calculate_confidence(len(panel_names))
            )
            gene_entries.append(gene_entry)
        
        # Normalize genes
        gene_entries = self.normalize_genes(gene_entries)
        
        # Sort genes by occurrence count
        gene_entries.sort(key=lambda x: x.occurrence_count, reverse=True)
        
        # Create provider data
        provider_data = ProviderData(
            provider_id=self.provider_id,
            provider_name=self.provider_name,
            provider_type=self.provider_type,
            main_url=self.base_url,
            total_panels=len(sub_panels_data),
            sub_panels=sub_panels_data,
            total_unique_genes=len(gene_entries),
            genes=gene_entries,
            metadata={
                'scraper_version': '1.0.0',
                'most_common_genes': [
                    {'gene': g.symbol, 'count': g.occurrence_count} 
                    for g in gene_entries[:10]
                ] if gene_entries else [],
                'panels_scraped': len(sub_panels_data),
                'panels_failed': len(errors)
            },
            errors=errors if errors else None
        )
        
        # Save output
        self.save_output(provider_data)
        
        logger.info(f"Blueprint Genetics scraping complete: {len(gene_entries)} unique genes from {len(sub_panels_data)} panels")
        
        return provider_data


if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = BlueprintGeneticsScraper()
    result = scraper.run()
    print(f"Scraped {result.total_unique_genes} genes from {result.total_panels} panels")