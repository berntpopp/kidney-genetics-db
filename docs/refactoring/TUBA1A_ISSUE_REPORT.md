# TUBA1A Issue Investigation Report

## Executive Summary
TUBA1A (Tubulin Alpha 1a) is incorrectly appearing in the kidney genetics database despite being a brain-related gene. This is caused by a critical difference in panel filtering logic between the old (kidney-genetics-v1) and new (kidney-genetics-db) implementations.

## Problem Statement
TUBA1A, a gene associated with brain malformations and neurodevelopmental disorders, is being included in the kidney genetics database when it should not be, as it has no known kidney disease associations.

## Root Cause Analysis

### 1. Panel Filtering Logic Differences

#### Old Implementation (kidney-genetics-v1)
- **Filter String**: `((?=.*[Kk]idney)|(?=.*[Rr]enal)|(?=.*[Nn]ephro))(^((?!adrenal).)*$)`
- **Logic**:
  - Must contain "kidney" OR "renal" OR "nephro"
  - AND must NOT contain "adrenal"
- **Result**: Only panels with clear kidney-related names are included

#### New Implementation (kidney-genetics-db)
- **Keywords**: Multiple search terms including:
  ```python
  self.kidney_keywords = [
      "kidney", "renal", "nephro", "glomerul", "tubul",  # <- Problem here
      "polycystic", "alport", "nephritis", "cystic",
      "ciliopathy", "complement", "cakut", ...
  ]
  ```
- **Logic**: Searches for panels containing ANY of these keywords
- **Result**: Much broader search that captures non-kidney panels

### 2. The Specific Problem: "tubul" Keyword

The new implementation includes "tubul" as a search keyword, likely intended to capture:
- "Renal tubulopathies" (panel 292)
- "Tubulointerstitial kidney disease" (panel 548)

However, "tubul" also matches **"TUBULIN"** related terms in gene names and descriptions, causing false positives.

### 3. TUBA1A Panel Associations

TUBA1A is found in numerous non-kidney panels including:
- Cerebral malformation (panel 491) - **Green confidence level**
- Adult onset dystonia (panel 540)
- Childhood onset dystonia (panel 847)
- Brain channelopathy (panel 90)
- And many others...

These panels don't match kidney-related keywords, but when searching by keyword fragments, unintended matches occur.

## Implementation Comparison

### Search Strategy
| Aspect | Old Implementation | New Implementation |
|--------|-------------------|-------------------|
| Method | Direct panel name filtering | Keyword-based search |
| Precision | High (regex pattern) | Low (broad keywords) |
| Coverage | Conservative | Aggressive |
| False Positives | Minimal | Significant |

### Key Differences
1. **Regex vs Keyword Lists**: Old uses precise regex, new uses broad keyword matching
2. **Exclusion Logic**: Old explicitly excludes "adrenal", new has no exclusions
3. **Search Scope**: Old filters panel names only, new searches descriptions too

## Impact Analysis

### Genes Incorrectly Included
Based on the search logic, any gene from the following panel types may be incorrectly included:
- Brain/neurological panels (due to descriptions)
- Metabolic panels (may contain "tubul" references)
- Multi-system panels (broad descriptions)

### Data Quality Impact
- **False Positives**: Non-kidney genes appearing in kidney database
- **User Confusion**: Researchers seeing brain-specific genes in kidney gene lists
- **Downstream Analysis**: Potential bias in pathway/enrichment analyses

## Recommended Solutions

### Immediate Fix
```python
# Option 1: Remove problematic keywords
self.kidney_keywords = [
    "kidney", "renal", "nephro", "glomerul",
    # "tubul",  # REMOVED - too broad
    "polycystic", "alport", "nephritis",
    # "cystic",  # Consider removing - too broad
    "ciliopathy", "complement", "cakut",
    # Add more specific terms:
    "tubulopathy", "tubulointerstitial",  # More specific than "tubul"
    "focal segmental", "steroid resistant",
    "nephrotic", "proteinuria", "hematuria"
]
```

### Better Solution - Two-Stage Filtering
```python
# Stage 1: Broad search
panels = search_with_keywords(broad_keywords)

# Stage 2: Strict filtering
kidney_panels = []
for panel in panels:
    if is_truly_kidney_related(panel.name, panel.description):
        kidney_panels.append(panel)

def is_truly_kidney_related(name, description):
    # Implement logic similar to old regex
    # Must have kidney/renal/nephro
    # Exclude known false positives
    # Consider panel categories/tags
```

### Long-term Solution
1. **Use Panel Categories**: PanelApp provides panel categories - use these for filtering
2. **Curated Panel List**: Maintain a whitelist of known kidney-related panel IDs
3. **Gene-Level Filtering**: Even if a panel is included, filter genes by their actual disease associations
4. **Implement Exclusion List**: Maintain list of known false-positive genes

## Validation Steps

### To Verify the Fix
1. After implementing changes, check that:
   - TUBA1A is no longer included
   - Other known brain genes (TUBB2B, TUBB3, etc.) are excluded
   - True kidney genes (PKD1, PKD2, COL4A3-5) remain included

2. Compare gene counts:
   - Old implementation: ~500-600 genes
   - Current implementation: 571+ genes (likely inflated)
   - After fix: Should be closer to old count

### Test Cases
```python
# Should NOT be included
assert "TUBA1A" not in kidney_genes
assert "TUBB2B" not in kidney_genes

# Should be included
assert "PKD1" in kidney_genes
assert "COL4A3" in kidney_genes
assert "NPHS1" in kidney_genes
```

## Conclusion

The TUBA1A inclusion is a symptom of overly broad panel filtering in the new implementation. The keyword "tubul" and potentially others are causing false positives by matching unintended terms. The solution requires more precise filtering logic, similar to the regex-based approach in the original implementation, while maintaining the benefits of the new async architecture.

## Action Items

1. **Immediate**: Remove or refine "tubul" keyword
2. **Short-term**: Implement two-stage filtering
3. **Medium-term**: Add exclusion list for known false positives
4. **Long-term**: Use PanelApp categories/tags for more accurate filtering

---
*Report generated: 2025-09-14*
*Investigated by: Senior Developer & Bioinformatician*