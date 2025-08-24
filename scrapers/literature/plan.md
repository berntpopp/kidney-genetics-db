# Literature Scraping Implementation Plan

## Overview
Implement Python-based literature scraping functionality to extract gene symbols from scientific publications (PDF, DOCX, Excel) for the kidney genetics database, replicating the functionality from the R-based pipeline.

## Current State Analysis

### Existing Assets
1. **Data Sources** (`data/downloads/`)
   - 13 publication files: PDF (4), DOCX (4), Excel (3), ZIP (1), NA (1)
   - PMIDs: 35325889, 34264297, 36035137, 33664247, 30476936, 31027891, 31509055, 31822006, 29801666, 31027891, 26862157, 33532864, 35005812
   - Already downloaded and available for processing

2. **Metadata** (`data/230220_Kidney_Genes_Publication_List.xlsx`)
   - Contains publication metadata: PMID, Name, Authors, Type, Download links
   - Maps publications to their respective file types and extraction methods

3. **Reference Implementation** (`../kidney-genetics-v1/analyses/02_Literature/02_Literature.R`)
   - R script showing extraction patterns for each publication
   - Gene normalization via HGNC
   - Evidence scoring and aggregation logic

4. **Existing Infrastructure** (`scrapers/diagnostics/`)
   - Base scraper architecture with normalization
   - HGNC gene normalization utilities
   - Structured output schemas
   - Caching and error handling patterns

## Architecture Design

### Directory Structure
```
scrapers/literature/
├── __init__.py
├── base_literature_scraper.py     # Base class for literature extraction
├── extractors/
│   ├── __init__.py
│   ├── pdf_extractor.py           # PDF text extraction
│   ├── docx_extractor.py          # DOCX content extraction
│   ├── excel_extractor.py         # Excel data extraction
│   └── zip_extractor.py           # ZIP file handling
├── processors/
│   ├── __init__.py
│   ├── pmid_35325889.py          # Publication-specific processors
│   ├── pmid_34264297.py
│   ├── pmid_36035137.py
│   ├── pmid_33664247.py
│   ├── pmid_30476936.py
│   ├── pmid_31509055.py
│   ├── pmid_31822006.py
│   ├── pmid_29801666.py
│   ├── pmid_31027891.py
│   ├── pmid_26862157.py
│   ├── pmid_33532864.py
│   └── pmid_35005812.py
├── schemas.py                     # Data models
├── utils.py                       # Shared utilities
├── run_literature_scraper.py      # Main execution script
├── config/
│   └── config.yaml               # Configuration settings
├── data/                         # Input data (existing)
│   ├── downloads/               # Publication files
│   └── 230220_Kidney_Genes_Publication_List.xlsx
└── output/                      # Structured output
```

## Implementation Components

### 1. Base Literature Scraper
```python
class BaseLiteratureScraper:
    """Base class for literature extraction"""
    - Load publication metadata from Excel
    - Coordinate extraction and processing
    - Handle HGNC normalization
    - Generate structured output
```

### 2. File Type Extractors

#### PDF Extractor
- **Library**: `pdfplumber` or `pypdf2` + `pdfminer.six`
- **Features**:
  - Text extraction with layout preservation
  - Table detection and extraction
  - Handle multi-page documents
  - Special handling for supplementary tables

#### DOCX Extractor  
- **Library**: `python-docx`
- **Features**:
  - Paragraph text extraction
  - Table data extraction
  - Cell-by-cell processing for structured data
  - Handle track changes and comments

#### Excel Extractor
- **Library**: `openpyxl` or `pandas`
- **Features**:
  - Sheet selection and navigation
  - Header detection and skipping
  - Column-specific extraction
  - Handle merged cells and formulas

#### ZIP Extractor
- **Library**: `zipfile`
- **Features**:
  - Archive listing and extraction
  - Recursive processing of contained files
  - Temporary file management

### 3. Publication-Specific Processors

Each processor implements custom logic based on the R script patterns:

#### Example: PMID_35325889 Processor (DOCX)
```python
class PMID35325889Processor:
    def process(self, content):
        # Extract text containing "ABCC6" pattern
        # Split by ", " separator
        # Return unique gene list
```

#### Example: PMID_33664247 Processor (PDF)
```python
class PMID33664247Processor:
    def process(self, content):
        # Skip first 15 lines
        # Apply complex filtering rules
        # Remove specific non-gene strings
        # Clean underscore suffixes
```

### 4. Gene Processing Pipeline

#### Text Cleaning
- Remove special characters and formatting
- Handle various separators (comma, space, newline)
- Strip prefixes/suffixes (e.g., "*", "(", numbers)
- Convert case variations (orf → ORF)

#### Gene Symbol Validation
- Length constraints (2-15 characters)
- Pattern matching (uppercase alphanumeric)
- Exclude common false positives
- Filter noise words and phrases

#### HGNC Normalization
- Batch API calls for efficiency
- Cache results locally
- Handle symbol aliases and previous symbols
- Track unmapped genes for review

### 5. Output Schema

```python
@dataclass
class LiteratureGene:
    approved_symbol: str        # HGNC-approved symbol
    hgnc_id: Optional[str]      # HGNC:12345
    reported_symbols: List[str] # Original symbols found
    sources: List[str]          # PMIDs where found
    source_count: int           # Number of publications
    confidence_score: float     # 0-1 normalized score
    
@dataclass
class LiteratureResults:
    genes: List[LiteratureGene]
    metadata: Dict[str, Any]
    processing_stats: Dict[str, int]
    timestamp: datetime
```

## Dependencies

### Required Libraries
```toml
[project]
dependencies = [
    "openpyxl>=3.1.0",      # Excel file reading
    "python-docx>=1.0.0",    # DOCX file processing
    "pdfplumber>=0.10.0",    # PDF text extraction
    "beautifulsoup4>=4.12",  # HTML/XML parsing
    "pyyaml>=6.0",          # Configuration files
    "requests>=2.31",        # HTTP requests
    "pandas>=2.0",          # Data manipulation
]
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Set up project structure
- [ ] Create base scraper class
- [ ] Implement file type extractors
- [ ] Add HGNC normalization utilities
- [ ] Create output schemas

### Phase 2: Publication Processors (Week 2)
- [ ] Implement processors for each PMID
- [ ] Port extraction logic from R script
- [ ] Add publication-specific filters
- [ ] Test against expected outputs

### Phase 3: Integration & Testing (Week 3)
- [ ] Create main execution script
- [ ] Add batch processing capabilities
- [ ] Implement error handling and logging
- [ ] Generate comprehensive test suite
- [ ] Validate against R script outputs

### Phase 4: Optimization & Documentation (Week 4)
- [ ] Add caching for HGNC lookups
- [ ] Implement parallel processing
- [ ] Create usage documentation
- [ ] Add performance metrics
- [ ] Integration with main pipeline

## Key Considerations

### Data Quality
- **Validation**: Compare outputs with R script results
- **Coverage**: Ensure all genes are captured
- **Accuracy**: Minimize false positives
- **Consistency**: Standardize gene symbols

### Performance
- **Caching**: Cache HGNC API responses
- **Batching**: Process API calls in batches
- **Parallelization**: Process multiple files concurrently
- **Memory**: Stream large files rather than loading entirely

### Maintainability
- **Modularity**: Separate concerns (extraction, processing, normalization)
- **Configuration**: Externalize patterns and rules
- **Logging**: Comprehensive logging for debugging
- **Testing**: Unit tests for each component

### Error Handling
- **File Access**: Handle missing or corrupted files
- **Extraction Failures**: Graceful degradation
- **API Failures**: Retry logic with backoff
- **Data Validation**: Schema validation

## Success Metrics

1. **Completeness**: Extract ≥95% of genes from R script output
2. **Accuracy**: ≥98% match with HGNC normalization
3. **Performance**: Process all files in <5 minutes
4. **Reliability**: Zero crashes on valid input
5. **Maintainability**: Clear documentation and tests

## Next Steps

1. **Immediate Actions**:
   - Install required dependencies
   - Create base scraper infrastructure
   - Implement first extractor (DOCX)
   - Test with PMID_35325889

2. **Validation**:
   - Compare outputs with R script results
   - Identify and resolve discrepancies
   - Document edge cases

3. **Integration**:
   - Connect to main pipeline
   - Add to automated workflows
   - Create monitoring dashboards

## Risk Mitigation

### Technical Risks
- **PDF Complexity**: Some PDFs may have complex layouts
  - *Mitigation*: Use multiple extraction libraries as fallback
  
- **HGNC API Limits**: Rate limiting on API calls
  - *Mitigation*: Implement caching and batch processing
  
- **File Format Changes**: Future publications may use different formats
  - *Mitigation*: Modular design allows easy addition of new extractors

### Data Risks
- **Missing Genes**: Some genes may not be captured
  - *Mitigation*: Manual review process for validation
  
- **False Positives**: Non-gene text matched as genes
  - *Mitigation*: Strict validation patterns and HGNC verification

## Appendix: Extraction Patterns from R Script

### Pattern Examples
1. **PMID_35325889**: Find paragraph with "ABCC6", split by ", "
2. **PMID_34264297**: Unzip, read Excel with skip=2, clean gene column
3. **PMID_36035137**: Read Excel with skip=1, extract Gene column
4. **PMID_33664247**: PDF text, skip 15 lines, complex filtering
5. **PMID_30476936**: Excel, extract "Gene Name" column
6. **PMID_31509055**: PDF text, filter noise, extract genes
7. **PMID_31822006**: PDF pages 1-9, skip 31 lines, clean
8. **PMID_29801666**: DOCX table, cell_id=1, filter "Gene"
9. **PMID_31027891**: DOCX table, cell_id=8, split by ", "
10. **PMID_26862157**: PDF pages 1-4, skip 9 lines, clean
11. **PMID_33532864**: DOCX table, cell_id=1, take first 316
12. **PMID_35005812**: Excel with skip=1, column 2, remove parentheses

## References
- Original R script: `../kidney-genetics-v1/analyses/02_Literature/02_Literature.R`
- Diagnostic scrapers: `scrapers/diagnostics/`
- Backend pipeline: `backend/app/pipeline/sources/`