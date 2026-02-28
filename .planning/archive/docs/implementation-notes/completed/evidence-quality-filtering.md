# Evidence Quality Filtering - ✅ IMPLEMENTED

**Status:** ✅ Complete
**Implementation Date:** 2025-09-30
**Commit:** `457b9ae` - feat: Add evidence quality filtering with consistent gene counts

---

## Problem
1,884 genes (~38% of database) have `evidence_score = 0`, making the default gene list noisy and hard to use.

## Solution
Added a simple API flag to hide genes with `evidence_score = 0` by default, with centralized filtering logic ensuring consistency across all endpoints.

---

## Implementation

### 1. API Parameter

**File:** `backend/app/api/endpoints/genes.py`

Add new query parameter to `get_genes()`:

```python
hide_zero_scores: bool = Query(
    True,  # Default: hide genes with score=0
    alias="filter[hide_zero_scores]",
    description="Hide genes with evidence_score=0 (default: true)"
)
```

### 2. Filter Logic

Add to WHERE clause:

```python
# Add to where_clauses (around line 112)
if hide_zero_scores:
    where_clauses.append("gs.percentage_score > 0")
```

### 3. Response Metadata

Add counts to meta:

```python
# In response (around line 225)
response["meta"]["total_genes"] = total_in_db  # All genes
response["meta"]["visible_genes"] = total  # After filter
response["meta"]["hidden_zero_scores"] = total_in_db - total if hide_zero_scores else 0
```

### 4. Configuration (Optional)

**File:** `backend/config/api_defaults.yaml` (new file)

```yaml
api_defaults:
  # Hide genes with evidence_score=0 by default
  hide_zero_scores: true

  # Minimum score threshold (future: allow admins to adjust)
  # Currently hardcoded to 0, but could be configured later
  minimum_evidence_score: 0.0
```

Load in `datasource_config.py`:

```python
class DataSourceConfig(BaseSettings):
    # ... existing ...
    api_defaults: dict[str, Any] = {}  # NEW

    @classmethod
    def settings_customise_sources(cls, ...):
        yaml_source = MultiYamlConfigSource(
            settings_cls,
            yaml_files=[
                config_dir / "datasources.yaml",
                config_dir / "keywords.yaml",
                config_dir / "annotations.yaml",
                config_dir / "api_defaults.yaml",  # NEW
            ],
        )
```

Then use in endpoint:

```python
from app.core.datasource_config import get_config

hide_zero_scores: bool = Query(
    default=get_config().api_defaults.get("hide_zero_scores", True),
    alias="filter[hide_zero_scores]"
)
```

---

## API Usage

```bash
# Default: hide genes with score=0 (shows ~3,100 genes)
GET /api/genes

# Show all genes including score=0 (shows ~5,000 genes)
GET /api/genes?filter[hide_zero_scores]=false

# Combine with other filters
GET /api/genes?filter[hide_zero_scores]=false&filter[source]=PubTator
```

---

## Response Format

```json
{
  "data": [...],
  "meta": {
    "total": 3116,
    "total_genes": 5000,
    "visible_genes": 3116,
    "hidden_zero_scores": 1884,
    "page": 1,
    "page_size": 10,
    "filters": {
      "hide_zero_scores": true
    }
  }
}
```

---

## Testing

### Unit Test
```python
def test_hide_zero_scores_default(client):
    """Default should hide genes with score=0"""
    response = client.get("/api/genes")
    data = response.json()

    # All genes should have score > 0
    for gene in data["data"]:
        assert gene["attributes"]["evidence_score"] > 0

    assert data["meta"]["hidden_zero_scores"] > 0

def test_show_zero_scores(client):
    """flag=false should show all genes"""
    response = client.get("/api/genes?filter[hide_zero_scores]=false")
    data = response.json()

    # Should include genes with score=0
    scores = [g["attributes"]["evidence_score"] for g in data["data"]]
    assert 0.0 in scores
```

---

## Frontend Implementation (✅ COMPLETED)

**File:** `frontend/src/components/GeneTable.vue`

Implemented comprehensive UI with:
- Toggle switch: "Show genes with insufficient evidence"
- Visual indicators: Warning chip showing hidden count
- Informative tooltips explaining filter behavior
- Pagination display: "3,112 Genes (1,884 hidden)"
- URL state management: Filter state preserved in query params

**Updated Files:**
- `frontend/src/api/genes.js` - Added `hideZeroScores` parameter
- `frontend/src/components/GeneTable.vue` - Added toggle and visual feedback
- `frontend/src/views/Home.vue` - Updated to "Genes with Evidence"
- `frontend/src/views/DataSources.vue` - Updated terminology
- `frontend/src/components/visualizations/UpSetChart.vue` - Added explanatory tooltip

---

## Future Enhancements

If needed later, could add:
- Configurable minimum score threshold (not just 0)
- Per-source minimum counts
- Evidence quality badges

But for now: **just hide score=0 by default**.

---

## Summary

**Changes:**
1. **Configuration:** `backend/config/api_defaults.yaml` with `hide_zero_scores: true`
2. **Config Loading:** Updated `datasource_config.py` to load API defaults
3. **Centralized Filtering:** Created `app/core/gene_filters.py` with reusable helpers:
   - `should_hide_zero_scores()` - Reads config, determines filter state
   - `get_gene_score_filter_clause()` - Returns WHERE clause for gene_scores joins
   - `get_gene_evidence_filter_join()` - Returns JOIN + WHERE for gene_evidence queries
   - `count_filtered_genes_sql()` - Complete SQL for counting genes
   - `count_filtered_genes_from_evidence_sql()` - SQL for counting from evidence table
4. **API Endpoints Updated:**
   - `/api/genes` - Added `filter[hide_zero_scores]` parameter
   - `/api/datasources/` - Updated gene count queries to use filtering
5. **Statistics CRUD:** Updated `app/crud/statistics.py` to use centralized helpers in:
   - `get_source_overlaps()` - Filters gene intersections by score
   - `get_source_distributions()` - Filters all distribution queries:
     - PanelApp: Panel count distributions with score filtering
     - PubTator: Publication count distributions with score filtering
     - DiagnosticPanels: Panel count distributions with score filtering
     - Generic sources (ClinGen, GenCC, HPO): Evidence counts with score filtering
6. **Response Metadata:** Added `total_genes`, `hidden_zero_scores` counts

**Result:**
- Default gene list: **3,112 genes** (down from 4,996)
- Hides **1,884 genes** with score=0
- **Consistent across ALL endpoints** - dashboard, gene list, statistics all show 3,112
- Users can toggle via `?filter[hide_zero_scores]=false`
- **Single source of truth** - all filtering logic in one place
- **All distribution queries filtered** - ensures accurate visualization statistics
- Simple, clean, DRY, configurable

**No database changes. No complex logic. Centralized helper functions ensure consistency.**

**Verification:**
```bash
# Genes endpoint
curl "http://localhost:8000/api/genes?page[size]=1" | jq '.meta.total'
# Returns: 3112

# Statistics summary
curl "http://localhost:8000/api/statistics/summary" | jq '.data.overview.total_genes'
# Returns: 3112

# ✓ Consistent!
```