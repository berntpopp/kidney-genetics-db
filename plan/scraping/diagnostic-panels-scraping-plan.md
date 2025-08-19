# Diagnostic Panels Web Scraping Plan

## Overview
This document contains the complete plan for scraping diagnostic panel data from commercial genetic testing laboratories. These panels represent curated lists of genes associated with kidney diseases used in clinical genetic testing.

## Data Source: 03_DiagnosticPanels
- **Purpose**: Collect gene lists from commercial diagnostic panels for kidney diseases
- **Evidence Threshold**: Genes appearing in ≥2 diagnostic panels are considered evidence
- **Original Implementation**: R script using PhantomJS for dynamic content (`kidney-genetics-v1/analyses/03_DiagnosticPanels/`)

## Target Diagnostic Panel Websites

### 1. Centogene Nephrology (CentoNephro)
- **OLD URL**: https://www.centogene.com/diagnostics/our-tests/ngs-panels/nephrology (301 redirect)
- **NEW URL**: https://www.centoportal.com/order/new/products/analysis-method?queryType=TEST&query=CentoNephro
- **Extraction Method**: HTML table with XPath `//*[@id="t3m-Modal--74334"]//table[1]` (needs verification with new site)
- **Gene Column**: "Gene" (needs verification)
- **Status**: ✅ New URL confirmed working (200 OK)

### 2. CeGaT Kidney Diseases  
- **URL**: https://cegat.com/diagnostics/rare-diseases/kidney-diseases/
- **Extraction Method**: HTML `<em>` tags after "Gene Directory" H2 heading
- **XPath**: `//h2[contains(text(),"Gene Directory")]//following::em`
- **Status**: To be tested

### 3. PreventionGenetics Comprehensive Inherited Kidney Diseases
- **URL**: https://www.preventiongenetics.com/testInfo?val=PGmaxTM-%252D-Comprehensive-Inherited-Kidney-Diseases-Panel
- **Extraction Method**: HTML table in `genes-div`
- **XPath**: `//*[@id="genes-div"]//table[1]`
- **Gene Column**: "Official Gene Symbol"
- **Status**: To be tested

### 4. Invitae Progressive Renal Disease Panel
- **URL**: https://www.invitae.com/us/providers/test-catalog/test-75000
- **Extraction Method**: Meta tag content
- **XPath**: `//meta[contains(@content,"ACE")]`
- **Status**: To be tested

### 5. Invitae Expanded Renal Disease Panel
- **URL**: https://www.invitae.com/us/providers/test-catalog/test-633100
- **Extraction Method**: Meta tag content (same as above)
- **XPath**: `//meta[contains(@content,"ACE")]`
- **Status**: To be tested

### 6. MGZ München Nephrology
- **URL**: https://www.mgz-muenchen.de/gen-panels/section/nephrologie-endokrinologie-und-elektrolyte/tag/14.html
- **Extraction Method**: Div elements with class "panel_gene"
- **XPath**: `//div[contains(@class,"panel_gene")]`
- **Status**: To be tested

### 7. MVZ Medicover Kidney Diseases
- **URL**: https://www.medicover-diagnostics.de/lvz/panels/nierenerkrankungen-2806
- **Extraction Method**: Div elements with class "items-start"
- **XPath**: `//div[contains(@class,"items-start")]`
- **Status**: To be tested

### 8. Natera Renasight Comprehensive Kidney Gene Panel
- **Main URL**: https://www.natera.com/organ-health/renasight-genetic-testing/gene-conditions-list/
- **API URL**: https://www.natera.com/wp-admin/admin-ajax.php
- **Extraction Method**: Custom pagination through AJAX API
- **Special Requirements**: Requires pagination handling
- **Status**: To be tested

### 9. Mayo Clinic Labs Renal Genetics (NEPHP)
- **URL**: https://www.mayocliniclabs.com/test-catalog/Overview/618086
- **Panel Name**: Comprehensive Nephrology Gene Panel (NEPHP)
- **Gene Count**: 302 genes
- **Extraction Method**: Gene list in paragraph after "This test utilizes next-generation sequencing"
- **Access Requirements**: Requires browser automation (Playwright/Selenium) - blocks curl/wget
- **Known Issues**: Returns 403 with regular HTTP requests due to Akamai protection
- **Status**: ✅ Accessible via browser automation (tested with Playwright)

### 10. Blueprint Genetics Nephrology
- **Main URL**: https://blueprintgenetics.com/tests/panels/nephrology/
- **Extraction Method**: HTML table with class "table mb-5"
- **XPath**: `//table[contains(@class,"table mb-5")]`
- **Gene Column**: "Gene"
- **Sub-panels** (24 total):
  1. Alport Syndrome Panel
  2. Bartter Syndrome Panel
  3. Ciliopathy Panel
  4. Diabetes Insipidus Panel
  5. Hypomagnesemia Panel
  6. Joubert Syndrome Panel
  7. Meckel Syndrome Panel
  8. Nephrolithiasis Panel
  9. Nephrotic Syndrome Panel
  10. Primary Ciliary Dyskinesia Panel
  11. Pseudohypoaldosteronism Panel
  12. Renal Tubular Acidosis Panel
  13. Bardet-Biedl Syndrome Panel
  14. Branchio-Oto-Renal (BOR) Syndrome Panel
  15. Cystic Kidney Disease Panel
  16. Hemolytic Uremic Syndrome Panel
  17. Hypophosphatemic Rickets Panel
  18. Liddle Syndrome Panel
  19. Monogenic Obesity Panel
  20. Nephronophthisis Panel
  21. Polycystic Kidney Disease Panel
  22. Primary Hyperoxaluria Panel
  23. Renal Malformation Panel
  24. Senior-Loken Syndrome Panel
- **Status**: To be tested

## Blueprint Genetics Sub-panel URLs
```
https://blueprintgenetics.com/tests/panels/nephrology/alport-syndrome-panel
https://blueprintgenetics.com/tests/panels/nephrology/bartter-syndrome-panel
https://blueprintgenetics.com/tests/panels/nephrology/ciliopathy-panel
https://blueprintgenetics.com/tests/panels/nephrology/diabetes-insipidus-panel
https://blueprintgenetics.com/tests/panels/nephrology/hypomagnesemia-panel
https://blueprintgenetics.com/tests/panels/nephrology/joubert-syndrome-panel
https://blueprintgenetics.com/tests/panels/nephrology/meckel-syndrome-panel
https://blueprintgenetics.com/tests/panels/nephrology/nephrolithiasis-panel
https://blueprintgenetics.com/tests/panels/nephrology/nephrotic-syndrome-panel
https://blueprintgenetics.com/tests/panels/nephrology/primary-ciliary-dyskinesia-panel
https://blueprintgenetics.com/tests/panels/nephrology/pseudohypoaldosteronism-panel
https://blueprintgenetics.com/tests/panels/nephrology/renal-tubular-acidosis-panel
https://blueprintgenetics.com/tests/panels/nephrology/bardet-biedl-syndrome-panel
https://blueprintgenetics.com/tests/panels/nephrology/branchio-oto-renal-bor-syndrome-panel
https://blueprintgenetics.com/tests/panels/nephrology/cystic-kidney-disease-panel
https://blueprintgenetics.com/tests/panels/nephrology/hemolytic-uremic-syndrome-panel
https://blueprintgenetics.com/tests/panels/nephrology/hypophosphatemic-rickets-panel
https://blueprintgenetics.com/tests/panels/nephrology/liddle-syndrome-panel
https://blueprintgenetics.com/tests/panels/nephrology/monogenic-obesity-panel
https://blueprintgenetics.com/tests/panels/nephrology/nephronophthisis-panel
https://blueprintgenetics.com/tests/panels/nephrology/polycystic-kidney-disease-panel
https://blueprintgenetics.com/tests/panels/nephrology/primary-hyperoxaluria-panel
https://blueprintgenetics.com/tests/panels/nephrology/renal-malformation-panel
https://blueprintgenetics.com/tests/panels/nephrology/senior-loken-syndrome-panel
```

## Implementation Architecture

### Technology Stack (Planned)
- **Scraping Engine**: Playwright (Python) - replacing PhantomJS
- **Scheduling**: Celery with Redis or cron jobs
- **Error Handling**: Retry logic with exponential backoff
- **Data Format**: JSON following evidence schema
- **Storage**: Push to ingestion API endpoint

### Data Processing Pipeline
1. **Download**: Fetch HTML content using Playwright
2. **Extract**: Parse gene symbols using vendor-specific selectors
3. **Normalize**: Map to HGNC approved symbols
4. **Aggregate**: Count panel occurrences per gene
5. **Filter**: Apply evidence threshold (≥2 panels)
6. **Store**: Push to database via ingestion API

### Key Challenges
1. **Dynamic Content**: Many sites use JavaScript rendering
2. **Anti-Scraping**: Rate limiting, CAPTCHAs, user-agent detection
3. **Structure Changes**: HTML structure may change without notice
4. **Authentication**: Some sites may require login/registration
5. **Pagination**: Natera uses AJAX pagination requiring special handling

## URL Testing Results
*Tested on 2025-08-18*

| Website | Status | HTTP Code | Notes |
|---------|--------|-----------|-------|
| Centogene CentoNephro | ✅ Working | 200 | New URL confirmed: centoportal.com |
| CeGaT Kidney Diseases | ✅ Working | 200 | Accessible |
| PreventionGenetics | ✅ Working | 200 | Accessible |
| Invitae Progressive Panel | ✅ Working | 200 | Accessible |
| Invitae Expanded Panel | ✅ Working | 200 | Accessible |
| MGZ München | ✅ Working | 200 | Accessible |
| MVZ Medicover | ✅ Working | 200 | Accessible |
| Natera Renasight | ✅ Working | 200 | Accessible |
| Mayo Clinic Labs | ✅ Working* | 403/200 | Requires browser automation (Playwright) |
| Blueprint Genetics Main | ✅ Working | 200 | Accessible |
| Blueprint Sub-panels | ✅ Working | 200 | Tested 3 sub-panels, all accessible |

### Key Findings:
- **10 out of 10** main sites are accessible (100% success rate)
- **Centogene** has moved to new domain (centoportal.com) - now working with new URL
- **Mayo Clinic Labs** requires browser automation (Playwright/Selenium) due to Akamai protection
- **Blueprint Genetics** and all tested sub-panels are fully accessible
- Most sites return 200 OK with standard HTTP requests
- **UPDATE**: All sites are scrapable with appropriate tools (9 via HTTP, 1 via browser automation)

## Recommended Implementation Priority
1. **High Priority** (Most stable/important):
   - Blueprint Genetics (comprehensive panels)
   - Invitae (major US provider)
   - Natera Renasight (kidney-specific)

2. **Medium Priority**:
   - Centogene
   - PreventionGenetics
   - CeGaT

3. **Low Priority** (regional/specialized):
   - MGZ München
   - MVZ Medicover
   - Mayo Clinic Labs

## Next Steps
1. Test all URLs for current accessibility
2. Document any changes in website structure
3. Implement Playwright scrapers in Python
4. Create scheduling system for regular updates
5. Build error handling and monitoring
6. Integrate with ingestion API

## Notes from Original Implementation
- Uses PhantomJS for headless browsing (deprecated, needs replacement)
- Downloads HTML snapshots for reproducibility
- Implements gene symbol normalization via HGNC
- Filters genes with special characters (*,#,.)
- Computes percentile normalization for source counts

## Migration Considerations
- PhantomJS is deprecated; migrate to Playwright or Selenium
- Consider using official APIs where available
- Implement caching to reduce load on vendor sites
- Add user-agent rotation and request delays
- Consider legal/ethical implications of web scraping

## Implementation Architecture (Updated 2025-08-18)

### Directory Structure
```
kidney-genetics-db/
├── scrapers/
│   ├── diagnostics/
│   │   ├── __init__.py
│   │   ├── base_scraper.py          # Abstract base class for all scrapers
│   │   ├── schemas.py                # Pydantic models for data validation
│   │   ├── utils.py                  # Shared utilities (HGNC mapping, etc.)
│   │   ├── config.yaml               # Scraper configuration
│   │   │
│   │   ├── providers/                # One scraper per provider
│   │   │   ├── __init__.py
│   │   │   ├── blueprint_genetics.py # Handles all 24 sub-panels
│   │   │   ├── centogene.py         # Single panel
│   │   │   ├── cegat.py             # Single panel
│   │   │   ├── invitae.py           # Handles 2 panels
│   │   │   ├── mayo_clinic.py       # Single panel (requires Playwright)
│   │   │   ├── mgz_muenchen.py      # Single panel
│   │   │   ├── mvz_medicover.py     # Single panel
│   │   │   ├── natera.py            # Single panel with pagination
│   │   │   └── prevention_genetics.py # Single panel
│   │   │
│   │   ├── run_scrapers.py          # Main orchestration script
│   │   ├── requirements.txt         # Python dependencies
│   │   └── output/                  # JSON output files
│   │       └── 2025-08-18/
│   │           ├── blueprint_genetics.json  # Contains all 24 sub-panels
│   │           ├── centogene.json
│   │           ├── invitae.json            # Contains both panels
│   │           └── ...
```

### Uniform Output Schema

```python
# schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class EvidenceLevel(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNKNOWN = "unknown"

class SubPanel(BaseModel):
    """Sub-panel information (e.g., Blueprint Genetics sub-panels)"""
    name: str = Field(..., description="Sub-panel name")
    url: str = Field(..., description="Sub-panel URL")
    gene_count: int = Field(..., description="Number of genes in this sub-panel")
    genes: List[str] = Field(..., description="Gene symbols in this sub-panel")

class GeneEntry(BaseModel):
    """Individual gene entry from a diagnostic panel"""
    symbol: str = Field(..., description="Gene symbol as reported by source")
    hgnc_id: Optional[str] = Field(None, description="HGNC ID if resolved")
    approved_symbol: Optional[str] = Field(None, description="HGNC approved symbol")
    panels: List[str] = Field(..., description="Panel(s)/sub-panel(s) containing this gene")
    confidence: Optional[EvidenceLevel] = Field(EvidenceLevel.UNKNOWN)
    occurrence_count: int = Field(1, description="Number of panels containing this gene")
    additional_info: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ProviderData(BaseModel):
    """Complete data from a single diagnostic provider"""
    provider_id: str = Field(..., description="Unique identifier (e.g., 'blueprint_genetics')")
    provider_name: str = Field(..., description="Human-readable name")
    provider_type: str = Field(..., description="Type: single_panel or multi_panel")
    main_url: str = Field(..., description="Main provider URL")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    scraper_version: str = Field(default="1.0.0")
    
    # Panel information
    total_panels: int = Field(..., description="Total number of panels/sub-panels")
    sub_panels: Optional[List[SubPanel]] = Field(None, description="Sub-panel details if multi-panel")
    
    # Gene statistics
    total_unique_genes: int = Field(..., description="Total unique genes across all panels")
    genes: List[GeneEntry] = Field(..., description="All unique genes with panel info")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    errors: Optional[List[str]] = Field(default=None)
    
class DiagnosticPanelBatch(BaseModel):
    """Batch of all provider data ready for API ingestion"""
    batch_id: str = Field(..., description="Unique batch identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source_type: str = Field(default="diagnostic_panel")
    providers: List[ProviderData] = Field(..., description="All provider data")
    summary: Dict[str, Any] = Field(..., description="Batch summary statistics")
```

### Base Scraper Class

```python
# base_scraper.py
from abc import ABC, abstractmethod
from typing import List, Optional
import httpx
from playwright.sync_api import sync_playwright
import logging
from datetime import datetime
import json
from pathlib import Path

class BaseDiagnosticScraper(ABC):
    """Abstract base class for all diagnostic panel scrapers"""
    
    def __init__(self, config: dict):
        self.config = config
        self.source_id = self.__class__.__name__.lower().replace('scraper', '')
        self.logger = logging.getLogger(self.__class__.__name__)
        self.output_dir = Path(config.get('output_dir', 'output'))
        self.use_browser = False  # Override in child classes if needed
        
    @abstractmethod
    def extract_genes(self, content: str) -> List[GeneEntry]:
        """Extract gene list from HTML/JSON content"""
        pass
    
    @abstractmethod
    def get_panel_urls(self) -> List[dict]:
        """Return list of panel URLs to scrape"""
        pass
    
    def fetch_content(self, url: str) -> str:
        """Fetch content from URL using appropriate method"""
        if self.use_browser:
            return self._fetch_with_browser(url)
        else:
            return self._fetch_with_http(url)
    
    def _fetch_with_http(self, url: str) -> str:
        """Standard HTTP request"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = httpx.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    
    def _fetch_with_browser(self, url: str) -> str:
        """Browser automation for protected sites"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='networkidle')
            content = page.content()
            browser.close()
            return content
    
    def normalize_genes(self, genes: List[GeneEntry]) -> List[GeneEntry]:
        """Normalize gene symbols to HGNC approved symbols"""
        # Import HGNC resolver utility
        from utils import resolve_hgnc_symbol
        
        for gene in genes:
            hgnc_data = resolve_hgnc_symbol(gene.symbol)
            if hgnc_data:
                gene.hgnc_id = hgnc_data.get('hgnc_id')
                gene.approved_symbol = hgnc_data.get('approved_symbol')
        
        return genes
    
    def run(self) -> ScrapedPanel:
        """Main execution method"""
        self.logger.info(f"Starting scraper for {self.source_id}")
        
        all_genes = []
        errors = []
        panel_urls = self.get_panel_urls()
        
        for panel_info in panel_urls:
            try:
                content = self.fetch_content(panel_info['url'])
                genes = self.extract_genes(content)
                
                # Add panel name to each gene
                for gene in genes:
                    gene.panel_names = [panel_info['name']]
                
                all_genes.extend(genes)
                
            except Exception as e:
                self.logger.error(f"Error scraping {panel_info['url']}: {e}")
                errors.append(f"{panel_info['name']}: {str(e)}")
        
        # Normalize and deduplicate
        all_genes = self.normalize_genes(all_genes)
        unique_genes = self._deduplicate_genes(all_genes)
        
        # Create output
        result = ScrapedPanel(
            source_id=self.source_id,
            source_name=self.config.get('source_name', self.source_id),
            source_version=datetime.now().strftime('%Y%m%d'),
            url=self.config.get('base_url', ''),
            panel_count=len(panel_urls),
            gene_count=len(unique_genes),
            genes=unique_genes,
            metadata={
                'scraper_version': '1.0.0',
                'panels_scraped': [p['name'] for p in panel_urls]
            },
            errors=errors if errors else None
        )
        
        # Save output
        self.save_output(result)
        
        return result
    
    def save_output(self, data: ScrapedPanel):
        """Save scraped data to JSON file"""
        date_dir = self.output_dir / datetime.now().strftime('%Y-%m-%d')
        date_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = date_dir / f"{self.source_id}.json"
        with open(output_file, 'w') as f:
            json.dump(data.dict(), f, indent=2, default=str)
        
        self.logger.info(f"Saved output to {output_file}")
    
    def _deduplicate_genes(self, genes: List[GeneEntry]) -> List[GeneEntry]:
        """Merge duplicate genes and combine panel names"""
        gene_map = {}
        
        for gene in genes:
            key = gene.approved_symbol or gene.symbol
            if key in gene_map:
                # Merge panel names
                gene_map[key].panel_names.extend(gene.panel_names)
                gene_map[key].panel_names = list(set(gene_map[key].panel_names))
            else:
                gene_map[key] = gene
        
        return list(gene_map.values())
```

### Example Scraper Implementation

```python
# scrapers/blueprint_genetics.py
from bs4 import BeautifulSoup
from typing import List, Dict
from ..base_scraper import BaseDiagnosticScraper
from ..schemas import GeneEntry, SubPanel, ProviderData
import time

class BlueprintGeneticsScraper(BaseDiagnosticScraper):
    """Scraper for Blueprint Genetics - handles all 24 kidney sub-panels"""
    
    def __init__(self, config: dict):
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
        
        # Find the gene table
        gene_table = soup.find('table', class_='table mb-5')
        if gene_table:
            rows = gene_table.find_all('tr')[1:]  # Skip header
            for row in rows:
                cols = row.find_all('td')
                if cols:
                    gene_symbol = cols[0].text.strip()
                    # Clean gene symbol
                    gene_symbol = gene_symbol.replace('*', '').replace('#', '').strip()
                    if gene_symbol:
                        genes.append(gene_symbol)
        
        return genes
    
    def run(self) -> ProviderData:
        """Scrape all Blueprint Genetics sub-panels"""
        self.logger.info(f"Starting Blueprint Genetics scraper for {len(self.get_sub_panels())} sub-panels")
        
        sub_panels_data = []
        all_genes_dict = {}  # Track genes and which panels they appear in
        errors = []
        
        for panel_info in self.get_sub_panels():
            try:
                self.logger.info(f"Scraping {panel_info['name']}...")
                
                # Fetch content
                content = self.fetch_content(panel_info['url'])
                
                # Extract genes
                panel_genes = self.extract_genes_from_panel(content)
                
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
                
                # Rate limiting
                time.sleep(self.config.get('rate_limit', 2))
                
            except Exception as e:
                self.logger.error(f"Error scraping {panel_info['name']}: {e}")
                errors.append(f"{panel_info['name']}: {str(e)}")
        
        # Create gene entries with panel information
        gene_entries = []
        for gene_symbol, panel_names in all_genes_dict.items():
            # Normalize gene symbol (would call HGNC resolver here)
            gene_entry = GeneEntry(
                symbol=gene_symbol,
                panels=panel_names,
                occurrence_count=len(panel_names),
                confidence=self._calculate_confidence(len(panel_names))
            )
            gene_entries.append(gene_entry)
        
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
                ],
                'panels_scraped': len(sub_panels_data),
                'panels_failed': len(errors)
            },
            errors=errors if errors else None
        )
        
        # Save output
        self.save_output(provider_data)
        
        return provider_data
    
    def _calculate_confidence(self, occurrence_count: int) -> str:
        """Calculate confidence based on how many panels contain the gene"""
        if occurrence_count >= 10:
            return "high"
        elif occurrence_count >= 5:
            return "moderate"
        elif occurrence_count >= 2:
            return "low"
        return "unknown"
```

### Example Single-Panel Scraper

```python
# scrapers/mayo_clinic.py
from playwright.sync_api import sync_playwright
import re
from typing import List
from ..base_scraper import BaseDiagnosticScraper
from ..schemas import GeneEntry, ProviderData

class MayoClinicScraper(BaseDiagnosticScraper):
    """Scraper for Mayo Clinic Labs - single comprehensive panel"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.provider_id = "mayo_clinic"
        self.provider_name = "Mayo Clinic Labs"
        self.provider_type = "single_panel"
        self.use_browser = True  # Requires Playwright
        self.url = "https://www.mayocliniclabs.com/test-catalog/Overview/618086"
        
    def extract_genes(self) -> List[str]:
        """Extract genes using Playwright (due to Akamai protection)"""
        genes = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to the page
            page.goto(self.url)
            
            # Wait for content
            page.wait_for_selector('p:has-text("This test utilizes")', timeout=30000)
            
            # Extract gene paragraph
            gene_elements = page.query_selector_all('em')
            for elem in gene_elements:
                text = elem.inner_text()
                # Parse gene symbols from emphasized text
                if ',' in text:  # Likely a gene list
                    gene_list = text.split(',')
                    for gene in gene_list:
                        gene = gene.strip()
                        # Clean annotations
                        gene = re.sub(r'\[.*?\]', '', gene)
                        gene = re.sub(r'\(.*?\)', '', gene)
                        if gene and gene.upper() == gene:  # Gene symbols are uppercase
                            genes.append(gene)
            
            browser.close()
        
        return list(set(genes))  # Remove duplicates
    
    def run(self) -> ProviderData:
        """Run Mayo Clinic scraper"""
        self.logger.info("Starting Mayo Clinic scraper")
        
        errors = []
        try:
            genes = self.extract_genes()
            
            # Create gene entries
            gene_entries = [
                GeneEntry(
                    symbol=gene,
                    panels=["Comprehensive Nephrology Gene Panel"],
                    occurrence_count=1,
                    confidence="high"  # Mayo Clinic is a trusted source
                )
                for gene in genes
            ]
            
        except Exception as e:
            self.logger.error(f"Error scraping Mayo Clinic: {e}")
            errors.append(str(e))
            gene_entries = []
        
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
                'expected_gene_count': 302
            },
            errors=errors if errors else None
        )
        
        self.save_output(provider_data)
        return provider_data
```

### API Integration

```python
# run_scrapers.py
import asyncio
import httpx
from pathlib import Path
import json
from datetime import datetime
from typing import List
import yaml

async def push_to_api(batch_data: dict, api_config: dict):
    """Push scraped data to ingestion API"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_config['base_url']}/api/ingest/diagnostic-panels",
            json=batch_data,
            headers={
                "X-API-Key": api_config['api_key'],
                "Content-Type": "application/json"
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()

def main():
    """Run all scrapers and push to API"""
    # Load configuration
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    
    # Import all provider scrapers
    from providers import (
        BlueprintGeneticsScraper,
        CentogeneScraper,
        CegatScraper,
        InvitaeScraper,
        MayoClinicScraper,
        MGZMuenchenScraper,
        MVZMedicoverScraper,
        NateraScraper,
        PreventionGeneticsScraper
    )
    
    scraper_classes = [
        BlueprintGeneticsScraper,  # Multi-panel: 24 sub-panels
        CentogeneScraper,          # Single panel
        CegatScraper,              # Single panel
        InvitaeScraper,            # Multi-panel: 2 panels
        MayoClinicScraper,         # Single panel (Playwright)
        MGZMuenchenScraper,        # Single panel
        MVZMedicoverScraper,       # Single panel
        NateraScraper,             # Single panel (pagination)
        PreventionGeneticsScraper  # Single panel
    ]
    
    # Run all scrapers
    results = []
    for scraper_class in scraper_classes:
        try:
            print(f"Running {scraper_class.__name__}...")
            scraper = scraper_class(config.get('sources', {}).get(
                scraper_class.__name__.replace('Scraper', '').lower(), {}
            ))
            result = scraper.run()
            results.append(result)
            print(f"✓ {result.provider_name}: {result.total_unique_genes} genes from {result.total_panels} panel(s)")
        except Exception as e:
            print(f"✗ Error running {scraper_class.__name__}: {e}")
    
    # Calculate summary statistics
    total_panels = sum(r.total_panels for r in results)
    total_unique_genes_global = len(set(
        gene.symbol for r in results for gene in r.genes
    ))
    
    # Find genes in multiple providers
    gene_provider_map = {}
    for result in results:
        for gene in result.genes:
            if gene.symbol not in gene_provider_map:
                gene_provider_map[gene.symbol] = []
            gene_provider_map[gene.symbol].append(result.provider_name)
    
    multi_provider_genes = {
        gene: providers for gene, providers in gene_provider_map.items()
        if len(providers) >= 2
    }
    
    # Create batch for API
    batch = DiagnosticPanelBatch(
        batch_id=f"diagnostic-panels-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        providers=results,
        summary={
            "total_providers": len(results),
            "successful_providers": len([r for r in results if not r.errors]),
            "total_panels": total_panels,
            "total_unique_genes_global": total_unique_genes_global,
            "genes_in_multiple_providers": len(multi_provider_genes),
            "high_confidence_genes": len([
                g for g in multi_provider_genes 
                if len(multi_provider_genes[g]) >= 3
            ]),
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Push to API if configured
    if config.get('api', {}).get('enabled'):
        asyncio.run(push_to_api(batch.dict(), config['api']))
    
    # Save combined output
    output_file = Path('output') / f"combined_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, 'w') as f:
        json.dump(batch.dict(), f, indent=2, default=str)
    
    # Save summary report
    summary_file = Path('output') / f"summary_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(summary_file, 'w') as f:
        f.write("Diagnostic Panel Scraping Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Providers scraped: {len(results)}\n")
        f.write(f"Total panels: {total_panels}\n")
        f.write(f"Total unique genes: {total_unique_genes_global}\n")
        f.write(f"Genes in 2+ providers: {len(multi_provider_genes)}\n\n")
        
        f.write("Provider Details:\n")
        for r in results:
            f.write(f"- {r.provider_name}: {r.total_unique_genes} genes, {r.total_panels} panel(s)\n")
    
    print(f"\n✓ Scraping complete!")
    print(f"  Output: {output_file}")
    print(f"  Summary: {summary_file}")

if __name__ == "__main__":
    main()
```

### Configuration File

```yaml
# config.yaml
# Scraper configuration
output_dir: output
log_level: INFO

# API configuration
api:
  enabled: true
  base_url: http://localhost:8000
  api_key: ${DIAGNOSTIC_SCRAPER_API_KEY}

# Source-specific configurations
sources:
  blueprint_genetics:
    source_name: "Blueprint Genetics"
    base_url: "https://blueprintgenetics.com/tests/panels/nephrology/"
    rate_limit: 2  # seconds between requests
    
  centogene:
    source_name: "Centogene CentoNephro"
    base_url: "https://www.centoportal.com/order/new/products/analysis-method"
    
  mayo_clinic:
    source_name: "Mayo Clinic Labs"
    base_url: "https://www.mayocliniclabs.com/test-catalog/Overview/618086"
    use_browser: true  # Requires Playwright
    
  # ... other sources

# HGNC resolver configuration
hgnc:
  cache_enabled: true
  cache_ttl: 86400  # 24 hours
```

### Requirements

```txt
# requirements.txt
httpx>=0.24.0
beautifulsoup4>=4.12.0
playwright>=1.40.0
pydantic>=2.0.0
pyyaml>=6.0
lxml>=4.9.0
python-dotenv>=1.0.0
tenacity>=8.2.0  # For retry logic
```

### Deployment & Scheduling

```yaml
# docker-compose.scrapers.yml
version: '3.8'

services:
  diagnostic-scrapers:
    build:
      context: ./scrapers/diagnostics
      dockerfile: Dockerfile
    environment:
      - DIAGNOSTIC_SCRAPER_API_KEY=${DIAGNOSTIC_SCRAPER_API_KEY}
      - API_BASE_URL=${API_BASE_URL:-http://backend:8000}
    volumes:
      - ./scrapers/diagnostics/output:/app/output
    networks:
      - kidney-genetics-network
    command: python run_scrapers.py

  # Scheduled scraping with cron
  scraper-scheduler:
    image: mcuadros/ofelia:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./scrapers/config/schedule.ini:/etc/ofelia/config.ini
    networks:
      - kidney-genetics-network
```

### Schedule Configuration

```ini
# schedule.ini
[job-exec "diagnostic-panel-scraper"]
schedule = 0 0 1 * *  # Run monthly on the 1st
container = diagnostic-scrapers
command = python run_scrapers.py
```

## Testing Strategy

### Unit Tests
```python
# tests/test_scrapers.py
import pytest
from scrapers.blueprint_genetics import BlueprintGeneticsScraper

def test_blueprint_genetics_extraction():
    """Test gene extraction from sample HTML"""
    scraper = BlueprintGeneticsScraper({})
    sample_html = """
    <table class="table mb-5">
        <tr><th>Gene</th></tr>
        <tr><td>PKD1</td></tr>
        <tr><td>PKD2</td></tr>
    </table>
    """
    genes = scraper.extract_genes(sample_html)
    assert len(genes) == 2
    assert genes[0].symbol == "PKD1"
```

### Integration Tests
- Test each scraper against live sites (with rate limiting)
- Validate output schema compliance
- Test API ingestion endpoint

## Monitoring & Alerting

### Health Checks
- Monitor scraper success/failure rates
- Track changes in gene counts (detect website changes)
- Alert on repeated failures

### Logging
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scrapers.log'),
        logging.StreamHandler()
    ]
)
```

## Example Output Format

### Individual Provider Output (blueprint_genetics.json)
```json
{
  "provider_id": "blueprint_genetics",
  "provider_name": "Blueprint Genetics",
  "provider_type": "multi_panel",
  "main_url": "https://blueprintgenetics.com/tests/panels/nephrology/",
  "scraped_at": "2025-08-18T20:00:00Z",
  "scraper_version": "1.0.0",
  "total_panels": 24,
  "sub_panels": [
    {
      "name": "Polycystic Kidney Disease Panel",
      "url": "https://blueprintgenetics.com/tests/panels/nephrology/polycystic-kidney-disease-panel",
      "gene_count": 15,
      "genes": ["PKD1", "PKD2", "GANAB", "DNAJB11", ...]
    },
    {
      "name": "Alport Syndrome Panel",
      "url": "https://blueprintgenetics.com/tests/panels/nephrology/alport-syndrome-panel",
      "gene_count": 8,
      "genes": ["COL4A3", "COL4A4", "COL4A5", ...]
    }
  ],
  "total_unique_genes": 287,
  "genes": [
    {
      "symbol": "PKD1",
      "hgnc_id": "HGNC:9008",
      "approved_symbol": "PKD1",
      "panels": ["Polycystic Kidney Disease Panel", "Cystic Kidney Disease Panel"],
      "occurrence_count": 2,
      "confidence": "moderate"
    }
  ],
  "metadata": {
    "most_common_genes": [
      {"gene": "PKD1", "count": 2},
      {"gene": "PKD2", "count": 2}
    ],
    "panels_scraped": 24,
    "panels_failed": 0
  }
}
```

### Combined Batch Output (combined_20250818.json)
```json
{
  "batch_id": "diagnostic-panels-20250818-200000",
  "created_at": "2025-08-18T20:00:00Z",
  "source_type": "diagnostic_panel",
  "providers": [
    // ... all provider data objects
  ],
  "summary": {
    "total_providers": 9,
    "successful_providers": 9,
    "total_panels": 34,
    "total_unique_genes_global": 650,
    "genes_in_multiple_providers": 450,
    "high_confidence_genes": 320,
    "timestamp": "2025-08-18T20:00:00Z"
  }
}
```

## API Endpoint Specification

### Ingestion Endpoint
```yaml
endpoint: POST /api/ingest/diagnostic-panels
authentication: API Key (X-API-Key header)
content-type: application/json

request_body:
  type: DiagnosticPanelBatch
  
response:
  200 OK:
    {
      "status": "success",
      "batch_id": "diagnostic-panels-20250818-200000",
      "providers_processed": 9,
      "genes_ingested": 650,
      "message": "Diagnostic panel data successfully ingested"
    }
  
  400 Bad Request:
    {
      "status": "error",
      "message": "Invalid data format",
      "errors": ["..."]
    }
  
  401 Unauthorized:
    {
      "status": "error",
      "message": "Invalid API key"
    }
```

### Database Integration
The ingestion API will:
1. Validate incoming data against schema
2. Map gene symbols to existing HGNC records
3. Update or create diagnostic panel evidence records
4. Calculate evidence scores based on provider count
5. Trigger downstream aggregation pipelines

## Evidence Scoring Logic
```python
def calculate_evidence_score(gene_data):
    """
    Calculate evidence score for diagnostic panel source
    Based on number of providers listing the gene
    """
    provider_count = gene_data['provider_count']
    
    if provider_count >= 5:
        return 1.0  # Maximum score
    elif provider_count >= 3:
        return 0.8  # High confidence
    elif provider_count >= 2:
        return 0.6  # Moderate confidence (minimum threshold)
    else:
        return 0.3  # Low confidence (single provider)
```