# Diagnostic Panel Scrapers

Web scrapers for extracting kidney disease gene data from diagnostic panel providers.

## Quick Start

```bash
# Run all scrapers with default configuration
python3 run_scrapers.py

# Run specific provider only
python3 run_scrapers.py --provider blueprint_genetics

# Preview what would run without executing  
python3 run_scrapers.py --dry-run
```

## Supported Providers

| Provider | Genes | Type | Status |
|----------|-------|------|--------|
| Centogene | 493 | Single panel | ✅ Working |
| MGZ München | 481 | Single panel | ✅ Working |  
| Natera RenaSight | 407 | Single panel | ✅ Working |
| Invitae | 400 | Single panel | ✅ Working |
| Blueprint Genetics | 370 | Multi-panel (24 panels) | ✅ Working |
| CeGaT | 336 | Single panel | ✅ Working |
| PreventionGenetics | 330 | Single panel | ✅ Working |
| Mayo Clinic | 303 | Single panel | ✅ Working (Stealth) |
| MVZ Medicover | 125 | Single panel | ✅ Working |

## Configuration

All settings are in `config/config.yaml`:

```yaml
scrapers:
  blueprint_genetics:
    enabled: true
    panels:
      - name: "Alport Syndrome Panel"
        url_suffix: "alport-syndrome-panel"
      # ... 23 more panels
```

To disable a scraper, set `enabled: false`.

## Output

Results saved to:
```
output/YYYY-MM-DD/
├── blueprint_genetics.json    # 370 genes from 24 panels
├── natera.json               # 407 genes  
├── invitae.json              # 400 genes
└── ...
```

Each JSON contains:
- `provider_name`: Provider identifier
- `total_unique_genes`: Gene count
- `genes[]`: Array of gene symbols with metadata
- `sub_panels[]`: Sub-panel info (multi-panel providers)

## Development

### Add New Provider

1. Create `providers/new_provider.py`:
```python
from base_scraper import BaseDiagnosticScraper

class NewProviderScraper(BaseDiagnosticScraper):
    def __init__(self, config=None):
        super().__init__(config)
        self.provider_id = "new_provider"
        
    def extract_genes_from_panel(self, content):
        # Parse HTML/JSON and return gene list
        return ["GENE1", "GENE2"]
```

2. Add to `providers/__init__.py`
3. Add configuration to `config/config.yaml`

### Debug Individual Scrapers

```bash
python3 providers/blueprint_genetics.py   # Direct execution
python3 run_scrapers.py --provider natera  # Via orchestrator
```

Raw HTML data saved to `data/provider_name/` for debugging.

## Mayo Clinic Akamai Bypass

Mayo Clinic uses advanced Akamai protection that blocks standard automation. We bypass this using **Playwright Stealth**:

```python
# Mayo Clinic specific implementation
from playwright_stealth import Stealth

stealth = Stealth(
    navigator_languages_override=("en-US", "en"),
    init_scripts_only=True
)

# Advanced browser args to avoid detection
args = [
    "--disable-blink-features=AutomationControlled",
    "--disable-web-security", 
    "--no-default-browser-check"
]
```

**Dependencies**: `pip install playwright-stealth && playwright install chromium`

## Architecture

- **Base**: `BaseDiagnosticScraper` handles HTTP/browser automation, rate limiting, output
- **Providers**: Individual scrapers inherit base and implement `extract_genes_from_panel()`  
- **Schemas**: Data structures in `schemas.py` (no Pydantic dependency)
- **Utils**: Gene symbol cleaning and validation in `utils.py`

Rate limited to 2 seconds between requests. All scrapers save raw data for debugging.