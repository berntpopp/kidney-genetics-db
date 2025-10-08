# Hybrid Source Upload Guide

## Overview

Upload DiagnosticPanels and Literature evidence files through the admin panel to supplement automated data sources.

## Supported Sources

### DiagnosticPanels
Commercial diagnostic panel data from providers like:
- Blueprint Genetics
- Invitae
- GeneDx
- CeGaT
- Custom lab panels

### Literature
Manually curated literature evidence from:
- Research publications
- Case reports
- Expert reviews

## Upload Process

### 1. Access Upload Interface

1. Log in as Admin user
2. Navigate to **Admin Panel** → **Hybrid Sources**
3. Select source type tab (DiagnosticPanels or Literature)

### 2. Prepare Your File

**Supported Formats**:
- JSON (.json)
- CSV (.csv)
- TSV (.tsv)
- Excel (.xlsx, .xls)

**File Size Limit**: 50MB

**Required Fields** (CSV/TSV/Excel):
- `gene_symbol` - HGNC gene symbol
- Additional fields vary by source

**Example CSV**:
```csv
gene_symbol,panel_name,confidence
PKD1,Polycystic Kidney Disease,high
PKD2,Polycystic Kidney Disease,high
NPHS1,Congenital Nephrotic Syndrome,definitive
```

### 3. Upload File

**Method 1: Drag & Drop**
1. Drag file from your computer
2. Drop onto the upload zone
3. File automatically validated

**Method 2: Browse**
1. Click "Browse Files" button
2. Select file from file picker
3. Confirm selection

### 4. Configure Upload

**Provider Name** (optional):
- Enter provider identifier (e.g., "blueprint_genetics")
- If empty, filename used as provider name
- Used for evidence attribution

### 5. Review Results

Upload results show:
- **Status**: Success or failure
- **Genes Processed**: Total genes in file
- **Created**: New gene records added
- **Merged**: Evidence merged into existing genes

## File Format Examples

### DiagnosticPanels JSON
```json
{
  "provider": "blueprint_genetics",
  "genes": [
    {
      "gene_symbol": "PKD1",
      "panels": ["Polycystic Kidney Disease"],
      "confidence": "high"
    }
  ]
}
```

### Literature CSV
```csv
gene_symbol,pmid,publication_year,evidence_type
NPHS1,12345678,2020,case_report
NPHS2,87654321,2021,cohort_study
```

## Troubleshooting

### File Rejected
- **Issue**: "Unsupported file type"
- **Solution**: Ensure file extension is .json, .csv, .tsv, .xlsx, or .xls

### File Too Large
- **Issue**: "File size exceeds 50MB limit"
- **Solution**: Split file into smaller chunks, upload separately

### Upload Failed
- **Issue**: "Processing failed"
- **Solution**: Check file format, ensure required fields present

### Gene Not Found
- **Issue**: Gene symbol not recognized
- **Solution**: System attempts HGNC normalization, check symbol validity

## Best Practices

1. **Validate Data First**: Review file contents before upload
2. **Use Provider Names**: Helps track data sources
3. **Small Batches**: Upload 100-500 genes at a time for better tracking
4. **Check Results**: Review created/merged counts
5. **Document Sources**: Keep records of upload dates and providers

## API Integration

For automated uploads, use the REST API:

```bash
curl -X POST http://localhost:8000/api/ingestion/DiagnosticPanels/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@diagnostic_panels.csv" \
  -F "provider_name=blueprint_genetics"
```

See API documentation: `/api/docs#/ingestion`
