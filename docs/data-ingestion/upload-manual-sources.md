# Manual Data Source Upload Guide

This guide explains how to upload diagnostic panel and literature data to the Kidney Genetics Database.

## Prerequisites

1. Admin credentials (default: `admin` / `ChangeMe!Admin2024`)
2. Data files in JSON format:
   - Diagnostic panels: `scrapers/diagnostics/output/YYYY-MM-DD/`
   - Literature: `scrapers/literature/output/YYYY-MM-DD/`

## Authentication

First, obtain an authentication token:

```bash
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=ChangeMe!Admin2024")

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')
```

## Uploading Diagnostic Panels

**IMPORTANT**: Each diagnostic panel provider must be uploaded separately to preserve source attribution for the evidence counting algorithm.

### Individual Provider Upload

```bash
# Upload a single diagnostic panel provider
curl -X POST "http://localhost:8000/api/ingestion/DiagnosticPanels/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/provider.json" \
  -F "mode=full"
```

### Batch Upload All Providers

```bash
# Navigate to diagnostic panels directory
cd scrapers/diagnostics/output/2025-08-24/

# Upload each provider separately
for file in *.json; do
  echo "Uploading $file..."
  curl -X POST "http://localhost:8000/api/ingestion/DiagnosticPanels/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$file" \
    -F "mode=full" \
    -s | jq -c '{status:.data.status, provider:.data.provider, genes:.data.genes_processed}'
done
```

### Supported Diagnostic Panel Providers

- blueprint_genetics.json - Blueprint Genetics kidney disease panels
- cegat.json - CeGaT kidney genetic testing
- centogene.json - Centogene rare kidney disease panels
- invitae.json - Invitae comprehensive kidney panels
- mayo_clinic.json - Mayo Clinic kidney genetics
- mgz_muenchen.json - MGZ München diagnostic panels
- mvz_medicover.json - MVZ Medicover genetics
- natera.json - Natera kidney disease testing
- prevention_genetics.json - Prevention Genetics panels

## Uploading Literature Data

Literature files contain curated gene lists from scientific publications. Each file represents a different publication (identified by PMID).

### Individual Publication Upload

```bash
# Upload a single literature file
curl -X POST "http://localhost:8000/api/ingestion/Literature/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/literature_pmid_XXXXX.json" \
  -F "mode=full"
```

### Batch Upload All Literature

```bash
# Navigate to literature directory
cd scrapers/literature/output/2025-08-24/

# Upload each publication separately
for file in literature_pmid_*.json; do
  pmid=$(echo $file | grep -oP '\d+')
  echo "Uploading PMID $pmid..."
  curl -X POST "http://localhost:8000/api/ingestion/Literature/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$file" \
    -F "mode=full" \
    -s | jq -c "{pmid: \"${pmid}\", status:.data.status, genes:.data.genes_processed}"
done
```

## Upload Modes

- `full`: Replace all existing data for this source (recommended for initial upload)
- `incremental`: Add new data without removing existing entries

## Response Format

Successful uploads return:
```json
{
  "data": {
    "status": "success",
    "source": "DiagnosticPanels",
    "provider": "provider_name",
    "filename": "provider.json",
    "genes_processed": 370,
    "storage_stats": {
      "created": 369,
      "merged": 0,
      "failed": 1,
      "filtered": 0
    },
    "message": "Successfully processed 370 genes"
  }
}
```

## Automated Data Sources

The following sources are automatically updated via API and don't require manual upload:
- **PanelApp**: UK/Australia gene panels
- **HPO**: Human Phenotype Ontology
- **ClinGen**: Clinical Genome Resource
- **GenCC**: Gene Curation Coalition
- **PubTator**: Literature mining from PubMed

To update all automated sources:
```bash
curl -X POST "http://localhost:8000/api/datasources/update-all" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

## Complete Database Rebuild

To completely rebuild the database with all sources:

1. Clean the database:
```bash
make db-clean
```

2. Update automated sources:
```bash
curl -X POST "http://localhost:8000/api/datasources/update-all" \
  -H "Authorization: Bearer $TOKEN"
```

3. Upload diagnostic panels (see above)

4. Upload literature data (see above)

## Troubleshooting

### Authentication Errors
- Ensure token hasn't expired (30 minutes lifetime)
- Regenerate token if needed

### File Upload Errors
- Check file exists and is valid JSON
- Ensure proper file permissions
- Verify file follows expected schema

### Data Not Appearing
- Check upload response for errors
- Verify data in Admin panel: http://localhost:5173/admin
- Check backend logs: `make dev-logs`

## API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/login` | POST | Get authentication token |
| `/api/datasources/update-all` | POST | Update all automated sources |
| `/api/ingestion/DiagnosticPanels/upload` | POST | Upload diagnostic panel file |
| `/api/ingestion/Literature/upload` | POST | Upload literature file |
| `/api/datasources/` | GET | List all data sources and status |
| `/api/progress/status/{source}` | GET | Check source update progress |

## Important Notes

1. **Never combine diagnostic panel files** - Each provider must remain separate for proper evidence counting
2. **Each literature file represents a single publication** - Keep PMIDs separate
3. **Use full mode for initial uploads** to ensure clean data
4. **Monitor progress** via the admin panel during large uploads
5. **Token expires after 30 minutes** - Refresh if needed for long operations