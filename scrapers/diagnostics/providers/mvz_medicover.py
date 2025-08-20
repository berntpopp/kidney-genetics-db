"""
MVZ Medicover scraper - Kidney diseases genetic testing.
"""

import logging
import os
import re
import sys
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_scraper import BaseDiagnosticScraper
from schemas import GeneEntry, ProviderData
from utils import clean_gene_symbol

logger = logging.getLogger(__name__)

class MVZMedicoverScraper(BaseDiagnosticScraper):
    """Scraper for MVZ Medicover - Kidney genetic testing"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config, provider_id="mvz_medicover")
        self.provider_name = "MVZ Medicover"
        self.provider_type = "single_panel"
        self.use_browser = True  # Page may use JavaScript

    def extract_genes(self, content: str) -> List[str]:
        """Extract genes from MVZ Medicover page"""
        genes = []

        # The Medicover page has genes embedded in JSON within the HTML
        # Look for gene slugs in the format: "slug":"genename"
        import re

        # Find all gene slugs in the HTML
        gene_pattern = r'"slug":"([a-zA-Z0-9]+)"'
        matches = re.findall(gene_pattern, content)

        # Process matches
        for match in matches:
            # Convert to uppercase
            gene = match.upper()
            # Check if it looks like a gene symbol
            if gene and gene[0].isalpha() and 2 <= len(gene) <= 15:
                # Skip common non-gene words
                if gene not in ['DISEASES', 'GENES', 'PANELS', 'INFO', 'TYPE',
                               'NAME', 'URI', 'SLUG', 'NODE', 'PAGE', 'DATA'] and \
                   not gene.endswith('SYNDROM') and gene != 'MORBUSFABRY':  # Skip disease names
                    cleaned = clean_gene_symbol(gene)
                    if cleaned:
                        genes.append(cleaned)

        # Remove duplicates while preserving order
        seen = set()
        unique_genes = []
        for gene in genes:
            if gene not in seen:
                seen.add(gene)
                unique_genes.append(gene)

        return unique_genes

    def _parse_continuous_gene_string_deprecated(self, gene_string: str) -> List[str]:
        """Parse a continuous string of gene symbols dynamically."""
        genes = []

        # Use a more sophisticated approach:
        # 1. Look for known gene patterns
        # 2. Split on likely boundaries

        # Common kidney disease genes as anchors
        anchor_genes = ['COL4A3', 'COL4A4', 'COL4A5', 'PKD1', 'PKD2', 'PKHD1',
                       'NPHS1', 'NPHS2', 'WT1', 'PAX2', 'HNF1B', 'UMOD']

        remaining = gene_string

        # First pass: extract known anchor genes
        for anchor in anchor_genes:
            if anchor in remaining:
                genes.append(anchor)
                remaining = remaining.replace(anchor, '|', 1)

        # Second pass: use regex to find gene-like patterns
        # Gene patterns in order of specificity
        patterns = [
            r'([A-Z]{2,6}\d{1,3}[A-Z]\d?)',  # Like SLC12A3, COL4A3
            r'([A-Z]{3,8}\d{1,3})',          # Like PKD1, CEP290
            r'([A-Z]{4,8})',                  # Like GANAB, DSTYK
            r'([A-Z]{2,3}\d)',               # Like CD2
            r'([A-Z]{3})',                    # Like ACE, AGT
        ]

        # Split remaining string by anchors
        segments = remaining.split('|')

        for segment in segments:
            if not segment:
                continue

            # Try to extract genes from this segment
            while segment:
                found = False

                # Try each pattern
                for pattern in patterns:
                    match = re.match(pattern, segment)
                    if match:
                        gene = match.group(1)
                        if gene not in genes and 2 <= len(gene) <= 15:
                            genes.append(gene)
                        segment = segment[len(gene):]
                        found = True
                        break

                # If no pattern matched, try to find next uppercase letter
                if not found:
                    # Skip to next uppercase letter
                    next_upper = 1
                    while next_upper < len(segment) and not segment[next_upper].isupper():
                        next_upper += 1
                    segment = segment[next_upper:]

        return genes

    def _is_likely_gene_deprecated(self, candidate: str, next_chars: str) -> bool:
        """Check if a string is likely a gene symbol."""
        # Must start with uppercase letter
        if not candidate[0].isupper():
            return False

        # Common gene patterns
        if re.match(r'^[A-Z]{2,6}[0-9]{1,3}[A-Z]?[0-9]?$', candidate):  # Like COL4A3, PKD1
            return True
        if re.match(r'^[A-Z]{3,8}$', candidate):  # Like ACE, GDNF
            # Check if next character suggests end of gene
            if next_chars and next_chars[0].isupper():
                return True
        if re.match(r'^[A-Z]{2,}[0-9]+[A-Z]{1,2}$', candidate):  # Like SLC12A3
            return True
        if candidate in ['ACE', 'AGT', 'REN', 'RET', 'GLA', 'WT1']:  # Known short genes
            return True

        return False

    def run(self) -> ProviderData:
        """Run MVZ Medicover scraper"""
        logger.info("Starting MVZ Medicover scraper")

        errors = []
        gene_entries = []

        try:
            # Fetch content
            content = self.fetch_content(self.url)

            # Extract genes
            genes = self.extract_genes(content)

            if not genes:
                logger.warning("No genes found for MVZ Medicover kidney panel")

            # Create gene entries
            gene_entries = [
                GeneEntry(
                    symbol=gene,
                    panels=["Kidney Diseases Panel"],
                    occurrence_count=1,
                    confidence="high"
                )
                for gene in genes
            ]

            # Normalize genes
            gene_entries = self.normalize_genes(gene_entries)

        except Exception as e:
            logger.error(f"Error scraping MVZ Medicover: {e}")
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
                'panel_name': 'Kidney Diseases Panel',
                'scraper_version': '1.0.0'
            },
            errors=errors if errors else None
        )

        # Save output
        self.save_output(provider_data)

        logger.info(f"MVZ Medicover scraping complete: {len(gene_entries)} genes")
        return provider_data

if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    scraper = MVZMedicoverScraper()
    result = scraper.run()
    print(f"Scraped {result.total_unique_genes} genes")
