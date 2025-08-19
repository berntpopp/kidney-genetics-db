# Diagnostic Panel Scraping - Implementation Guide

## Quick Start

### 1. Setup Environment
```bash
cd scrapers/diagnostics
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install chromium  # For Mayo Clinic scraping
```

### 2. Configure Scrapers
Edit `config.yaml`:
```yaml
api:
  enabled: false  # Set to true for production
  base_url: http://localhost:8000
  api_key: your-api-key-here

sources:
  blueprint_genetics:
    rate_limit: 2  # seconds between requests
  mayo_clinic:
    use_browser: true
```

### 3. Run Scrapers
```bash
# Run all scrapers
python run_scrapers.py

# Run specific provider (example)
python -m providers.blueprint_genetics

# Check output
ls output/2025-08-18/
```

## Provider Implementation Status

| Provider | Script | Panels | Special Requirements |
|----------|--------|--------|---------------------|
| Blueprint Genetics | `blueprint_genetics.py` | 24 sub-panels | Rate limiting |
| Centogene | `centogene.py` | 1 panel | New URL (centoportal.com) |
| CeGaT | `cegat.py` | 1 panel | None |
| Invitae | `invitae.py` | 2 panels | Meta tag parsing |
| Mayo Clinic | `mayo_clinic.py` | 1 panel | **Playwright required** |
| MGZ München | `mgz_muenchen.py` | 1 panel | None |
| MVZ Medicover | `mvz_medicover.py` | 1 panel | None |
| Natera | `natera.py` | 1 panel | AJAX pagination |
| PreventionGenetics | `prevention_genetics.py` | 1 panel | None |

## Output Files

### Individual Provider Output
```
output/2025-08-18/
├── blueprint_genetics.json  # 24 sub-panels, ~287 genes
├── centogene.json          # 1 panel
├── mayo_clinic.json        # 302 genes
└── ...
```

### Combined Output
```
output/
├── combined_20250818.json    # All provider data
└── summary_20250818.txt      # Human-readable summary
```

## JSON Structure

### Provider with Sub-panels (Blueprint)
```json
{
  "provider_id": "blueprint_genetics",
  "provider_type": "multi_panel",
  "total_panels": 24,
  "sub_panels": [
    {
      "name": "Alport Syndrome Panel",
      "genes": ["COL4A3", "COL4A4", "COL4A5"]
    }
  ],
  "genes": [
    {
      "symbol": "COL4A3",
      "panels": ["Alport Syndrome Panel"],
      "occurrence_count": 1
    }
  ]
}
```

### Single Panel Provider (Mayo)
```json
{
  "provider_id": "mayo_clinic",
  "provider_type": "single_panel",
  "total_panels": 1,
  "sub_panels": null,
  "total_unique_genes": 302,
  "genes": [...]
}
```

## API Integration

### Manual Upload
```bash
curl -X POST http://localhost:8000/api/ingest/diagnostic-panels \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d @output/combined_20250818.json
```

### Automatic Upload
Set `api.enabled: true` in config.yaml

## Testing Individual Scrapers

```python
# test_blueprint.py
from providers.blueprint_genetics import BlueprintGeneticsScraper

config = {
    'rate_limit': 2,
    'output_dir': 'test_output'
}

scraper = BlueprintGeneticsScraper(config)
result = scraper.run()
print(f"Found {result.total_unique_genes} genes across {result.total_panels} panels")
```

## Troubleshooting

### Mayo Clinic 403 Error
- Ensure Playwright is installed: `playwright install chromium`
- Check browser automation works: `python -m providers.mayo_clinic`

### Empty Gene Lists
- Check HTML structure hasn't changed
- Verify CSS selectors/XPath expressions
- Enable debug logging in config

### Rate Limiting
- Increase `rate_limit` in config.yaml
- Add retry logic with exponential backoff

## Evidence Scoring

Genes are scored based on provider occurrence:
- **5+ providers**: Score 1.0 (maximum)
- **3-4 providers**: Score 0.8 (high confidence)
- **2 providers**: Score 0.6 (moderate, minimum threshold)
- **1 provider**: Score 0.3 (low confidence)

## Monthly Update Schedule

Add to crontab:
```bash
0 0 1 * * cd /path/to/scrapers/diagnostics && python run_scrapers.py
```

Or use Docker + Ofelia for container-based scheduling.

## Development Workflow

1. **Add New Provider**:
   - Create `providers/new_provider.py`
   - Inherit from `BaseDiagnosticScraper`
   - Implement `extract_genes()` method
   - Add to `run_scrapers.py`

2. **Update Existing Provider**:
   - Check current HTML structure
   - Update extraction logic
   - Test with sample HTML
   - Verify output schema

3. **Debug Scraper**:
   - Enable debug logging
   - Save HTML snapshots
   - Test extraction separately
   - Compare with expected output

## Contact & Support

For issues or questions:
- Check `/plan/scraping/diagnostic-panels-scraping-plan.md` for detailed specs
- Review error logs in `scrapers.log`
- Verify URLs are still accessible