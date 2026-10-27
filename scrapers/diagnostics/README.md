# Diagnostic Panel Scrapers

A unified framework for extracting and normalizing kidney disease gene panel data from commercial and academic diagnostic providers. Features HGNC (HUGO Gene Nomenclature Committee) normalization and standardized JSON output for downstream analysis.

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

Statuses without a date are historical and have not been re-verified. Gene counts are not
kept here; read them from a dated `output/YYYY-MM-DD/<provider>.json` run.

| Provider | Type | Status |
|----------|------|--------|
| UChicago Genetic Services | Multi-panel (Nephrology category) | Verified 2026-10-27 (static HTML, see below) |
| Invitae | Single panel | Historical: working |
| Mayo Clinic | Single panel | Historical: working (Stealth) |
| Centogene | Single panel | Historical: configured |
| MGZ München | Single panel | Historical: configured |
| Natera RenaSight | Single panel | Historical: configured |
| Blueprint Genetics | Multi-panel (24) | Historical: configured |
| CeGaT | Single panel | Historical: configured |
| PreventionGenetics | Single panel | Historical: configured |
| MVZ Medicover | Single panel | Historical: configured |

### Provider Validation (2026-10-27)

Candidates from issue #1, checked with plain HTTP only (no login, CAPTCHA or ToS workaround).
Only a source with a public, attributable, static gene list was added.

| Candidate | Checked URL | Public kidney gene list? | robots.txt / terms | Verdict |
|-----------|-------------|--------------------------|--------------------|---------|
| UChicago Genetic Services | https://dnatesting.uchicago.edu/category/nephrology | Yes: static HTML panel pages with linked gene lists | `/category/` and `/tests/` allowed, `Crawl-delay: 10` (honoured); no site terms restricting access found | **Added** (`uchicago_genetics`) |
| GeneDx | https://www.genedx.com/test-catalog | No: static catalog lists exome/genome/targeted testing only; no kidney panel | Allowed (sitemap only) | Not usable |
| Fulgent Genetics | https://www.fulgentgenetics.com/ | No static list: AngularJS app; gene lists only via undocumented internal POST APIs | Allowed except order/login paths; terms PDF not reviewed | Blocked (no stable public source) |
| Ambry Genetics | https://ambrygen.com/genetic-testing-sitemap.xml | No kidney-disease panel (only an HLRCC cancer page) | `Disallow:` empty | Not usable |
| Myriad Genetics | https://myriad.com/page-sitemap.xml | No kidney/nephrology panel | Generic paths allowed; named AI crawlers blocked | Not usable |
| CHOP | https://www.chop.edu/ | No public kidney panel gene list found | Allowed for content paths | Not usable |
| Boston Children's | https://www.childrenshospital.org/ | Kidney genetics clinic page only; no gene list | Allowed for content paths | Not usable |

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
├── blueprint_genetics.json
├── uchicago_genetics.json
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
from schemas import GeneEntry, ProviderData

class NewProviderScraper(BaseDiagnosticScraper):
    def __init__(self, config=None):
        super().__init__(config, provider_id="new_provider")
        self.provider_name = "New Provider Name"
        self.provider_type = "single_panel"  # or "multi_panel"
        self.use_browser = False  # Set True for JavaScript sites
        
    def extract_genes(self, content: str) -> List[str]:
        # Parse HTML and return gene list
        soup = BeautifulSoup(content, 'html.parser')
        # Provider-specific extraction logic
        return genes
        
    def run(self) -> ProviderData:
        # Main execution - usually calls parent methods
        content = self.fetch_content(self.url)
        genes = self.extract_genes(content)
        # Create GeneEntry objects
        gene_entries = [GeneEntry(symbol=g, panels=["Panel Name"]) for g in genes]
        # Normalize via HGNC
        gene_entries = self.normalize_genes(gene_entries)
        # Return ProviderData
        return self.create_provider_data(gene_entries)
```

2. Add configuration to `config/config.yaml`:
```yaml
scrapers:
  new_provider:
    enabled: true
    url: "https://newprovider.com/kidney-panel"
```

3. Register in `run_scrapers.py`:
```python
from providers.new_provider import NewProviderScraper
# Add to scraper_classes list
('new_provider', NewProviderScraper)
```

### Tests

```bash
python -m pytest tests/   # offline: mocked HGNC, captured HTML fixtures in tests/fixtures/
```

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

### Core Components

- **Base Scraper** (`base_scraper.py`): Abstract base class providing:
  - HTTP and browser automation (Playwright)
  - HGNC gene symbol normalization
  - Raw data caching for debugging
  - Rate limiting and error handling
  
- **Provider Scrapers** (`providers/*.py`): Concrete implementations for each provider
  - Extract genes using provider-specific patterns
  - Handle pagination, AJAX, and JavaScript rendering
  - Support both single and multi-panel providers

- **HGNC Normalizer** (`utils.py`): Gene symbol standardization
  - Maps provider symbols to official HGNC symbols
  - 3-tier lookup: current → previous → alias symbols
  - File-based caching with 30-day TTL
  - Batch processing for efficiency

- **Schemas** (`schemas.py`): Data structures using Python dataclasses
  - No external dependencies (no Pydantic)
  - Type hints for validation
  - JSON serialization support

## HGNC Normalization

### Process Flow
1. Extract raw gene symbols from provider
2. Batch normalize via HGNC REST API
3. Try lookups in order: current → previous → alias
4. Cache all results (including negatives)
5. Update gene entries with normalized data

### Gene Entry Schema
```python
@dataclass
class GeneEntry:
    symbol: str                    # HGNC-approved symbol (or reported if not found)
    panels: List[str]              # Associated panel names
    occurrence_count: int = 1      # Times gene appears
    reported_as: Optional[str]     # Original symbol as reported by provider
    hgnc_id: Optional[str]         # HGNC identifier (e.g., "HGNC:12345")
    normalization_status: str      # "normalized" (found in HGNC), "not_found", "ambiguous"
                                   # (several HGNC candidates; symbol kept as reported) or
                                   # "hgnc_unavailable" (HGNC request failed; retried next run)
```

### Example Normalizations
- `G6PC` → `G6PC1` (HGNC:4056)
- `MUT` → `MMUT` (HGNC:7526)
- `SLC9A3R1` → `NHERF1` (HGNC:11075)

### Cache Performance
- First run: ~400 API calls for 400 genes
- Subsequent runs: 0 API calls (100% cache hit rate)
- Cache location: `data/hgnc_cache/`
- TTL: 30 days

## Technology Stack

- **Python 3.8+**: Core language
- **BeautifulSoup4**: HTML parsing
- **Playwright**: Browser automation for JavaScript sites
- **Playwright Stealth**: Anti-bot bypass (Akamai)
- **urllib**: Synchronous HTTP requests
- **YAML**: Configuration management
- **JSON**: Output format
- **Dataclasses**: Schema definition

## Provider-Specific Strategies

### Standard HTTP (Most Providers)
Direct HTTP requests for static HTML content

### Browser Automation (JavaScript Sites)
Playwright for dynamic content requiring client-side rendering

### AJAX/API Endpoints (Natera)
Direct API calls with pagination handling

### Anti-Bot Protection (Mayo Clinic)
Playwright Stealth with browser fingerprint masking

## Configuration Details

All URLs and settings centralized in `config/config.yaml`:
- No hardcoded URLs in scraper code
- Provider-specific parameters
- Enable/disable flags
- Rate limiting settings

Rate limited to 2 seconds between requests. All scrapers save raw HTML to `data/` for debugging.