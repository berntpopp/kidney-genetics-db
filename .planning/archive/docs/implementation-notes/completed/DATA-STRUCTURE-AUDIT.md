# Data Structure Audit - Dashboard Visualizations

**Date**: 2025-10-03
**Status**: ✅ Complete Database Audit

---

## Actual JSONB Structures in Database

### ✅ HPO (Human Phenotype Ontology)

**Available Fields**:
```json
{
  "hpo_terms": ["HP:0000077", "HP:0000107", ...],  // Array of phenotype IDs
  "evidence_score": 100,
  "syndromic_assessment": {...},
  "last_updated": "2025-09-26T16:20:07.297622+00:00"
}
```

**Best Visualization**: Count of HPO terms per gene
- Shows how many phenotypes each gene is associated with
- More phenotypes = more comprehensive annotation

**View Query**:
```sql
SELECT
    jsonb_array_length(evidence_data->'hpo_terms') as hpo_term_count,
    COUNT(*) as gene_count
FROM gene_evidence
WHERE source_name = 'HPO'
    AND evidence_data->'hpo_terms' IS NOT NULL
GROUP BY 1
ORDER BY 1 DESC
```

---

### ✅ GenCC (Gene Curation Coalition)

**Available Fields**:
```json
{
  "classifications": ["Strong", "Supportive", "Definitive"],  // Array
  "submissions": [...],
  "submission_count": 6,
  "submitters": ["Orphanet", "PanelApp Australia", ...],
  "evidence_score": 1.0
}
```

**Best Visualization**: Classification distribution
- Shows strength of gene-disease associations
- Values: "Definitive", "Strong", "Moderate", "Supportive", "Limited", "Disputed Evidence", etc.

**View Query**:
```sql
SELECT
    jsonb_array_elements_text(evidence_data->'classifications') as classification,
    COUNT(DISTINCT gene_id) as gene_count
FROM gene_evidence
WHERE source_name = 'GenCC'
    AND evidence_data->'classifications' IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC
```

**Status**: ✅ View correct as-is

---

### ✅ ClinGen (Clinical Genome Resource)

**Available Fields**:
```json
{
  "classifications": ["Limited"],  // Array
  "validities": [...],
  "validity_count": 1,
  "expert_panels": ["Kidney Cystic and Ciliopathy Disorders..."],
  "evidence_score": 30.0,
  "max_classification_score": 0.3
}
```

**Best Visualization**: Classification distribution
- Shows strength of gene-disease validity
- Values: "Definitive", "Strong", "Moderate", "Limited", "Disputed", "Refuted"

**View Query**:
```sql
SELECT
    jsonb_array_elements_text(evidence_data->'classifications') as classification,
    COUNT(DISTINCT gene_id) as gene_count
FROM gene_evidence
WHERE source_name = 'ClinGen'
    AND evidence_data->'classifications' IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC
```

**Status**: ✅ View correct as-is

---

### ✅ DiagnosticPanels (Commercial Diagnostic Panels)

**Available Fields**:
```json
{
  "panels": ["Comprehensive Kidney Disease Panel", ...],  // Array
  "providers": ["blueprint_genetics", "invitae", ...],  // Array
  "panel_count": 6,
  "provider_count": 6
}
```

**Best Visualization**: Provider distribution
- Shows which commercial labs include this gene
- Helps clinicians understand testing availability

**View Query**:
```sql
SELECT
    jsonb_array_elements_text(evidence_data->'providers') as provider,
    COUNT(DISTINCT gene_id) as gene_count
FROM gene_evidence
WHERE source_name = 'DiagnosticPanels'
    AND evidence_data->'providers' IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC
```

**Status**: ✅ View correct as-is

---

### ⚠️ PanelApp (UK/Australia Gene Panels)

**Available Fields**:
```json
{
  "panels": [...],
  "evidence_levels": ["3"],  // Array of strings: "1", "2", "3"
  "modes_of_inheritance": ["BIALLELIC, autosomal or pseudoautosomal"],
  "panel_count": 1,
  "phenotypes": [...]
}
```

**Best Visualization**: Evidence level distribution
- NOT "confidence_level" (that field doesn't exist!)
- Values: "1", "2", "3" (Green/Amber/Red light system)
  - "3" = Green (High confidence)
  - "2" = Amber (Moderate confidence)
  - "1" = Red (Low confidence)

**CORRECTED View Query**:
```sql
SELECT
    jsonb_array_elements_text(evidence_data->'evidence_levels') as evidence_level,
    COUNT(DISTINCT gene_id) as gene_count
FROM gene_evidence
WHERE source_name = 'PanelApp'
    AND evidence_data->'evidence_levels' IS NOT NULL
GROUP BY 1
ORDER BY 1 DESC
```

**Status**: ❌ View INCORRECT - needs fixing

---

### ❌ ClinVar (Clinical Variant Database)

**Database Status**: ⚠️ **NO DATA FOUND**

**Analysis**: The gene_evidence table has no ClinVar entries. ClinVar may be:
1. Not yet implemented in the pipeline
2. Disabled in configuration
3. Data ingestion failed

**Action**: Remove ClinVar view entirely until data is available

**Status**: ❌ View should be REMOVED

---

### ✅ PubTator (Literature Mining)

**Available Fields**:
```json
{
  "publication_count": 1,  // Integer
  "total_mentions": 1,
  "mentions": [...],
  "pmids": ["24971102"],
  "evidence_score": 32.176647
}
```

**Best Visualization**: Publication count distribution
- Shows literature support for each gene
- More publications = more research/clinical interest

**View Query**:
```sql
SELECT
    CAST(evidence_data->>'publication_count' AS INTEGER) as publication_count,
    COUNT(DISTINCT gene_id) as gene_count
FROM gene_evidence
WHERE source_name = 'PubTator'
    AND evidence_data->>'publication_count' IS NOT NULL
GROUP BY 1
ORDER BY 1 DESC
LIMIT 20
```

**Status**: ✅ View correct as-is

---

## Summary of Required Fixes

### Views to Fix
1. **✅ HPO**: Change from `publication_count` to `hpo_term_count` (jsonb_array_length)
2. **❌ PanelApp**: Change from `confidence_level` to `evidence_levels`
3. **❌ ClinVar**: Remove entirely (no data)

### Views that are Correct
- ✅ GenCC (classifications array)
- ✅ ClinGen (classifications array)
- ✅ DiagnosticPanels (providers array)
- ✅ PubTator (publication_count)

---

## Handlers to Update

### HPODistributionHandler
```python
def format_result(self, rows: list) -> list[dict[str, Any]]:
    return [
        {
            "category": f"{row[0]} HPO terms",  # Changed from publications
            "value": row[1],
            "metadata": {"hpo_term_count": row[0]},
        }
        for row in rows
    ]
```

### PanelAppDistributionHandler
```python
def format_result(self, rows: list) -> list[dict[str, Any]]:
    # Map evidence levels to labels
    level_labels = {
        "3": "Green (High confidence)",
        "2": "Amber (Moderate confidence)",
        "1": "Red (Low confidence)",
    }

    return [
        {
            "category": level_labels.get(row[0], f"Level {row[0]}"),
            "value": row[1],
            "metadata": {"evidence_level": row[0]},
        }
        for row in rows
    ]
```

### Factory - Remove ClinVar
```python
_handlers = {
    "HPO": HPODistributionHandler,
    "GenCC": GenCCDistributionHandler,
    "ClinGen": ClinGenDistributionHandler,
    "DiagnosticPanels": DiagnosticPanelsDistributionHandler,
    "PanelApp": PanelAppDistributionHandler,
    # "ClinVar": ClinVarDistributionHandler,  # REMOVED - no data
    "PubTator": PubTatorDistributionHandler,
}
```

---

## Migration Update Required

The migration needs to be updated to:
1. Fix HPO view query
2. Fix PanelApp view query
3. Remove ClinVar view creation

---

**Next Steps**: Apply these corrections to views.py, handlers, and migration
