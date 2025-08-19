# Diagnostic Panel Scrapers

Web scrapers for extracting kidney disease gene panels from diagnostic laboratory websites.

## Overview

This module provides automated extraction of gene lists from various diagnostic providers offering kidney disease genetic testing panels. The scrapers are designed to be modular, maintainable, and robust.

## Features

- **Modular Architecture**: Base scraper class with provider-specific implementations
- **Multiple Extraction Methods**: HTTP requests and browser automation (Playwright)
- **Data Validation**: Gene symbol cleaning and validation
- **Structured Output**: JSON output with consistent schema
- **Error Handling**: Comprehensive error logging and recovery

## Directory Structure

```
scrapers/diagnostics/
├── base_scraper.py        # Abstract base class for all scrapers
├── schemas_simple.py       # Data models using dataclasses
├── utils.py               # Shared utility functions
├── providers/             # Provider-specific scrapers
│   ├── natera.py         # Natera Renasight panel
│   ├── mayo_clinic.py    # Mayo Clinic Labs
│   ├── mvz_medicover.py  # MVZ Medicover
│   └── ...               # Other providers
├── config/               # Configuration files
├── output/               # Scraped data (JSON)
├── data/                 # Temporary data files
├── logs/                 # Scraper logs
└── tests/               # Unit and integration tests
```

## Installation

### Basic Setup (HTTP-only scrapers)

```bash
# Install required Python packages
pip install beautifulsoup4
```

### Full Setup (including browser automation)

```bash
# Install all dependencies
pip install beautifulsoup4 playwright

# Install browser for Playwright
playwright install chromium
```

## Usage

### Running Individual Scrapers

```python
from providers.natera import NateraScraper

# Initialize and run scraper
scraper = NateraScraper()
result = scraper.run()

print(f"Found {result.total_unique_genes} genes")
```

### Running All Scrapers

```python
import run_scrapers

# Run all configured scrapers
results = run_scrapers.main()
```

## Providers

### Working Scrapers

| Provider | Status | Method | Genes | Notes |
|----------|--------|--------|-------|-------|
| Natera | ✅ Working | AJAX API | 407 | Pagination through 41 pages |
| MGZ München | ✅ Working | HTTP | 481 | Simple HTML parsing |
| MVZ Medicover | ✅ Working | Browser | 125 | Extracts from embedded JSON |
| CeGaT | ⚠️ Partial | HTTP | 336 | Genes may be in PDF |
| Invitae | ✅ Working | HTTP | ~350 | Multiple panels |
| Centogene | ✅ Working | HTTP | ~600 | 8 sub-panels |

### Scrapers Needing Fixes

- **PreventionGenetics**: JavaScript loading issues (only 2 genes found)
- **Mayo Clinic**: Akamai protection (0 genes extracted)

## Configuration

### Scraper Configuration (config/config.yaml)

```yaml
scrapers:
  rate_limit: 2  # Seconds between requests
  output_dir: "output"
  use_cache: false
  
providers:
  natera:
    enabled: true
    url: "https://www.natera.com/..."
```

### Environment Variables

```bash
# Optional: Set output directory
export SCRAPER_OUTPUT_DIR="/path/to/output"

# Optional: Enable debug logging
export LOG_LEVEL="DEBUG"
```

## Development

### Adding a New Scraper

1. Create a new file in `providers/`
2. Extend `BaseDiagnosticScraper`
3. Implement the `run()` method
4. Add extraction logic

Example:

```python
from base_scraper import BaseDiagnosticScraper
from schemas_simple import GeneEntry, ProviderData

class NewProviderScraper(BaseDiagnosticScraper):
    def __init__(self, config=None):
        super().__init__(config)
        self.provider_id = "new_provider"
        self.url = "https://example.com/panel"
        
    def run(self) -> ProviderData:
        # Implement scraping logic
        pass
```

### Testing

```bash
# Run unit tests
python -m pytest tests/unit/

# Run integration tests
python -m pytest tests/integration/

# Test individual scraper
python providers/natera.py
```

### Code Quality

```bash
# Format code with black
black .

# Lint with ruff
ruff check .

# Type checking
mypy .
```

## Output Format

Scrapers produce JSON files with the following structure:

```json
{
  "provider_id": "natera",
  "provider_name": "Natera",
  "provider_type": "single_panel",
  "main_url": "https://...",
  "total_panels": 1,
  "total_unique_genes": 407,
  "genes": [
    {
      "symbol": "PKD1",
      "panels": ["Renasight"],
      "occurrence_count": 1,
      "confidence": "high",
      "hgnc_id": null,
      "approved_symbol": "PKD1"
    }
  ],
  "metadata": {
    "panel_name": "Renasight",
    "scraper_version": "1.0.0"
  },
  "scraped_at": "2025-08-19T08:00:00"
}
```

## Troubleshooting

### Common Issues

1. **"Playwright not installed"**
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. **Rate limiting errors**
   - Increase `rate_limit` in config
   - Add retry logic with exponential backoff

3. **No genes found**
   - Check if website structure changed
   - Verify URL is correct
   - Check browser console for JavaScript errors

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

scraper = NateraScraper()
result = scraper.run()
```

## License

This project is part of the kidney-genetics-db system.

## Contributing

1. Follow the existing code style
2. Add tests for new scrapers
3. Update documentation
4. Lint code before committing