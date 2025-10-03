# GenCC-Compatible Schema Migration Guide

## Overview

This guide covers the migration from the original R-based CSV schema to our new GenCC-compatible JSON schema. The new schema enables direct submission to the international Gene Curation Coalition database while preserving all existing functionality.

## Schema Evolution

### From CSV to Structured JSON

**Original R Schema (CSV-based)**:
```csv
approved_symbol,hgnc_id,source,omim_summary,clingen_summary,source_count,final_score
PKD1,HGNC:9008,"PMID_35325889 | PanelApp_UK","Polycystic kidney disease","Definitive",3,85.2
```

**New GenCC-Compatible Schema**:
```json
{
  "hgnc_id": "HGNC:9008",
  "approved_symbol": "PKD1", 
  "evidence_sources": [
    {
      "id": "pmid-35325889",
      "source_name": "Literature Review",
      "source_category": "Literature",
      "date_accessed": "2024-05-15",
      "details": {"publication_id": "PMID:35325889"}
    },
    {
      "id": "panelapp-uk-234", 
      "source_name": "PanelApp UK",
      "source_category": "Expert Panel",
      "date_accessed": "2024-05-15",
      "details": {"evidence_level": "Green"}
    }
  ],
  "disease_associations": [
    {
      "disease_id": "MONDO:0009180",
      "disease_name": "Polycystic kidney disease 1",
      "clinical_validity": "Definitive",
      "assertion_date": "2024-05-15",
      "supporting_evidence_ids": ["pmid-35325889", "panelapp-uk-234"]
    }
  ]
}
```

## Key Improvements

### 1. From Summary Strings to Structured Evidence
- **Before**: `"PMID_35325889 | PMID_34264297"` (concatenated string)
- **After**: Array of evidence objects with full metadata and provenance

### 2. From Aggregated Scores to Traceable Classifications  
- **Before**: `final_score: 85.2` (opaque calculation)
- **After**: Clear mapping from evidence sources to GenCC clinical validity terms

### 3. From Single Disease to Multiple Associations
- **Before**: One disease per gene (implicit from context)
- **After**: Explicit gene-disease-inheritance triplets with evidence support

## Migration Strategy

### Phase 1: Schema Validation Setup

```python
# scripts/validate_schema.py
import json
import jsonschema
from pathlib import Path

def validate_gene_curation(data: dict) -> bool:
    """Validate gene curation data against GenCC-compatible schema."""
    schema_path = Path("schema/gene_curation.json")
    with open(schema_path) as f:
        schema = json.load(f)
    
    try:
        jsonschema.validate(data, schema)
        return True
    except jsonschema.ValidationError as e:
        print(f"Validation error: {e.message}")
        return False
```

### Phase 2: Data Transformation Pipeline

```python
# scripts/migrate_csv_to_json.py
import pandas as pd
from typing import Dict, List, Any

def transform_csv_row_to_json(row: pd.Series) -> Dict[str, Any]:
    """Transform legacy CSV row to GenCC-compatible JSON."""
    
    # Parse concatenated source strings
    sources = parse_source_string(row['source'])
    
    # Build evidence_sources array
    evidence_sources = []
    for i, source in enumerate(sources):
        evidence_sources.append({
            "id": f"legacy-{i}",
            "source_name": source['name'],
            "source_category": categorize_source(source['name']),
            "date_accessed": row.get('date_updated', '2024-01-01'),
            "original_classification": source.get('classification', 'Unknown'),
            "details": source.get('details', {})
        })
    
    # Build disease associations 
    disease_associations = []
    if pd.notna(row.get('omim_summary')):
        disease_associations.append({
            "disease_id": extract_omim_id(row['omim_summary']),
            "disease_name": extract_disease_name(row['omim_summary']),
            "clinical_validity": map_to_gencc_term(row.get('clingen_summary', '')),
            "assertion_date": row.get('date_updated', '2024-01-01'),
            "supporting_evidence_ids": [e["id"] for e in evidence_sources]
        })
    
    return {
        "hgnc_id": row['hgnc_id'],
        "approved_symbol": row['approved_symbol'],
        "evidence_sources": evidence_sources,
        "disease_associations": disease_associations,
        "curation_metadata": {
            "curation_status": "Automated",
            "curation_version": 1,
            "last_updated": row.get('date_updated', '2024-01-01T00:00:00Z'),
            "flags": {
                "migrated_from_csv": True
            }
        }
    }
```

### Phase 3: Evidence Level Mapping

```python
def map_to_gencc_term(legacy_classification: str) -> str:
    """Map legacy classifications to GenCC standardized terms."""
    
    mapping = {
        # ClinGen mappings
        "Definitive": "Definitive",
        "Strong": "Strong", 
        "Moderate": "Moderate",
        "Limited": "Limited",
        "Disputed": "Disputed Evidence",
        "Refuted": "Refuted Evidence",
        
        # PanelApp mappings
        "Green": "Strong",
        "Amber": "Moderate", 
        "Red": "Limited",
        
        # Literature confidence mappings
        "High confidence": "Strong",
        "Medium confidence": "Moderate",
        "Low confidence": "Limited",
        
        # Default fallback
        "Unknown": "Limited"
    }
    
    return mapping.get(legacy_classification, "Limited")
```

## Database Migration

### Alembic Migration Script

```python
# alembic/versions/001_add_gencc_schema.py
"""Add GenCC-compatible schema validation

Revision ID: 001
Create Date: 2024-05-15 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Add constraint for GenCC compatibility
    op.execute("""
        ALTER TABLE gene_curations 
        ADD CONSTRAINT gencc_compatible_schema CHECK (
            -- Required GenCC fields
            (curation_data ? 'hgnc_id') AND
            (curation_data ? 'approved_symbol') AND
            (curation_data ? 'evidence_sources') AND
            
            -- HGNC ID format validation
            (curation_data->>'hgnc_id' ~ '^HGNC:[0-9]+$') AND
            
            -- Evidence sources structure validation
            (jsonb_typeof(curation_data->'evidence_sources') = 'array') AND
            
            -- Disease associations validation (if present)
            (CASE WHEN curation_data ? 'disease_associations' 
             THEN jsonb_typeof(curation_data->'disease_associations') = 'array' AND
                  curation_data->'disease_associations' @> '[{"clinical_validity": "Definitive"}]'::jsonb OR
                  curation_data->'disease_associations' @> '[{"clinical_validity": "Strong"}]'::jsonb OR  
                  curation_data->'disease_associations' @> '[{"clinical_validity": "Moderate"}]'::jsonb OR
                  curation_data->'disease_associations' @> '[{"clinical_validity": "Limited"}]'::jsonb OR
                  curation_data->'disease_associations' @> '[{"clinical_validity": "Disputed Evidence"}]'::jsonb OR
                  curation_data->'disease_associations' @> '[{"clinical_validity": "Refuted Evidence"}]'::jsonb OR
                  curation_data->'disease_associations' @> '[{"clinical_validity": "No Known Disease Relationship"}]'::jsonb OR
                  curation_data->'disease_associations' @> '[{"clinical_validity": "Animal Model Only"}]'::jsonb
             ELSE true END)
        )
    """)

def downgrade():
    op.drop_constraint('gencc_compatible_schema', 'gene_curations')
```

## Validation Tools

### Schema Compliance Checker

```python
# scripts/check_gencc_compliance.py
def check_gencc_compliance(gene_data: dict) -> Dict[str, Any]:
    """Check if gene curation meets GenCC submission requirements."""
    
    issues = []
    warnings = []
    
    # Required field validation
    required_fields = ['hgnc_id', 'approved_symbol', 'evidence_sources', 'curation_metadata']
    for field in required_fields:
        if field not in gene_data:
            issues.append(f"Missing required field: {field}")
    
    # HGNC ID format validation
    if not re.match(r'^HGNC:[0-9]+$', gene_data.get('hgnc_id', '')):
        issues.append("Invalid HGNC ID format")
    
    # Disease associations validation
    if 'disease_associations' in gene_data:
        for assoc in gene_data['disease_associations']:
            if assoc.get('clinical_validity') not in GENCC_VALID_TERMS:
                issues.append(f"Invalid clinical validity term: {assoc.get('clinical_validity')}")
            
            if not assoc.get('assertion_date'):
                warnings.append("Missing assertion_date - required for GenCC submission")
    
    return {
        "compliant": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "gencc_submittable": len(issues) == 0 and len(warnings) == 0
    }
```

## Testing Strategy

### Unit Tests for Schema Validation

```python
def test_gencc_schema_validation():
    """Test GenCC schema compliance."""
    
    valid_data = {
        "hgnc_id": "HGNC:9008",
        "approved_symbol": "PKD1",
        "evidence_sources": [
            {
                "id": "test-1",
                "source_name": "Test Source",
                "source_category": "Expert Panel",
                "date_accessed": "2024-05-15"
            }
        ],
        "disease_associations": [
            {
                "disease_id": "MONDO:0009180",
                "disease_name": "Test Disease",
                "clinical_validity": "Strong",
                "assertion_date": "2024-05-15"
            }
        ],
        "curation_metadata": {
            "curation_status": "Expert Curated",
            "curation_version": 1,
            "last_updated": "2024-05-15T10:00:00Z"
        }
    }
    
    assert validate_gene_curation(valid_data) == True
    
    compliance = check_gencc_compliance(valid_data)
    assert compliance["compliant"] == True
    assert compliance["gencc_submittable"] == True
```

## Rollout Plan

1. **Phase 1**: Implement schema validation in development environment
2. **Phase 2**: Migrate historical CSV data with validation checks  
3. **Phase 3**: Update pipeline to generate GenCC-compatible output
4. **Phase 4**: Implement GenCC submission workflow
5. **Phase 5**: Production deployment with monitoring

## Monitoring and Alerts

- Schema validation failure alerts
- GenCC submission success/failure tracking  
- Data quality metrics dashboard
- Performance impact monitoring during migration

This migration establishes the foundation for international collaboration while maintaining full backward compatibility with existing workflows.