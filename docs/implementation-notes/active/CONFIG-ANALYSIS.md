# Configuration System Analysis - Dashboard Visualizations

## What Already EXISTS in Config (DRY!)

### 📁 `backend/config/datasources.yaml`

**Line 88-93**: Classification weights ALREADY defined!
```yaml
GenCC:
  confidence_categories: [definitive, strong, moderate]
  classification_weights:
    Definitive: 1.0
    Strong: 0.8
    Moderate: 0.6
```

**Line 66**: Min classification setting
```yaml
ClinGen:
  min_classification: Limited
```

### 📁 `backend/config/api_defaults.yaml`

```yaml
api_defaults:
  hide_zero_scores: true
```

### 📁 `backend/config/annotations.yaml`

**Line 54-62**: Review confidence levels
```yaml
ClinVar:
  review_confidence:
    practice guideline: 4
    reviewed by expert panel: 4
    criteria provided, conflicting classifications: 2
    no classification provided: 0
```

---

## What's HARDCODED (DRY Violations to Fix!)

### ❌ `backend/app/pipeline/sources/unified/clingen.py:68-74`

```python
# DUPLICATE! Already in datasources.yaml
self.classification_weights = {
    "Definitive": 1.0,
    "Strong": 0.8,
    "Moderate": 0.6,
    "Limited": 0.3,
    "Disputed": 0.1,
    "Refuted": 0.0,
}
```

**Fix**: Read from config:
```python
from app.core.datasource_config import get_source_parameter

self.classification_weights = get_source_parameter(
    "GenCC",
    "classification_weights",
    {  # Fallback
        "Definitive": 1.0,
        "Strong": 0.8,
        "Moderate": 0.6,
        "Limited": 0.3,
        "Disputed": 0.1,
        "Refuted": 0.0,
    }
)
```

### ❌ `backend/app/crud/statistics.py:400-420`

```python
# HARDCODED tier ranges and labels
CASE
    WHEN percentage_score >= 90 THEN '90-100'
    WHEN percentage_score >= 70 THEN '70-90'
    ...
END

confidence_mapping = {
    "90-100": "Very High Confidence",
    "70-90": "High Confidence",
    ...
}
```

**Fix**: Move to `api_defaults.yaml`!

---

## CORRECT Approach - Use Existing Config System

### Step 1: Add Missing Config to `api_defaults.yaml`

```yaml
api_defaults:
  hide_zero_scores: true

  # Evidence tier configuration for aggregated scores
  evidence_tiers:
    ranges:
      - range: "90-100"
        label: "Very High Confidence"
        threshold: 90
      - range: "70-90"
        label: "High Confidence"
        threshold: 70
      - range: "50-70"
        label: "Medium Confidence"
        threshold: 50
      - range: "30-50"
        label: "Low Confidence"
        threshold: 30
      - range: "0-30"
        label: "Very Low Confidence"
        threshold: 0

  # Source-specific classification labels (for ClinGen/GenCC)
  classification_labels:
    - "Definitive"
    - "Strong"
    - "Moderate"
    - "Limited"
    - "Disputed"
    - "Refuted"
```

### Step 2: Add Missing Weights to `datasources.yaml`

```yaml
GenCC:
  # ... existing config ...
  classification_weights:
    Definitive: 1.0
    Strong: 0.8
    Moderate: 0.6
    Limited: 0.3      # ADD THIS
    Disputed: 0.1     # ADD THIS
    Refuted: 0.0      # ADD THIS
```

### Step 3: Update Code to Read from Config

**`statistics.py`**:
```python
from app.core.datasource_config import API_DEFAULTS_CONFIG

def get_evidence_composition(self, db: Session):
    # Get tier config from YAML
    tier_config = API_DEFAULTS_CONFIG.get("evidence_tiers", {})
    ranges = tier_config.get("ranges", [])

    # Build CASE statement from config
    case_clauses = [
        f"WHEN percentage_score >= {tier['threshold']} THEN '{tier['range']}'"
        for tier in sorted(ranges, key=lambda x: x['threshold'], reverse=True)
    ]

    score_distribution = db.execute(
        text(f"""
            SELECT
                CASE
                    {' '.join(case_clauses)}
                END as score_range,
                COUNT(*) as gene_count
            FROM gene_scores
            ...
        """)
    )

    # Map ranges to labels from config
    confidence_mapping = {
        tier['range']: tier['label']
        for tier in ranges
    }
```

**`clingen.py`**:
```python
from app.core.datasource_config import get_source_parameter

def __init__(self):
    # Read from config, don't hardcode!
    self.classification_weights = get_source_parameter(
        "GenCC",
        "classification_weights",
        {}  # Empty fallback - config should always be present
    )
```

---

## Summary - NO constants.py Needed!

### ✅ Use Existing Config System

1. **Add to `api_defaults.yaml`**: Evidence tiers, ranges, labels
2. **Update `datasources.yaml`**: Complete classification_weights (add Limited, Disputed, Refuted)
3. **Fix existing DRY violations**: ClinGen should read from config
4. **All code reads from config**: No hardcoded values

### ❌ Don't Create

- ~~`constants.py`~~ - Would duplicate config system
- ~~Hardcoded dictionaries~~ - Use `API_DEFAULTS_CONFIG`
- ~~New config patterns~~ - Use established YAML + pydantic-settings

---

## Implementation Plan Revision

### Phase 0 Task 0.1 (REVISED): Extend api_defaults.yaml

**File**: `backend/config/api_defaults.yaml`

Add evidence tier configuration:
```yaml
api_defaults:
  hide_zero_scores: true

  evidence_tiers:
    # Used for aggregated evidence scores (gene_scores view)
    ranges:
      - { range: "90-100", label: "Very High Confidence", threshold: 90, color: "#059669" }
      - { range: "70-90", label: "High Confidence", threshold: 70, color: "#10B981" }
      - { range: "50-70", label: "Medium Confidence", threshold: 50, color: "#34D399" }
      - { range: "30-50", label: "Low Confidence", threshold: 30, color: "#FCD34D" }
      - { range: "0-30", label: "Very Low Confidence", threshold: 0, color: "#F87171" }

    # Filter thresholds for API
    filter_thresholds:
      Very High: 90
      High: 70
      Medium: 50
      Low: 30

  # Source-specific classification order (for ClinGen/GenCC)
  classification_order:
    Definitive: 1
    Strong: 2
    Moderate: 3
    Limited: 4
    Disputed: 5
    Refuted: 6
```

### Phase 0 Task 0.2 (REVISED): Complete datasources.yaml

**File**: `backend/config/datasources.yaml`

```yaml
GenCC:
  # ... existing ...
  classification_weights:
    Definitive: 1.0
    Strong: 0.8
    Moderate: 0.6
    Limited: 0.3      # ADD
    Disputed: 0.1     # ADD
    Refuted: 0.0      # ADD
```

### Phase 0 Task 0.3 (NEW): Fix Existing DRY Violations

**File**: `backend/app/pipeline/sources/unified/clingen.py`

```python
# Line 68-74: REPLACE hardcoded weights
from app.core.datasource_config import get_source_parameter

self.classification_weights = get_source_parameter(
    "GenCC",
    "classification_weights",
    {  # Fallback only if config missing
        "Definitive": 1.0,
        "Strong": 0.8,
        "Moderate": 0.6,
        "Limited": 0.3,
        "Disputed": 0.1,
        "Refuted": 0.0,
    }
)
```

---

## Config Access Patterns (Already Established!)

### Get API defaults:
```python
from app.core.datasource_config import API_DEFAULTS_CONFIG

tier_config = API_DEFAULTS_CONFIG.get("evidence_tiers", {})
hide_zeros = API_DEFAULTS_CONFIG.get("hide_zero_scores", True)
```

### Get source-specific config:
```python
from app.core.datasource_config import get_source_parameter

weights = get_source_parameter("GenCC", "classification_weights", {})
min_class = get_source_parameter("ClinGen", "min_classification", "Limited")
```

### Get all sources:
```python
from app.core.datasource_config import DATA_SOURCE_CONFIG

for source_name, config in DATA_SOURCE_CONFIG.items():
    print(f"{source_name}: {config}")
```

---

**Result**: No new files, no constants.py, just proper use of existing YAML config system! ✅
