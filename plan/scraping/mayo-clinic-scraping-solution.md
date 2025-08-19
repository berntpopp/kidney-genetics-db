# Mayo Clinic Labs Scraping Solution

## Problem
Mayo Clinic Labs (https://www.mayocliniclabs.com/test-catalog/Overview/618086) blocks standard HTTP requests with a 403 Forbidden error due to Akamai edge protection.

## Solution: Browser Automation with Playwright

### Working Method (Tested 2025-08-18)
```python
from playwright.sync_api import sync_playwright
import re

def scrape_mayo_clinic_panel():
    """
    Scrape Mayo Clinic Labs Comprehensive Nephrology Gene Panel
    Returns list of gene symbols
    """
    url = "https://www.mayocliniclabs.com/test-catalog/Overview/618086"
    
    with sync_playwright() as p:
        # Launch browser (headless mode works)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to the page
        page.goto(url)
        
        # Wait for content to load
        page.wait_for_selector('p:has-text("This test utilizes")')
        
        # Extract the gene list from the paragraph
        gene_paragraph = page.query_selector('p:has-text("This test utilizes")')
        gene_text = gene_paragraph.inner_text() if gene_paragraph else ""
        
        # Parse genes using regex
        # The genes are listed after "302 genes associated with hereditary kidney disease:"
        gene_pattern = r'disease:\s*(.*?)(?:See|$)'
        match = re.search(gene_pattern, gene_text, re.DOTALL)
        
        if match:
            gene_string = match.group(1)
            # Clean up the gene list
            # Remove annotations like [Chr22(GRCh37]:g.36661895-36661916...]
            gene_string = re.sub(r'\[.*?\]', '', gene_string)
            # Remove parenthetical aliases like (MCP) or (KATNIP)
            gene_string = re.sub(r'\([A-Z]+\)', '', gene_string)
            # Split by comma and clean
            genes = [g.strip() for g in gene_string.split(',') if g.strip()]
            # Remove any remaining special characters or empty strings
            genes = [g for g in genes if g and not g.startswith('.')]
            
            browser.close()
            return genes
        
        browser.close()
        return []
```

## Key Details

### Panel Information
- **Panel Name**: Comprehensive Nephrology Gene Panel (NEPHP)
- **Test ID**: NEPHP (618086)
- **Gene Count**: 302 genes
- **Coverage**: Hereditary kidney diseases including:
  - Focal segmental glomerulosclerosis
  - Alport syndrome
  - Polycystic kidney disease
  - Nephronophthisis
  - Bartter syndrome
  - And many others

### Technical Notes
1. **Akamai Protection**: The site uses Akamai edge services that detect and block non-browser requests
2. **User-Agent Not Sufficient**: Simply adding browser headers to curl/requests doesn't work
3. **JavaScript Required**: The page loads content dynamically
4. **Playwright Success**: Browser automation successfully bypasses all protections

### Gene List Location
The complete gene list is in a paragraph element that starts with:
> "This test utilizes next-generation sequencing to detect single nucleotide, deletion-insertion, and copy number variants in 302 genes associated with hereditary kidney disease:"

Followed by all 302 gene symbols separated by commas.

### Alternative Access Methods
1. **PDF Download**: The page offers a PDF download at:
   `https://www.mayocliniclabs.com/test-catalog/download-setup?format=pdf&unit_code=618086`
   (Also requires browser session)

2. **Detailed Gene List**: Additional documentation available at:
   `https://www.mayocliniclabs.com/-/media/it-mmfiles/Special%20Instructions/C/A/C/MC4091%20200%20TargetedGenesMethodologyComprehensiveNephGenePanel`

## Implementation Priority
Given the complexity of accessing Mayo Clinic's data, consider:
1. Implementing Playwright-based scraper specifically for this site
2. Caching results aggressively (data doesn't change frequently)
3. Consider reaching out to Mayo Clinic for official data access
4. As fallback, manual periodic updates may be more efficient

## Success Confirmation
✅ Successfully accessed on 2025-08-18 using Playwright
✅ Extracted 302 gene symbols
✅ Page fully loads with browser automation
✅ No CAPTCHA or additional authentication required