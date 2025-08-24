# Literature Scraper for Kidney Genetics Database

## Overview
Python-based literature scraping system that extracts gene symbols from scientific publications (PDF, DOCX, Excel, ZIP) for the kidney genetics database. This replaces the original R-based pipeline with a modern, maintainable Python implementation.

## Features
- **Multi-format support**: PDF, DOCX, Excel, ZIP archives
- **Publication-specific processors**: Custom extraction logic for each publication
- **HGNC normalization**: Automatic gene symbol normalization via HGNC API
- **Batch processing**: Efficient processing of multiple publications
- **Individual outputs**: Each publication generates its own JSON file
- **Comprehensive logging**: Detailed logging for debugging and monitoring

## Installation

```bash
# Navigate to the literature scraper directory
cd scrapers/literature

# Install dependencies using UV (recommended)
uv sync

# Or create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### Quick Start
```bash
# Process all publications
uv run python run_literature_scraper.py

# Process all publications with detailed logging
uv run python run_literature_scraper.py --log-level DEBUG
```

### Command Line Options
```bash
# See all available options
uv run python run_literature_scraper.py --help

# Process a single publication by PMID
uv run python run_literature_scraper.py --pmid 35325889

# Dry run - see what would be processed without running
uv run python run_literature_scraper.py --dry-run

# Use custom configuration
uv run python run_literature_scraper.py --config path/to/config.yaml

# Adjust logging level
uv run python run_literature_scraper.py --log-level DEBUG
```

## Output Structure

The scraper generates individual JSON files for each publication in `output/<date>/` directory:
- `literature_pmid_XXXXX.json` - Individual publication data
- `literature_summary.json` - Summary of all processed publications

Each publication file has the following structure:

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
├── base_literature_scraper.py        # Base scraper class with common functionality
├── literature_scraper_individual.py  # Main scraper for individual publication processing
├── run_literature_scraper.py         # Command-line entry point
├── extractors/                       # File type extractors
│   ├── docx_extractor.py
│   ├── excel_extractor.py
│   ├── pdf_extractor.py
│   └── zip_extractor.py
├── processors/                       # Publication-specific processors
│   ├── base_processor.py            # Base processor class
│   ├── filters.py                   # Gene symbol filtering utilities
│   ├── pmid_35325889.py            # Individual processor for specific PMID
│   ├── pmid_33664247.py
│   ├── pmid_34264297.py
│   ├── pmid_36035137.py
│   └── remaining_processors.py     # Processors for multiple PMIDs
├── schemas.py                       # Data models (GeneEntry, Publication, LiteratureData)
├── utils.py                         # HGNC normalization and utilities
├── config/                          # Configuration
│   └── config.yaml
├── data/                           # Input data
│   ├── 230220_Kidney_Genes_Publication_List.xlsx  # Publication metadata
│   ├── downloads/                  # Publication files (PDF, DOCX, Excel, ZIP)
│   └── hgnc_cache/                # HGNC API cache
├── logs/                           # Processing logs
└── output/                         # Results by date
    └── YYYY-MM-DD/
        ├── literature_pmid_*.json  # Individual publication results
        └── literature_summary.json # Summary of all processed publications
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

## Execution Results

The scraper successfully processes 12 out of 16 publications (4 lack processors for NA file types):
- **Total genes extracted**: 2,947 across all publications
- **Unique genes identified**: 820 distinct gene symbols
- **HGNC normalization**: 100% success rate with efficient caching
- **Processing time**: ~3 seconds for all publications
- **Cache efficiency**: 823 cache hits vs 9 API calls

## Performance
- Processes 12 publications in ~3 seconds
- Extracts 820 unique genes with 100% HGNC mapping
- Efficient caching reduces API calls by 99%
- Individual JSON output for each publication enables parallel processing

## Requirements
- Python 3.8+
- See `pyproject.toml` for dependencies