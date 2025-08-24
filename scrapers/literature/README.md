# Literature Scraper for Kidney Genetics Database

## Overview
Python-based literature scraping system that extracts gene symbols from scientific publications (PDF, DOCX, Excel, ZIP) for the kidney genetics database. This replaces the original R-based pipeline with a modern, maintainable Python implementation.

## Features
- **Multi-format support**: PDF, DOCX, Excel, ZIP archives
- **Publication-specific processors**: Custom extraction logic for each publication
- **HGNC normalization**: Automatic gene symbol normalization via HGNC API
- **Batch processing**: Efficient processing of multiple publications
- **Structured output**: JSON output matching diagnostic scraper schemas
- **Comprehensive logging**: Detailed logging for debugging and monitoring

## Installation

```bash
# Install dependencies using UV
uv sync

# Or using pip
pip install -r requirements.txt
```

## Usage

### Quick Start
```bash
# Run the complete pipeline
uv run python run_literature_scraper.py
```

### Test Individual Processors
```bash
# Test first processor only
uv run python test_first_processor.py

# Test multiple processors
uv run python test_processors.py
```

## Output Structure

The scraper generates output in `output/<date>/literature.json` with the following structure:

```json
{
  "provider_id": "literature",
  "provider_type": "literature",
  "total_panels": 12,
  "total_unique_genes": 826,
  "genes": [
    {
      "symbol": "ABCC6",
      "panels": ["PMID_35325889", "PMID_30476936"],
      "occurrence_count": 2,
      "confidence": "medium",
      "hgnc_id": "HGNC:57",
      "approved_symbol": "ABCC6",
      "reported_symbol": "ABCC6"
    }
  ],
  "publications": [
    {
      "pmid": "35325889",
      "name": "Genetic Etiologies for Chronic Kidney Disease",
      "authors": "Anthony J. Bleyer",
      "gene_count": 381,
      "file_type": "docx"
    }
  ]
}
```

## Architecture

### Directory Structure
```
scrapers/literature/
├── base_literature_scraper.py  # Base scraper class
├── literature_scraper.py       # Main scraper implementation
├── extractors/                 # File type extractors
│   ├── docx_extractor.py
│   ├── excel_extractor.py
│   ├── pdf_extractor.py
│   └── zip_extractor.py
├── processors/                 # Publication-specific processors
│   ├── pmid_35325889.py      # Individual processors
│   └── ...
├── schemas.py                  # Data models
├── utils.py                    # Utilities (HGNC normalization)
├── config/                     # Configuration
│   └── config.yaml
├── data/                       # Input data
│   ├── downloads/             # Publication files
│   └── *.xlsx                 # Metadata
└── output/                     # Results
```

### Processing Pipeline
1. **Load metadata** from Excel file listing all publications
2. **Process each publication** using specific processor
3. **Extract genes** based on publication-specific patterns
4. **Aggregate genes** across all publications
5. **Normalize symbols** via HGNC API
6. **Generate output** in structured JSON format

## Publications Processed

| PMID | Title | Type | Genes |
|------|-------|------|-------|
| 35325889 | Genetic Etiologies for Chronic Kidney Disease | DOCX | 381 |
| 34264297 | Genetic testing in chronic kidney disease | ZIP | 21 |
| 36035137 | Analysis of chronic kidney disease patients | Excel | 100 |
| 33664247 | Australia and New Zealand renal gene panel | PDF | 215 |
| 30476936 | The Burden of Candidate Pathogenic Variants | Excel | 623 |
| 31509055 | Autosomal dominant tubulointerstitial kidney disease | PDF | 226 |
| 31822006 | Utility of Genomic Testing after Renal Biopsy | PDF | 212 |
| 29801666 | A kidney-disease gene panel | DOCX | 140 |
| 31027891 | Value of renal gene panel diagnostics | DOCX | 213 |
| 26862157 | Genetic spectrum of Saudi Arabian patients | PDF | 86 |
| 33532864 | Clinical utility of genetic testing | DOCX | 316 |
| 35005812 | Targeted next-generation sequencing | Excel | 151 |

## Configuration

Edit `config/config.yaml` to customize:
- Output directory
- Logging level
- HGNC cache settings
- Processing options

## Development

### Adding New Processors
1. Create new processor in `processors/` directory
2. Inherit from `BaseProcessor` class
3. Implement `process()` method
4. Add mapping in `literature_scraper.py`

### Testing
```bash
# Run tests for specific processor
uv run python -c "from processors.pmid_35325889 import PMID35325889Processor; ..."
```

## Performance
- Processes 12 publications in ~2 minutes
- Extracts 826 unique genes with 98% HGNC mapping
- Caches HGNC lookups for efficiency

## Requirements
- Python 3.8+
- See `pyproject.toml` for dependencies