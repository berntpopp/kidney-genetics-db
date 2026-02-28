# Hybrid Source CRUD API Testing Guide

**Status**: Implemented
**Date**: 2025-10-08
**Related**: hybrid-source-crud-implementation.md

## Overview

This guide provides curl commands for manually testing all hybrid source CRUD endpoints for DiagnosticPanels and Literature sources.

## Prerequisites

1. Backend running on `http://localhost:8000`
2. Valid curator authentication token
3. Test data files (JSON, CSV, or Excel)

## Getting an Auth Token

```bash
# Login as curator
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "curator_username", "password": "curator_password"}'

# Extract token from response and export
export TOKEN="your_jwt_token_here"
```

## Endpoint Testing Commands

### 1. List Available Sources

```bash
curl -X GET http://localhost:8000/api/ingestion/ \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "data": {
    "sources": [
      {
        "name": "DiagnosticPanels",
        "supports_upload": true,
        "supported_formats": ["json", "csv", "tsv", "xlsx", "xls"],
        "description": "Commercial diagnostic panel data from various providers"
      },
      {
        "name": "Literature",
        "supports_upload": true,
        "supported_formats": ["json", "csv", "tsv", "xlsx", "xls"],
        "description": "Manually curated literature evidence"
      }
    ]
  },
  "meta": {"total": 2}
}
```

### 2. Get Source Status

```bash
# DiagnosticPanels status
curl -X GET http://localhost:8000/api/ingestion/DiagnosticPanels/status \
  -H "Content-Type: application/json"

# Literature status
curl -X GET http://localhost:8000/api/ingestion/Literature/status \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "data": {
    "source": "DiagnosticPanels",
    "evidence_records": 250,
    "unique_genes": 150,
    "supports_upload": true,
    "supported_formats": ["json", "csv", "tsv", "xlsx", "xls"],
    "sample_providers": ["Invitae", "Blueprint Genetics"],
    "provider_count_estimate": 5
  },
  "meta": {"source_name": "DiagnosticPanels"}
}
```

### 3. Upload File (MERGE Mode)

```bash
# Create test file
cat > test_panel.json << 'EOF'
[
  {
    "gene": "PKD1",
    "panel": "Kidney Disease Panel",
    "provider": "TestProvider",
    "confidence": "high"
  },
  {
    "gene": "PKD2",
    "panel": "Kidney Disease Panel",
    "provider": "TestProvider",
    "confidence": "high"
  }
]
EOF

# Upload in merge mode (default)
curl -X POST http://localhost:8000/api/ingestion/DiagnosticPanels/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_panel.json" \
  -F "provider_name=TestProvider" \
  -F "mode=merge"
```

**Expected Response:**
```json
{
  "data": {
    "status": "success",
    "source": "DiagnosticPanels",
    "provider": "TestProvider",
    "filename": "test_panel.json",
    "file_size": 234,
    "genes_processed": 2,
    "storage_stats": {
      "created": 2,
      "merged": 0,
      "failed": 0,
      "filtered": 0
    },
    "message": "Successfully processed 2 genes. Created: 2, Merged: 0"
  },
  "meta": {
    "upload_id": "upload_1696780800",
    "processing_time_ms": null
  }
}
```

### 4. Upload File (REPLACE Mode)

```bash
# Upload in replace mode (deletes existing provider data first)
curl -X POST http://localhost:8000/api/ingestion/DiagnosticPanels/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_panel.json" \
  -F "provider_name=TestProvider" \
  -F "mode=replace"
```

**Expected Response:**
```json
{
  "data": {
    "status": "success",
    "source": "DiagnosticPanels",
    "provider": "TestProvider",
    "filename": "test_panel.json",
    "file_size": 234,
    "genes_processed": 2,
    "storage_stats": {
      "created": 2,
      "merged": 0,
      "failed": 0,
      "filtered": 0
    },
    "message": "Successfully processed 2 genes. Created: 2, Merged: 0"
  }
}
```

### 5. List Identifiers

```bash
# List DiagnosticPanels providers
curl -X GET http://localhost:8000/api/ingestion/DiagnosticPanels/identifiers \
  -H "Content-Type: application/json"

# List Literature publications
curl -X GET http://localhost:8000/api/ingestion/Literature/identifiers \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "data": {
    "identifiers": [
      {
        "identifier": "TestProvider",
        "gene_count": 2,
        "last_updated": "2025-10-08T10:30:00Z"
      },
      {
        "identifier": "Invitae",
        "gene_count": 150,
        "last_updated": "2025-10-07T14:20:00Z"
      }
    ]
  },
  "meta": {
    "total": 2,
    "source_name": "DiagnosticPanels"
  }
}
```

### 6. Delete by Identifier

```bash
# Delete DiagnosticPanels provider
curl -X DELETE http://localhost:8000/api/ingestion/DiagnosticPanels/identifiers/TestProvider \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Delete Literature publication
curl -X DELETE http://localhost:8000/api/ingestion/Literature/identifiers/PMID12345678 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "data": {
    "source": "DiagnosticPanels",
    "identifier": "TestProvider",
    "deletion_stats": {
      "deleted_evidence": 2,
      "affected_genes": 2,
      "audit_created": true
    },
    "message": "Successfully deleted 2 evidence records"
  },
  "meta": {
    "deleted_by": "curator_username"
  }
}
```

### 7. List Upload History

```bash
# List DiagnosticPanels uploads
curl -X GET "http://localhost:8000/api/ingestion/DiagnosticPanels/uploads?limit=10&offset=0" \
  -H "Content-Type: application/json"

# List Literature uploads
curl -X GET "http://localhost:8000/api/ingestion/Literature/uploads?limit=10&offset=0" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "data": {
    "uploads": [
      {
        "id": 1,
        "evidence_name": "TestProvider",
        "file_hash": "abc123...",
        "original_filename": "test_panel.json",
        "upload_status": "completed",
        "uploaded_by": "curator_username",
        "uploaded_at": "2025-10-08T10:30:00Z",
        "processed_at": "2025-10-08T10:30:05Z",
        "gene_count": 2,
        "genes_normalized": 2,
        "genes_failed": 0,
        "upload_metadata": {"mode": "merge"}
      }
    ]
  },
  "meta": {
    "total": 1,
    "limit": 10,
    "offset": 0,
    "source_name": "DiagnosticPanels"
  }
}
```

### 8. Soft Delete Upload Record

```bash
# Soft delete upload (marks as deleted, doesn't remove data)
curl -X DELETE http://localhost:8000/api/ingestion/DiagnosticPanels/uploads/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "data": {
    "upload_id": 1,
    "source": "DiagnosticPanels",
    "status": "deleted",
    "message": "Upload 1 marked as deleted"
  },
  "meta": {
    "deleted_by": "curator_username"
  }
}
```

### 9. Get Audit Trail

```bash
# Get DiagnosticPanels audit trail
curl -X GET "http://localhost:8000/api/ingestion/DiagnosticPanels/audit?limit=10&offset=0" \
  -H "Content-Type: application/json"

# Get Literature audit trail
curl -X GET "http://localhost:8000/api/ingestion/Literature/audit?limit=10&offset=0" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "data": {
    "audit_records": [
      {
        "id": 1,
        "operation_type": "upload",
        "performed_by": "curator_username",
        "created_at": "2025-10-08T10:30:00Z",
        "changes_summary": "Uploaded TestProvider with 2 genes",
        "metadata": {
          "provider": "TestProvider",
          "mode": "merge",
          "file": "test_panel.json"
        }
      },
      {
        "id": 2,
        "operation_type": "delete",
        "performed_by": "curator_username",
        "created_at": "2025-10-08T11:00:00Z",
        "changes_summary": "Deleted TestProvider (2 genes)",
        "metadata": {
          "provider": "TestProvider",
          "deleted_evidence": 2
        }
      }
    ]
  },
  "meta": {
    "total": 2,
    "limit": 10,
    "offset": 0,
    "source_name": "DiagnosticPanels"
  }
}
```

## Test Data Examples

### DiagnosticPanels JSON Format
```json
[
  {
    "gene": "PKD1",
    "panel": "Kidney Disease Panel",
    "provider": "TestLab",
    "confidence": "high",
    "moi": "AD"
  },
  {
    "gene": "PKD2",
    "panel": "Kidney Disease Panel",
    "provider": "TestLab",
    "confidence": "moderate",
    "moi": "AD"
  }
]
```

### DiagnosticPanels CSV Format
```csv
gene,panel,provider,confidence,moi
PKD1,Kidney Disease Panel,TestLab,high,AD
PKD2,Kidney Disease Panel,TestLab,moderate,AD
COL4A5,Alport Syndrome Panel,TestLab,high,XL
```

### Literature JSON Format
```json
[
  {
    "gene": "PKD1",
    "publication_id": "PMID12345678",
    "title": "PKD1 mutations in ADPKD",
    "authors": ["Smith J", "Doe A"],
    "journal": "Kidney International",
    "publication_date": "2025-01-15"
  }
]
```

## Error Testing

### Test Invalid Source
```bash
curl -X GET http://localhost:8000/api/ingestion/InvalidSource/status \
  -H "Content-Type: application/json"
```

**Expected**: 400 Bad Request with error message

### Test Unauthorized Access
```bash
curl -X POST http://localhost:8000/api/ingestion/DiagnosticPanels/upload \
  -F "file=@test_panel.json"
```

**Expected**: 401 Unauthorized

### Test File Too Large
```bash
# Create 51MB file
dd if=/dev/zero of=large_file.json bs=1M count=51

curl -X POST http://localhost:8000/api/ingestion/DiagnosticPanels/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@large_file.json"
```

**Expected**: 400 Bad Request with "File size exceeds 50MB limit"

### Test Invalid File Type
```bash
curl -X POST http://localhost:8000/api/ingestion/DiagnosticPanels/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@invalid.pdf" \
  -F "provider_name=Test"
```

**Expected**: 400 Bad Request with "Unsupported file type"

## Testing Workflow

### Complete Upload-Delete Cycle
```bash
# 1. Upload test data
curl -X POST http://localhost:8000/api/ingestion/DiagnosticPanels/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_panel.json" \
  -F "provider_name=TestProvider" \
  -F "mode=merge"

# 2. Verify in identifiers list
curl -X GET http://localhost:8000/api/ingestion/DiagnosticPanels/identifiers

# 3. Check upload history
curl -X GET http://localhost:8000/api/ingestion/DiagnosticPanels/uploads

# 4. View audit trail
curl -X GET http://localhost:8000/api/ingestion/DiagnosticPanels/audit

# 5. Delete the data
curl -X DELETE http://localhost:8000/api/ingestion/DiagnosticPanels/identifiers/TestProvider \
  -H "Authorization: Bearer $TOKEN"

# 6. Verify deletion
curl -X GET http://localhost:8000/api/ingestion/DiagnosticPanels/identifiers
```

### Replace Mode Test
```bash
# 1. Upload initial data
curl -X POST http://localhost:8000/api/ingestion/DiagnosticPanels/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_panel_v1.json" \
  -F "provider_name=TestProvider" \
  -F "mode=merge"

# 2. Check gene count
curl -X GET http://localhost:8000/api/ingestion/DiagnosticPanels/identifiers

# 3. Replace with new data
curl -X POST http://localhost:8000/api/ingestion/DiagnosticPanels/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_panel_v2.json" \
  -F "provider_name=TestProvider" \
  -F "mode=replace"

# 4. Verify gene count changed
curl -X GET http://localhost:8000/api/ingestion/DiagnosticPanels/identifiers

# 5. Check audit trail for both upload and delete operations
curl -X GET http://localhost:8000/api/ingestion/DiagnosticPanels/audit
```

## Integration with Frontend

The frontend at `http://localhost:5173/admin/hybrid-sources` provides a UI for all these operations:

1. **Upload Tab**: File upload with mode selection (merge/replace)
2. **History Tab**: View upload history
3. **Audit Trail Tab**: View all operations
4. **Manage Tab**: List and delete providers/publications

## Notes

- All DELETE operations require curator authentication
- File uploads support JSON, CSV, TSV, and Excel formats
- Maximum file size is 50MB
- SHA256 hash is calculated for all uploaded files
- REPLACE mode creates a transaction savepoint for safety
- Audit records are automatically created for all operations
- Upload tracking includes gene counts, normalization stats, and metadata

## Troubleshooting

### Upload Fails with "Processing failed"
- Check file format matches expected structure
- Verify gene symbols are valid
- Review backend logs for detailed error messages

### Delete Fails with "No evidence found"
- Verify identifier exists using list endpoint
- Check exact spelling (identifiers are case-sensitive)

### Authentication Issues
- Ensure token is valid and not expired
- Verify user has curator role
- Check Authorization header format: `Bearer <token>`

## Implementation Status

✅ All endpoints implemented and tested
✅ Frontend integration complete
✅ Unit tests created (test_hybrid_crud.py)
✅ Migration and database views in place
✅ Upload tracking and audit trail functional
