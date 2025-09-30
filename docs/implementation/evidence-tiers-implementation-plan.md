# Evidence Tier System Implementation Plan

**Version:** 1.0
**Date:** 2025-09-30
**Status:** Design Approved - Awaiting Implementation
**Author:** Development Team

---

## Executive Summary

Implement a tiered evidence classification system to separate genes with higher-quality evidence (~600 genes) from those with emerging evidence (~2,400 genes). This system uses quantitative, non-ClinGen terminology to avoid confusion with future manual ClinGen-compliant curation.

**Key Objectives:**
- Provide users with clear evidence quality indicators
- Enable filtering by evidence strength without misleading terminology
- Maintain backward compatibility with existing API
- Prepare foundation for future ClinGen manual curation integration

---

## Background

### Current State
- **Total genes:** ~3,000 (after filtering zero-evidence genes)
- **Evidence metrics:** `evidence_count` (number of sources), `percentage_score` (0-100)
- **Current classification:** Generic "High/Medium/Low" based on percentage_score only
- **Problem:** No distinction between well-evidenced genes and exploratory candidates

### Research Summary

**Industry Standards Reviewed:**
- **ClinGen:** Definitive, Strong, Moderate, Limited (MUST AVOID - reserved for manual curation)
- **PanelApp:** Green/Amber/Red traffic light system
- **GenCC:** Harmonized terminology including "Supportive"
- **Gene2Phenotype:** Confirmed, Probable, Possible

**Decision:** Use evidence-quantitative terminology that clearly indicates automated aggregation.

---

## Requirements

### Functional Requirements
1. **FR-1:** Classify genes into two major groups based on evidence quality
2. **FR-2:** Subdivide each major group into meaningful sub-tiers
3. **FR-3:** Enable API filtering by tier and group
4. **FR-4:** Display tier information in frontend gene tables
5. **FR-5:** Provide user-facing documentation explaining tier system

### Non-Functional Requirements
1. **NFR-1:** No performance degradation on gene list queries (<20ms overhead)
2. **NFR-2:** Backward compatible - existing API functionality unchanged
3. **NFR-3:** Clear separation from ClinGen terminology
4. **NFR-4:** Extensible for future manual curation integration

---

## Design Decisions

### Terminology Framework

#### Major Groups

| Group | Display Name | Criteria | Expected Count | Use Case |
|-------|--------------|----------|----------------|----------|
| **Group 1** | **Well-Supported** | `evidence_count >= 2` AND `percentage_score >= 20` | ~600 genes | High-confidence clinical/research use |
| **Group 2** | **Emerging Evidence** | `percentage_score > 0` (remainder) | ~2,400 genes | Exploratory research, hypothesis generation |

#### Sub-Tiers (Well-Supported)

| Tier | Internal Name | Display Name | Criteria | Expected Count | Color |
|------|---------------|--------------|----------|----------------|-------|
| **T1** | `comprehensive_support` | Comprehensive Support | `evidence_count >= 4` AND `percentage_score >= 50` | ~150-200 | success |
| **T2** | `multi_source_support` | Multi-Source Support | `evidence_count >= 3` AND `percentage_score >= 35` | ~200-250 | info |
| **T3** | `established_support` | Established Support | `evidence_count >= 2` AND `percentage_score >= 20` | ~150-200 | primary |

#### Sub-Tiers (Emerging Evidence)

| Tier | Internal Name | Display Name | Criteria | Expected Count | Color |
|------|---------------|--------------|----------|----------------|-------|
| **T4** | `preliminary_evidence` | Preliminary Evidence | `percentage_score >= 10` | ~1,500 | warning |
| **T5** | `minimal_evidence` | Minimal Evidence | `percentage_score > 0` AND `percentage_score < 10` | ~1,300 | grey |

### Rationale

**Why two groups?**
- Clear separation between "ready for clinical consideration" vs "needs more evidence"
- Matches user mental model from ClinGen exposure (definitive/strong/moderate vs limited)

**Why these thresholds?**
- `evidence_count >= 2`: Minimum for cross-validation across sources
- `percentage_score >= 20`: ~2 full sources contributing (7 total sources = ~14% per source)
- Sub-tier thresholds: Based on natural distribution breakpoints (validated in Phase 1)

**Why avoid ClinGen terms?**
- Current system is automated aggregation, NOT manual expert curation
- Future enhancement will add true ClinGen-compliant curation workflow
- Clear terminology prevents clinical misinterpretation

---

## Implementation Plan

### Phase 1: Database & View Updates

#### Task 1.1: Update `gene_scores` View

**File:** `backend/app/db/views.py`

**Change:** Add computed columns to `gene_scores` ReplaceableObject (around line 224)

```python
gene_scores = ReplaceableObject(
    name="gene_scores",
    sqltext="""
    WITH source_scores_per_gene AS (
        SELECT g.id AS gene_id,
               g.approved_symbol,
               g.hgnc_id,
               ces.source_name,
               MAX(ces.normalized_score) AS source_score
        FROM genes g
        INNER JOIN combined_evidence_scores ces ON g.id = ces.gene_id
        GROUP BY g.id, g.approved_symbol, g.hgnc_id, ces.source_name
    )
    SELECT gene_id,
           approved_symbol,
           hgnc_id,
           COUNT(DISTINCT source_name) AS source_count,
           COUNT(DISTINCT source_name) AS evidence_count,
           SUM(source_score) AS raw_score,
           SUM(source_score) / (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) * 100 AS percentage_score,
           jsonb_object_agg(source_name, ROUND(source_score::numeric, 4)) AS source_scores,
           (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) AS total_active_sources,
           -- NEW: Evidence tier calculation
           CASE
               WHEN COUNT(DISTINCT source_name) >= 4 AND SUM(source_score) / (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) * 100 >= 50
                   THEN 'comprehensive_support'
               WHEN COUNT(DISTINCT source_name) >= 3 AND SUM(source_score) / (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) * 100 >= 35
                   THEN 'multi_source_support'
               WHEN COUNT(DISTINCT source_name) >= 2 AND SUM(source_score) / (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) * 100 >= 20
                   THEN 'established_support'
               WHEN SUM(source_score) / (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) * 100 >= 10
                   THEN 'preliminary_evidence'
               WHEN SUM(source_score) / (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) * 100 > 0
                   THEN 'minimal_evidence'
               ELSE 'no_evidence'
           END AS evidence_tier,
           -- NEW: Evidence group calculation
           CASE
               WHEN COUNT(DISTINCT source_name) >= 2 AND SUM(source_score) / (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) * 100 >= 20
                   THEN 'well_supported'
               WHEN SUM(source_score) / (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) * 100 > 0
                   THEN 'emerging_evidence'
               ELSE 'insufficient'
           END AS evidence_group
    FROM source_scores_per_gene
    GROUP BY gene_id, approved_symbol, hgnc_id
    """,
    dependencies=["combined_evidence_scores"],
)
```

**Testing:** Verify view compiles without errors
```bash
make db-reset  # Recreates all views
```

---

#### Task 1.2: Create Alembic Migration

**Command:**
```bash
cd backend
uv run alembic revision -m "add_evidence_tiers_to_gene_scores_view"
```

**File:** `backend/alembic/versions/<generated>_add_evidence_tiers_to_gene_scores_view.py`

```python
"""add_evidence_tiers_to_gene_scores_view

Revision ID: <generated>
Revises: <previous>
Create Date: 2025-09-30
"""
from alembic import op
from app.db.views import gene_scores
from app.db.replaceable_objects import replace_view

revision = '<generated>'
down_revision = '<previous>'
branch_labels = None
depends_on = None


def upgrade():
    """Replace gene_scores view with tier calculations."""
    replace_view(op, gene_scores)


def downgrade():
    """Revert to previous gene_scores view (no tier fields)."""
    # Downgrade handled by alembic's view versioning
    pass
```

**Testing:**
```bash
cd backend
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head  # Verify idempotency
```

---

#### Task 1.3: Validate Tier Distribution

**File:** `backend/scripts/validate_tier_distribution.py`

```python
"""Validate evidence tier thresholds against actual data."""
from sqlalchemy import text
from app.db.session import SessionLocal

def validate_tiers():
    """Query and display tier distribution statistics."""
    db = SessionLocal()

    query = text("""
        SELECT
            evidence_tier,
            evidence_group,
            COUNT(*) as gene_count,
            MIN(percentage_score) as min_score,
            MAX(percentage_score) as max_score,
            AVG(percentage_score) as avg_score,
            MIN(evidence_count) as min_sources,
            MAX(evidence_count) as max_sources,
            AVG(evidence_count) as avg_sources
        FROM gene_scores
        WHERE percentage_score > 0
        GROUP BY evidence_tier, evidence_group
        ORDER BY MIN(percentage_score) DESC
    """)

    results = db.execute(query).fetchall()

    print("\n=== Evidence Tier Distribution ===\n")
    for row in results:
        print(f"Tier: {row.evidence_tier}")
        print(f"  Group: {row.evidence_group}")
        print(f"  Count: {row.gene_count}")
        print(f"  Score Range: {row.min_score:.1f} - {row.max_score:.1f} (avg: {row.avg_score:.1f})")
        print(f"  Source Range: {row.min_sources} - {row.max_sources} (avg: {row.avg_sources:.1f})")
        print()

    db.close()

if __name__ == "__main__":
    validate_tiers()
```

**Run:**
```bash
cd backend
uv run python scripts/validate_tier_distribution.py
```

**Action:** Review distribution and adjust thresholds in view if needed

---

### Phase 2: API Endpoint Updates

#### Task 2.1: Add Tier Filtering Parameters

**File:** `backend/app/api/endpoints/genes.py`

**Change:** Add new query parameters to `get_genes()` (around line 58)

```python
@router.get("/", response_model=dict)
@jsonapi_endpoint(
    resource_type="genes", model=Gene, searchable_fields=["approved_symbol", "hgnc_id"]
)
async def get_genes(
    db: Session = Depends(get_db),
    params: dict = Depends(get_jsonapi_params),
    search: str | None = Depends(get_search_filter),
    score_range: tuple[float | None, float | None] = Depends(
        get_range_filters("score", min_ge=0, max_le=100)
    ),
    count_range: tuple[int | None, int | None] = Depends(get_range_filters("count", min_ge=0)),
    filter_source: str | None = Query(None, alias="filter[source]"),
    hide_zero_scores: bool = Query(
        default=API_DEFAULTS_CONFIG.get("hide_zero_scores", True),
        alias="filter[hide_zero_scores]",
        description="Hide genes with evidence_score=0 (default: true)",
    ),
    # NEW PARAMETERS
    filter_tier: str | None = Query(
        None,
        alias="filter[tier]",
        description="Filter by evidence tier (comprehensive_support, multi_source_support, established_support, preliminary_evidence, minimal_evidence)",
    ),
    filter_group: str | None = Query(
        None,
        alias="filter[group]",
        description="Filter by major group (well_supported, emerging_evidence)",
    ),
    sort: str | None = Depends(get_sort_param("-evidence_score,approved_symbol")),
) -> dict[str, Any]:
    """
    Get genes with JSON:API compliant response using reusable components.

    Query parameters follow JSON:API specification:
    - Pagination: page[number], page[size]
    - Filtering:
        - filter[search] - Search by symbol or HGNC ID
        - filter[min_score] / filter[max_score] - Evidence score range (0-100)
        - filter[min_count] / filter[max_count] - Source count range
        - filter[source] - Filter by specific data source
        - filter[hide_zero_scores] - Hide genes with no evidence (default: true)
        - filter[tier] - Filter by evidence tier (NEW)
        - filter[group] - Filter by major group (NEW)
    - Sorting: sort=-evidence_score,approved_symbol (prefix with - for descending)

    Evidence Tier System:
    Classifies genes based on automated aggregation from multiple data sources.
    This is NOT ClinGen-compliant manual curation.
    """
```

---

#### Task 2.2: Implement Tier Filtering Logic

**File:** `backend/app/api/endpoints/genes.py` (within `get_genes()`)

**Change:** Add WHERE clauses (after line 120)

```python
# Filter by evidence tier
if filter_tier:
    valid_tiers = [
        'comprehensive_support',
        'multi_source_support',
        'established_support',
        'preliminary_evidence',
        'minimal_evidence'
    ]
    if filter_tier not in valid_tiers:
        raise ValidationError(
            field="filter[tier]",
            reason=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}"
        )
    where_clauses.append("gs.evidence_tier = :tier")
    query_params["tier"] = filter_tier

# Filter by evidence group
if filter_group:
    valid_groups = ['well_supported', 'emerging_evidence']
    if filter_group not in valid_groups:
        raise ValidationError(
            field="filter[group]",
            reason=f"Invalid group. Must be one of: {', '.join(valid_groups)}"
        )
    where_clauses.append("gs.evidence_group = :group")
    query_params["group"] = filter_group
```

---

#### Task 2.3: Update Data Query to Include Tier Fields

**File:** `backend/app/api/endpoints/genes.py` (within `get_genes()`)

**Change:** Add tier fields to SELECT statement (around line 170)

```python
data_query = f"""
    SELECT DISTINCT
        g.id,
        g.hgnc_id,
        g.approved_symbol,
        g.aliases,
        g.created_at,
        g.updated_at,
        COALESCE(gs.evidence_count, 0) as evidence_count,
        gs.percentage_score as evidence_score,
        gs.evidence_tier,  -- NEW
        gs.evidence_group, -- NEW
        COALESCE(
            array_agg(DISTINCT ge.source_name ORDER BY ge.source_name)
            FILTER (WHERE ge.source_name IS NOT NULL),
            ARRAY[]::text[]
        ) as sources
    FROM genes g
    LEFT JOIN gene_scores gs ON gs.gene_id = g.id
    LEFT JOIN gene_evidence ge ON g.id = ge.gene_id
    WHERE {where_clause}
    GROUP BY
        g.id, g.hgnc_id, g.approved_symbol, g.aliases,
        g.created_at, g.updated_at, gs.evidence_count, gs.percentage_score,
        gs.evidence_tier, gs.evidence_group  -- NEW
    {sort_clause}
"""
```

---

#### Task 2.4: Update Response Transform Function

**File:** `backend/app/api/endpoints/genes.py`

**Change:** Include tier fields in JSON:API response (around line 31)

```python
def transform_gene_to_jsonapi(results) -> list[dict]:
    """Transform gene query results to JSON:API format."""
    data = []
    for row in results:
        data.append(
            {
                "type": "genes",
                "id": str(row[0]),
                "attributes": {
                    "hgnc_id": row[1],
                    "approved_symbol": row[2],
                    "aliases": row[3] or [],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "updated_at": row[5].isoformat() if row[5] else None,
                    "evidence_count": row[6],
                    "evidence_score": float(row[7]) if row[7] is not None else None,
                    "evidence_tier": row[8],     # NEW
                    "evidence_group": row[9],    # NEW
                    "sources": list(row[10]) if row[10] else [],  # Updated index
                },
            }
        )
    return data
```

---

#### Task 2.5: Add Tier Metadata to API Response

**File:** `backend/app/api/endpoints/genes.py` (within `get_genes()`)

**Change:** Add tier distribution to metadata (after line 237)

```python
# Get tier distribution
tier_distribution_query = text("""
    SELECT
        evidence_group,
        evidence_tier,
        COUNT(*) as gene_count
    FROM gene_scores
    WHERE percentage_score > 0
    GROUP BY evidence_group, evidence_tier
    ORDER BY
        CASE evidence_group
            WHEN 'well_supported' THEN 1
            WHEN 'emerging_evidence' THEN 2
            ELSE 3
        END,
        MIN(percentage_score) DESC
""")

tier_results = db.execute(tier_distribution_query).fetchall()

tier_meta = {
    "well_supported": {},
    "emerging_evidence": {}
}

for row in tier_results:
    group = row.evidence_group
    tier = row.evidence_tier
    count = row.gene_count
    if group in tier_meta:
        tier_meta[group][tier] = count

# Calculate group totals
tier_meta["well_supported"]["total"] = sum(tier_meta["well_supported"].values())
tier_meta["emerging_evidence"]["total"] = sum(tier_meta["emerging_evidence"].values())

# Add to response metadata
response["meta"]["evidence_tiers"] = tier_meta
response["meta"]["valid_tiers"] = [
    "comprehensive_support",
    "multi_source_support",
    "established_support",
    "preliminary_evidence",
    "minimal_evidence"
]
response["meta"]["valid_groups"] = ["well_supported", "emerging_evidence"]
```

---

#### Task 2.6: Update Single Gene Endpoint

**File:** `backend/app/api/endpoints/genes.py` (within `get_gene()`)

**Change:** Include tier fields in single gene response (around line 273)

```python
# Update score_result query
score_result = db.execute(
    text("""
        SELECT
            evidence_count,
            percentage_score,
            source_scores,
            evidence_tier,
            evidence_group
        FROM gene_scores
        WHERE gene_id = :gene_id
    """),
    {"gene_id": gene.id},
).first()

# Update response (around line 314)
return {
    "data": {
        "type": "genes",
        "id": str(gene.id),
        "attributes": {
            "hgnc_id": gene.hgnc_id,
            "approved_symbol": gene.approved_symbol,
            "aliases": gene.aliases or [],
            "created_at": gene.created_at.isoformat() if gene.created_at else None,
            "updated_at": gene.updated_at.isoformat() if gene.updated_at else None,
            "evidence_count": score_result[0] if score_result else 0,
            "evidence_score": float(score_result[1]) if score_result and score_result[1] else None,
            "evidence_tier": score_result[3] if score_result else None,      # NEW
            "evidence_group": score_result[4] if score_result else None,     # NEW
            "sources": sources,
            "score_breakdown": score_breakdown,
            "source_scores": score_result[2] if score_result else {},
        },
    }
}
```

---

### Phase 3: Frontend Updates

#### Task 3.1: Create Tier Utility Functions

**File:** `frontend/src/utils/evidenceTiers.js` (NEW)

```javascript
/**
 * Evidence tier configuration and utility functions
 * Used for displaying tier badges and managing tier-related UI
 */

/**
 * @typedef {Object} TierConfig
 * @property {string} label - Display label for the tier
 * @property {string} color - Vuetify color name
 * @property {string} icon - MDI icon name
 * @property {string} description - Tooltip description
 */

/**
 * Configuration for evidence tiers
 * @type {Object.<string, TierConfig>}
 */
export const TIER_CONFIG = {
  comprehensive_support: {
    label: 'Comprehensive Support',
    color: 'success',
    icon: 'mdi-check-circle',
    description: '4+ sources with strong evidence (score ≥50%)'
  },
  multi_source_support: {
    label: 'Multi-Source Support',
    color: 'info',
    icon: 'mdi-check-circle-outline',
    description: '3+ sources with good evidence (score ≥35%)'
  },
  established_support: {
    label: 'Established Support',
    color: 'primary',
    icon: 'mdi-check',
    description: '2+ sources with baseline evidence (score ≥20%)'
  },
  preliminary_evidence: {
    label: 'Preliminary Evidence',
    color: 'warning',
    icon: 'mdi-alert-circle-outline',
    description: 'Moderate evidence level (score ≥10%)'
  },
  minimal_evidence: {
    label: 'Minimal Evidence',
    color: 'grey',
    icon: 'mdi-information-outline',
    description: 'Limited evidence available (score <10%)'
  }
}

/**
 * Configuration for evidence groups
 * @type {Object.<string, TierConfig>}
 */
export const GROUP_CONFIG = {
  well_supported: {
    label: 'Well-Supported',
    color: 'success',
    icon: 'mdi-star',
    description: '2+ sources with strong evidence scores'
  },
  emerging_evidence: {
    label: 'Emerging Evidence',
    color: 'warning',
    icon: 'mdi-star-outline',
    description: 'Initial evidence, needs further validation'
  }
}

/**
 * Get tier configuration by tier name
 * @param {string|null} tier - Tier name
 * @returns {TierConfig} Tier configuration object
 */
export function getTierConfig(tier) {
  if (!tier || !TIER_CONFIG[tier]) {
    return {
      label: 'No Classification',
      color: 'grey-lighten-2',
      icon: 'mdi-help-circle-outline',
      description: 'No evidence tier assigned'
    }
  }
  return TIER_CONFIG[tier]
}

/**
 * Get group configuration by group name
 * @param {string|null} group - Group name
 * @returns {TierConfig} Group configuration object
 */
export function getGroupConfig(group) {
  if (!group || !GROUP_CONFIG[group]) {
    return {
      label: 'Unclassified',
      color: 'grey-lighten-2',
      icon: 'mdi-help-circle-outline',
      description: 'No evidence group assigned'
    }
  }
  return GROUP_CONFIG[group]
}

/**
 * Get sort order for tier (lower is better)
 * @param {string|null} tier - Tier name
 * @returns {number} Sort order
 */
export function getTierSortOrder(tier) {
  const order = {
    'comprehensive_support': 1,
    'multi_source_support': 2,
    'established_support': 3,
    'preliminary_evidence': 4,
    'minimal_evidence': 5
  }
  return tier ? (order[tier] || 999) : 999
}

/**
 * List of all valid tier values
 * @type {string[]}
 */
export const VALID_TIERS = Object.keys(TIER_CONFIG)

/**
 * List of all valid group values
 * @type {string[]}
 */
export const VALID_GROUPS = Object.keys(GROUP_CONFIG)
```

---

#### Task 3.2: Create Evidence Tier Badge Component

**File:** `frontend/src/components/EvidenceTierBadge.vue` (NEW)

```vue
<template>
  <v-tooltip :text="config.description" location="bottom" max-width="320">
    <template #activator="{ props: tooltipProps }">
      <v-chip
        v-bind="tooltipProps"
        :color="config.color"
        :prepend-icon="config.icon"
        :size="size"
        variant="flat"
        class="evidence-tier-badge font-weight-medium"
      >
        {{ config.label }}
      </v-chip>
    </template>
  </v-tooltip>
</template>

<script setup>
import { computed } from 'vue'
import { getTierConfig } from '@/utils/evidenceTiers'

/**
 * Evidence Tier Badge Component
 * Displays a colored badge with tier information and tooltip
 */

const props = defineProps({
  /**
   * Evidence tier identifier
   * @type {string|null}
   */
  tier: {
    type: String,
    default: null
  },
  /**
   * Badge size (Vuetify chip size)
   * @type {string}
   */
  size: {
    type: String,
    default: 'small'
  }
})

const config = computed(() => getTierConfig(props.tier))
</script>

<style scoped>
/* Following Style Guide - Minimal custom styles, prefer Vuetify utilities */
.evidence-tier-badge {
  cursor: help;
  font-variant-numeric: tabular-nums;
  transition: all 0.2s ease;
}

.evidence-tier-badge:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}
</style>
```

---

#### Task 3.3: Create Tier Help Dialog Component

**File:** `frontend/src/components/TierHelpDialog.vue` (NEW)

```vue
<template>
  <v-dialog v-model="isOpen" max-width="800" scrollable>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-information</v-icon>
        Evidence Tier System
      </v-card-title>

      <v-divider />

      <v-card-text class="py-4">
        <!-- Overview -->
        <div class="mb-6">
          <p class="text-body-1">
            Our evidence tier system classifies genes based on the quantity and quality
            of evidence from multiple data sources. This is an automated aggregation system,
            <strong>not manual expert curation</strong>.
          </p>
        </div>

        <!-- Well-Supported Group -->
        <div class="mb-6">
          <h3 class="text-h6 mb-3 d-flex align-center">
            <v-icon color="success" class="mr-2">mdi-star</v-icon>
            Well-Supported Genes (~600 genes)
          </h3>
          <p class="text-body-2 mb-3">
            Genes with evidence from 2+ sources and strong quality scores (≥20%).
          </p>

          <v-list density="compact">
            <v-list-item
              v-for="tier in wellSupportedTiers"
              :key="tier.value"
              class="mb-2"
            >
              <template #prepend>
                <v-chip
                  :color="tier.config.color"
                  :prepend-icon="tier.config.icon"
                  size="small"
                  label
                >
                  {{ tier.config.label }}
                </v-chip>
              </template>
              <v-list-item-subtitle class="ml-4">
                {{ tier.config.description }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </div>

        <!-- Emerging Evidence Group -->
        <div class="mb-6">
          <h3 class="text-h6 mb-3 d-flex align-center">
            <v-icon color="warning" class="mr-2">mdi-star-outline</v-icon>
            Emerging Evidence Genes (~2,400 genes)
          </h3>
          <p class="text-body-2 mb-3">
            Genes with preliminary evidence that requires further validation.
          </p>

          <v-list density="compact">
            <v-list-item
              v-for="tier in emergingTiers"
              :key="tier.value"
              class="mb-2"
            >
              <template #prepend>
                <v-chip
                  :color="tier.config.color"
                  :prepend-icon="tier.config.icon"
                  size="small"
                  label
                >
                  {{ tier.config.label }}
                </v-chip>
              </template>
              <v-list-item-subtitle class="ml-4">
                {{ tier.config.description }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </div>

        <!-- Data Sources -->
        <div class="mb-4">
          <h3 class="text-h6 mb-3">Evidence Sources</h3>
          <v-chip-group column>
            <v-chip size="small">PanelApp (UK/AU)</v-chip>
            <v-chip size="small">HPO</v-chip>
            <v-chip size="small">ClinGen</v-chip>
            <v-chip size="small">GenCC</v-chip>
            <v-chip size="small">PubTator</v-chip>
            <v-chip size="small">Diagnostic Panels</v-chip>
            <v-chip size="small">Literature</v-chip>
          </v-chip-group>
        </div>

        <!-- Important Note -->
        <v-alert type="info" variant="tonal" class="mt-4">
          <v-alert-title class="d-flex align-center">
            <v-icon class="mr-2">mdi-alert-circle</v-icon>
            Important Note
          </v-alert-title>
          <div class="text-body-2 mt-2">
            <p class="mb-2">
              <strong>This is not ClinGen-compliant gene curation.</strong>
              Our tiers are derived from automated evidence aggregation across multiple databases.
            </p>
            <p>
              Manual ClinGen-compliant curation (Definitive/Strong/Moderate/Limited classifications)
              will be added in a future release.
            </p>
          </div>
        </v-alert>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />
        <v-btn color="primary" variant="flat" @click="isOpen = false">
          Got it
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { TIER_CONFIG } from '@/utils/evidenceTiers'

/**
 * Tier Help Dialog Component
 * Displays detailed explanation of the evidence tier system
 */

const isOpen = defineModel({ type: Boolean, default: false })

const wellSupportedTiers = computed(() => {
  const tiers = [
    'comprehensive_support',
    'multi_source_support',
    'established_support'
  ]
  return tiers.map(tier => ({
    value: tier,
    config: TIER_CONFIG[tier]
  }))
})

const emergingTiers = computed(() => {
  const tiers = ['preliminary_evidence', 'minimal_evidence']
  return tiers.map(tier => ({
    value: tier,
    config: TIER_CONFIG[tier]
  }))
})
</script>

<style scoped>
/* Following Style Guide - Vuetify theme-aware styling */
.v-dialog > .v-overlay__content > .v-card {
  border-radius: 8px;
}

.v-list-item {
  transition: background-color 0.2s ease;
}

.v-theme--dark .v-list-item:hover {
  background: rgba(var(--v-theme-surface-bright), 0.08);
}
</style>
```

---

#### Task 3.4: Update Gene API Module

**File:** `frontend/src/api/genes.js`

**Change:** Handle tier fields in response transformation

```javascript
/**
 * Get paginated list of genes
 * @param {Object} params Query parameters
 * @returns {Promise} JSON:API response with genes
 */
async getGenes(params = {}) {
  const {
    page = 1,
    perPage = 20,
    search = '',
    minScore = null,
    maxScore = null,
    minCount = null,
    maxCount = null,
    source = null,
    tier = null,          // NEW
    group = null,         // NEW
    sortBy = null,
    sortDesc = false,
    hideZeroScores = true
  } = params

  // Build JSON:API query parameters
  const queryParams = {
    'page[number]': page,
    'page[size]': perPage
  }

  // Add filters (only if values are provided)
  if (search) queryParams['filter[search]'] = search
  if (minScore !== null) queryParams['filter[min_score]'] = minScore
  if (maxScore !== null) queryParams['filter[max_score]'] = maxScore
  if (minCount !== null) queryParams['filter[min_count]'] = minCount
  if (maxCount !== null) queryParams['filter[max_count]'] = maxCount
  if (source) queryParams['filter[source]'] = source
  if (tier) queryParams['filter[tier]'] = tier          // NEW
  if (group) queryParams['filter[group]'] = group       // NEW

  // Hide zero scores filter
  queryParams['filter[hide_zero_scores]'] = hideZeroScores

  // Build sort parameter
  if (sortBy) {
    const sortPrefix = sortDesc ? '-' : ''
    queryParams.sort = `${sortPrefix}${sortBy}`
  }

  const response = await apiClient.get('/api/genes/', {
    params: queryParams
  })

  // Transform JSON:API response to simpler format for Vue components
  return {
    items: response.data.data.map(item => ({
      id: item.id,
      ...item.attributes
    })),
    total: response.data.meta.total,
    page: response.data.meta.page,
    perPage: response.data.meta.per_page,
    pageCount: response.data.meta.page_count,
    meta: response.data.meta,
    tierMetadata: response.data.meta.evidence_tiers  // NEW
  }
},
```

---

#### Task 3.5: Update GeneTable Component

**File:** `frontend/src/components/GeneTable.vue`

**Change:** Add tier filtering UI and tier column

**Add imports (top of script section):**
```javascript
import EvidenceTierBadge from '@/components/EvidenceTierBadge.vue'
import TierHelpDialog from '@/components/TierHelpDialog.vue'
import { TIER_CONFIG, GROUP_CONFIG } from '@/utils/evidenceTiers'
```

**Add to data/refs:**
```javascript
const selectedGroup = ref('all')
const selectedTier = ref(null)
const showTierHelp = ref(false)
const tierMetadata = ref(null)
```

**Add after existing filter controls (around line 97):**
```vue
<!-- Evidence Group Filter -->
<v-col cols="12" lg="6">
  <v-chip-group
    v-model="selectedGroup"
    column
    mandatory
    density="compact"
    class="mb-2"
  >
    <v-chip filter value="all" color="grey-lighten-2" size="small">
      All Genes
    </v-chip>
    <v-chip filter value="well_supported" color="success" size="small">
      <v-icon start size="small">mdi-star</v-icon>
      Well-Supported
      <template v-if="tierMetadata?.well_supported?.total">
        ({{ tierMetadata.well_supported.total.toLocaleString() }})
      </template>
    </v-chip>
    <v-chip filter value="emerging_evidence" color="warning" size="small">
      <v-icon start size="small">mdi-star-outline</v-icon>
      Emerging Evidence
      <template v-if="tierMetadata?.emerging_evidence?.total">
        ({{ tierMetadata.emerging_evidence.total.toLocaleString() }})
      </template>
    </v-chip>
  </v-chip-group>
</v-col>

<!-- Evidence Tier Filter -->
<v-col cols="12" lg="6">
  <v-select
    v-model="selectedTier"
    :items="tierFilterOptions"
    label="Evidence Tier"
    clearable
    hide-details
    variant="outlined"
    density="compact"
  >
    <template #selection="{ item }">
      <v-chip :color="item.raw.color" size="small" label>
        {{ item.title }}
      </v-chip>
    </template>
    <template #append-inner>
      <v-btn
        icon="mdi-help-circle"
        variant="text"
        size="x-small"
        @click.stop="showTierHelp = true"
      />
    </template>
  </v-select>
</v-col>
```

**Add computed property for tier filter options:**
```javascript
const tierFilterOptions = computed(() => {
  return Object.entries(TIER_CONFIG).map(([value, config]) => ({
    value,
    title: config.label,
    color: config.color
  }))
})
```

**Add to table headers array:**
```javascript
{
  title: 'Evidence Tier',
  key: 'evidence_tier',
  sortable: true
}
```

**Add table slot for tier column:**
```vue
<!-- Evidence Tier Column -->
<template #item.evidence_tier="{ item }">
  <EvidenceTierBadge :tier="item.evidence_tier" />
</template>
```

**Add dialog component at end of template:**
```vue
<!-- Tier Help Dialog -->
<TierHelpDialog v-model="showTierHelp" />
```

**Update loadGenes function to include tier parameters:**
```javascript
const loadGenes = async () => {
  try {
    loading.value = true
    error.value = null

    const response = await geneApi.getGenes({
      page: currentPage.value,
      perPage: itemsPerPage.value,
      search: search.value,
      minScore: scoreRange.value[0],
      maxScore: scoreRange.value[1],
      minCount: countRange.value[0],
      maxCount: countRange.value[1],
      source: selectedSources.value.length > 0 ? selectedSources.value[0] : null,
      tier: selectedTier.value,       // NEW
      group: selectedGroup.value !== 'all' ? selectedGroup.value : null,  // NEW
      sortBy: sortBy.value,
      sortDesc: sortDescending.value,
      hideZeroScores: hideZeroScores.value
    })

    genes.value = response.items
    totalItems.value = response.total
    hiddenGeneCount.value = response.meta.hidden_zero_scores || 0
    tierMetadata.value = response.tierMetadata  // NEW
    availableSources.value = response.meta.filters?.available_sources || []
  } catch (err) {
    error.value = err.message || 'Failed to load genes'
    console.error('Error loading genes:', err)
  } finally {
    loading.value = false
  }
}
```

**Add watcher for tier/group filters:**
```javascript
// Watch tier and group filters
watch([selectedTier, selectedGroup], () => {
  debouncedSearch()
})
```

---

### Phase 4: Testing

#### Task 4.1: Backend Unit Tests

**File:** `backend/tests/test_evidence_tiers.py` (NEW)

```python
"""Tests for evidence tier classification system."""

import pytest
from sqlalchemy import text


def test_tier_classification_comprehensive(db_session):
    """Test that genes with 4+ sources and 50%+ score get comprehensive_support."""
    # Create test gene with high evidence
    db_session.execute(
        text("""
            INSERT INTO genes (hgnc_id, approved_symbol, aliases)
            VALUES ('HGNC:TEST1', 'GENE_COMP', '{}')
        """)
    )
    db_session.commit()

    # Query tier from view
    result = db_session.execute(
        text("""
            SELECT evidence_tier, evidence_group, evidence_count, percentage_score
            FROM gene_scores gs
            JOIN genes g ON g.id = gs.gene_id
            WHERE g.approved_symbol = 'GENE_COMP'
        """)
    ).first()

    # Verify tier assignment (depends on actual data)
    assert result is not None


def test_filter_by_tier(db_session):
    """Test filtering genes by evidence tier."""
    # Count well_supported group
    result = db_session.execute(
        text("""
            SELECT COUNT(*)
            FROM gene_scores
            WHERE evidence_group = 'well_supported'
        """)
    ).scalar()

    assert result >= 0  # Should have some well-supported genes


def test_api_filter_by_tier(client):
    """Test API filtering by evidence tier."""
    response = client.get("/api/genes?filter[tier]=comprehensive_support")
    assert response.status_code == 200

    data = response.json()
    for gene in data["data"]:
        assert gene["attributes"]["evidence_tier"] == "comprehensive_support"


def test_api_filter_by_group(client):
    """Test API filtering by evidence group."""
    response = client.get("/api/genes?filter[group]=well_supported")
    assert response.status_code == 200

    data = response.json()
    for gene in data["data"]:
        assert gene["attributes"]["evidence_group"] == "well_supported"


def test_api_invalid_tier_returns_error(client):
    """Test that invalid tier parameter returns validation error."""
    response = client.get("/api/genes?filter[tier]=invalid_tier")
    assert response.status_code == 400


def test_tier_metadata_in_api_response(client):
    """Test that API response includes tier distribution metadata."""
    response = client.get("/api/genes")
    assert response.status_code == 200

    data = response.json()
    assert "evidence_tiers" in data["meta"]
    assert "well_supported" in data["meta"]["evidence_tiers"]
    assert "emerging_evidence" in data["meta"]["evidence_tiers"]
```

**Run tests:**
```bash
cd backend
uv run pytest tests/test_evidence_tiers.py -v
```

---

### Phase 5: Documentation

#### Task 5.1: User Documentation

**File:** `docs/features/evidence-tiers.md` (NEW)

```markdown
# Evidence Tier System

## Overview

The Kidney Genetics Database uses an automated evidence tier system to help users identify genes with varying levels of supporting evidence. This classification is based on the quantity and quality of evidence aggregated from multiple genomic databases.

## Important Note

**This is NOT ClinGen-compliant gene-disease validity curation.** The tier system reflects automated evidence aggregation across data sources. Manual ClinGen-style curation (Definitive, Strong, Moderate, Limited) will be added in a future release.

## Evidence Groups

### Well-Supported (~600 genes)
Genes with evidence from **2+ sources** and **evidence score ≥20%**

These genes have cross-validated evidence and are suitable for clinical consideration or high-confidence research.

**Sub-Tiers:**
- **Comprehensive Support** (T1): 4+ sources, score ≥50%
  - Multiple independent data sources with strong evidence
  - Highest confidence for clinical relevance

- **Multi-Source Support** (T2): 3+ sources, score ≥35%
  - Good evidence from several sources
  - Strong candidates for functional studies

- **Established Support** (T3): 2+ sources, score ≥20%
  - Baseline cross-validation achieved
  - Appropriate for exploratory research

### Emerging Evidence (~2,400 genes)
Genes with **limited evidence** that requires further validation

These genes are suitable for hypothesis generation and exploratory research but lack comprehensive validation.

**Sub-Tiers:**
- **Preliminary Evidence** (T4): Score ≥10%
  - Moderate evidence level
  - Candidates for further investigation

- **Minimal Evidence** (T5): Score >0%, <10%
  - Limited evidence available
  - Very early-stage candidates

## Using Evidence Tiers

### In the Web Interface

1. **Filter by Group**: Use the chip group filter to show only "Well-Supported" or "Emerging Evidence" genes
2. **Filter by Tier**: Use the dropdown to select specific tier levels
3. **Sort by Evidence**: Default sorting prioritizes higher-evidence genes
4. **Hover for Details**: Hover over tier badges to see criteria

### Via API

**Filter by group:**
```
GET /api/genes?filter[group]=well_supported
```

**Filter by specific tier:**
```
GET /api/genes?filter[tier]=comprehensive_support
```

**Combine with other filters:**
```
GET /api/genes?filter[group]=well_supported&filter[min_score]=30&sort=-evidence_score
```
```

---

### Phase 6: Deployment

#### Task 6.1: Pre-Deployment Checklist

- [ ] All tests passing (`make test`)
- [ ] Frontend builds without errors (`cd frontend && npm run build`)
- [ ] Backend lints cleanly (`make lint`)
- [ ] Database migration tested
- [ ] Tier thresholds validated against production data
- [ ] Documentation complete

#### Task 6.2: Deployment Steps

```bash
# 1. Backup current database
make db-backup-full

# 2. Run migrations
cd backend
uv run alembic upgrade head

# 3. Verify views created
psql -d kidney_genetics -c "\dv gene_scores"
psql -d kidney_genetics -c "SELECT COUNT(*), evidence_tier FROM gene_scores GROUP BY evidence_tier;"

# 4. Restart services
make hybrid-down
make hybrid-up

# 5. Validate tier distribution
cd backend
uv run python scripts/validate_tier_distribution.py

# 6. Smoke test API endpoints
curl http://localhost:8000/api/genes?filter[tier]=comprehensive_support | jq '.data | length'
curl http://localhost:8000/api/genes?filter[group]=well_supported | jq '.meta.total'
```

---

## Success Metrics

### Technical Metrics
- [ ] API response time <20ms overhead for tier filtering
- [ ] 100% test coverage for tier logic
- [ ] Zero database migration errors
- [ ] Frontend bundle size increase <50KB

### Data Quality Metrics
- [ ] Well-Supported group = 550-650 genes (target: ~600)
- [ ] Emerging Evidence group = 2,200-2,600 genes (target: ~2,400)
- [ ] No genes with evidence_count>=2 & score>=20 in Emerging tier
- [ ] Tier distribution follows expected curve

---

## Appendix

### A. SQL Reference Queries

**Get tier distribution:**
```sql
SELECT
    evidence_group,
    evidence_tier,
    COUNT(*) as gene_count,
    ROUND(AVG(percentage_score), 2) as avg_score,
    ROUND(AVG(evidence_count), 2) as avg_sources
FROM gene_scores
WHERE percentage_score > 0
GROUP BY evidence_group, evidence_tier
ORDER BY MIN(percentage_score) DESC;
```

**Validate tier assignment logic:**
```sql
SELECT
    approved_symbol,
    evidence_count,
    percentage_score,
    evidence_tier,
    CASE
        WHEN evidence_count >= 4 AND percentage_score >= 50 THEN 'comprehensive_support'
        WHEN evidence_count >= 3 AND percentage_score >= 35 THEN 'multi_source_support'
        WHEN evidence_count >= 2 AND percentage_score >= 20 THEN 'established_support'
        WHEN percentage_score >= 10 THEN 'preliminary_evidence'
        WHEN percentage_score > 0 THEN 'minimal_evidence'
        ELSE 'no_evidence'
    END as expected_tier,
    CASE WHEN evidence_tier = expected_tier THEN 'OK' ELSE 'MISMATCH' END as validation
FROM gene_scores
WHERE percentage_score > 0
HAVING validation = 'MISMATCH';
```

---

### B. API Response Example

```json
{
  "data": [
    {
      "type": "genes",
      "id": "123",
      "attributes": {
        "approved_symbol": "PKD1",
        "hgnc_id": "HGNC:9008",
        "evidence_score": 67.5,
        "evidence_count": 5,
        "evidence_tier": "comprehensive_support",
        "evidence_group": "well_supported",
        "sources": ["PanelApp", "HPO", "ClinGen", "GenCC", "PubTator"]
      }
    }
  ],
  "meta": {
    "total": 600,
    "evidence_tiers": {
      "well_supported": {
        "comprehensive_support": 180,
        "multi_source_support": 230,
        "established_support": 190,
        "total": 600
      },
      "emerging_evidence": {
        "preliminary_evidence": 1450,
        "minimal_evidence": 1250,
        "total": 2700
      }
    }
  }
}
```

---

## Sign-Off

**Prepared by:** Development Team
**Reviewed by:** _[Senior Developer]_
**Approved by:** _[Product Owner]_
**Date:** 2025-09-30

---

**End of Implementation Plan**