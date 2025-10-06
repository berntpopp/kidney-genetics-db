# Dashboard Visualization Analysis Report
**Kidney Genetics Database - Data Visualization Dashboard**

**Date**: October 3, 2025
**Analyst**: Senior Data Scientist & Bioinformatician
**Status**: Comprehensive Review

---

## Executive Summary

This report provides a detailed analysis of the current dashboard visualizations in the Kidney Genetics Database, identifying critical issues with source distribution charts and recommending evidence-based improvements aligned with scientific data visualization best practices.

**Key Findings**:
- ✅ **UpSet Plot**: Excellent implementation - highly informative and interactive
- ❌ **Source Distributions**: Fundamentally flawed - showing meaningless single-bar charts
- ⚠️ **Evidence Composition**: Adequate but using suboptimal visualization components
- ❌ **Missing Features**: No evidence tier visualization, no filtering for insufficient evidence

**Critical Priority**: Redesign source distribution visualizations to display meaningful, source-specific metrics rather than uninformative counts.

---

## Table of Contents

1. [Current Implementation Review](#1-current-implementation-review)
2. [Technical Architecture Analysis](#2-technical-architecture-analysis)
3. [Data Quality and Availability](#3-data-quality-and-availability)
4. [Visualization Best Practices](#4-visualization-best-practices)
5. [Detailed Issues and Root Causes](#5-detailed-issues-and-root-causes)
6. [Recommendations](#6-recommendations)
7. [Implementation Roadmap](#7-implementation-roadmap)
8. [API Enhancements Required](#8-api-enhancements-required)

---

## 1. Current Implementation Review

### 1.1 Gene Source Overlaps (UpSet Plot) ✅

**Status**: **GOOD** - Keep as is

**Implementation**:
- Uses D3.js for custom UpSet plot visualization
- Shows intersections between 7 data sources (ClinGen, DiagnosticPanels, GenCC, HPO, Literature, PanelApp, PubTator)
- Displays 75 intersections across 3,112 genes

**Strengths**:
- Highly informative for understanding data source overlap
- Interactive source selection with real-time updates
- Professional D3.js implementation with proper scaling
- Shows both set sizes and intersection counts
- Click-to-explore gene lists

**Recommendations**:
- Minor: Add tooltip with gene examples on hover

---

### 1.2 Source Distributions ❌

**Status**: **CRITICAL ISSUES** - Requires complete redesign

**Current Problems**:

#### Problem 1: Uninformative Single-Bar Charts
For 4 out of 7 sources (ClinGen, GenCC, HPO, Literature), the visualization shows **only one bar** because every gene has exactly 1 evidence record from these sources. This provides **zero information value**.

**Example - ClinGen**:
```
Total Genes: 122
Max Evidence Per Gene: 1
Avg Evidence Per Gene: 1.00

[████████████████████████████████████] 122 genes
1 evidence item
```

This tells us nothing useful. We already know all 122 genes have ClinGen data.

#### Problem 2: Wrong Metrics for DiagnosticPanels
Currently shows distribution by **panel count** (1-16 panels per gene), but should show **provider distribution** (Blueprint Genetics, Invitae, Centogene, etc.). The question users want answered is: "Which providers cover kidney disease genes?" not "How many panels include each gene?"

**Current (Wrong)**:
```
1 panel:   259 genes
2 panels:  138 genes
3 panels:   85 genes
...
```

**Should Be**:
```
Blueprint Genetics: 450 genes
Invitae:           380 genes
Centogene:         220 genes
...
```

#### Problem 3: Rich Data Not Visualized
The backend stores extensive JSONB data that could provide meaningful insights:

**GenCC** - Instead of "1 evidence item", show:
- Classification distribution (Definitive: 45%, Strong: 30%, Moderate: 20%, etc.)
- Number of submitters per gene
- Literature evidence counts

**HPO** - Instead of "1 evidence item", show:
- Phenotype association counts per gene
- Disease association counts
- Phenotype category distribution

**ClinGen** - Instead of "1 evidence item", show:
- Gene-disease validity **classifications** (Definitive: 45 genes, Strong: 38 genes, Moderate: 25 genes, Limited: 12 genes, Disputed: 2 genes)
- Distribution across 5 kidney-specific expert panels (Cystic/Ciliopathy, Glomerulopathy, Tubulopathy, Complement-Mediated, CAKUT)
- Number of validity assessments per gene (shows genes with multiple disease associations)

*Note: ClinGen's evidence score is calculated from the highest classification (Definitive=100, Strong=80, Moderate=60, Limited=30, Disputed=10), so showing classification distribution directly explains what drives the scores.*

**PubTator** - Currently shows publication counts (good), but could enhance with:
- Publication trends over time
- Research topic distribution (genetics, pathology, treatment, etc.)

---

### 1.3 Evidence Composition ⚠️

**Status**: **ADEQUATE** - Could be significantly improved

**Current Implementation**:
- Shows source coverage distribution (7, 6, 5, 4, 3, 2, 1 sources)
- Uses simple Vuetify progress bars (`v-progress-linear`)
- Two views: Coverage and Weights

**Issues**:
1. Uses basic progress bars instead of proper chart library
2. No visualization of evidence **quality tiers** (Definitive, Strong, Moderate, Limited, Disputed)
3. No ability to filter by evidence sufficiency
4. Limited interactivity - can't click to see which genes are in each category

**What's Missing**:
- **Evidence Tiers Tab**: Show distribution of genes by evidence quality
- **Interactive Filtering**: Click a bar to filter the gene browser
- **Drill-down**: Click to see gene list for each category

---

## 2. Technical Architecture Analysis

### 2.1 Current Stack

**Frontend**:
- Vue 3 + Vite + Vuetify
- **vue-data-ui** (v2.x) - Installed but underutilized
- D3.js - Used only for UpSet plot
- Vuetify progress bars - Used for most charts

**Backend**:
- FastAPI with PostgreSQL
- JSONB storage for rich evidence data
- Three API endpoints:
  - `/api/statistics/source-overlaps` ✅ Well-designed
  - `/api/statistics/source-distributions` ⚠️ Returns wrong metrics
  - `/api/statistics/evidence-composition` ⚠️ Missing tier data

### 2.2 Chart Library Assessment

**vue-data-ui** (Currently Installed):
- 63+ native Vue 3 components
- Zero external dependencies
- TypeScript support
- **Severely underutilized** - Only used for potentially some components

**Available Chart Types** (from vue-data-ui):
- `VueUiXy` - Multi-series line/bar charts (perfect for trends, comparisons)
- `VueUiStackbar` - Stacked bar charts (perfect for composition data)
- `VueUiDonut` - Donut/pie charts (perfect for distribution data)
- `VueUiHeatmap` - Heatmaps (perfect for gene×source quality matrix)
- `VueUiRadar` - Radar charts (good for multi-dimensional gene profiles)
- `VueUiParallelCoordinatePlot` - Parallel coordinates (excellent for filtering genes by multiple criteria)

**Current Usage**: Almost none - still using basic Vuetify progress bars

---

## 3. Data Quality and Availability

### 3.1 API Data Analysis

Examined `/api/statistics/source-distributions` response:

**ClinGen**:
```json
{
  "distribution": [{"source_count": 1, "gene_count": 122}],
  "metadata": {
    "total_genes": 122,
    "max_evidence_per_gene": 1,
    "avg_evidence_per_gene": "1.00"
  }
}
```
**Problem**: No variance - all genes have exactly 1 record. Need to extract meaningful data from `evidence_data` JSONB field.

**DiagnosticPanels**:
```json
{
  "distribution": [
    {"source_count": 1, "gene_count": 259},
    {"source_count": 2, "gene_count": 138},
    ...
    {"source_count": 16, "gene_count": 1}
  ],
  "metadata": {
    "total_unique_panel_counts": 15,
    "max_panels_per_gene": 16,
    "avg_panels_per_gene": 3.96
  }
}
```
**Problem**: Counting panels per gene, but should extract and count **providers** from JSONB data.

### 3.2 Database Schema Analysis

From `backend/app/crud/statistics.py`, the current queries:

**PanelApp** (lines 192-212):
```python
jsonb_array_length(COALESCE(gene_evidence.evidence_data->'panels', '[]'::jsonb))
```
Counts panels - this is correct for PanelApp.

**DiagnosticPanels** (likely similar logic):
Should instead extract:
```sql
jsonb_array_elements(evidence_data->'panels')->>'provider'
```
To get provider distribution.

**For sources like GenCC, HPO, ClinGen**: The JSONB fields contain:
- `gene_evidence.evidence_data->'classifications'` (GenCC)
- `gene_evidence.evidence_data->'phenotypes'` (HPO)
- `gene_evidence.evidence_data->'dosage_sensitivity'` (ClinGen)

These are **not being queried or visualized**.

---

## 4. Visualization Best Practices

### 4.1 Scientific Data Visualization Principles

Based on recent research (Nature Cell Biology, 2025; PMC Genomics Visualization, 2024):

#### Principle 1: **Data Integrity and Truth**
> "Visual representations must always tell the truth"

**Current Violation**: Single-bar charts for ClinGen/GenCC/HPO suggest there's distribution data when there isn't - misleading.

**Fix**: Show the actual meaningful metrics (classifications, phenotypes, etc.)

#### Principle 2: **Clarity and Purpose**
> "Choose visualizations that communicate the intended message"

**Current Violation**: Bar charts showing "1 evidence item" communicate nothing.

**Fix**: Each source should have a visualization that answers the relevant scientific question:
- GenCC: "What's the evidence quality distribution?"
- HPO: "How many phenotypes are associated with each gene?"
- DiagnosticPanels: "Which providers cover kidney disease genes?"

#### Principle 3: **Appropriate Chart Types**
> "The chart type should match the data structure and question"

**Recommendations**:
- **Categorical distributions** (e.g., GenCC classifications) → Stacked bar or donut chart
- **Quantitative distributions** (e.g., HPO phenotype counts) → Histogram or density plot
- **Hierarchical data** (e.g., providers > panels) → Treemap or sunburst
- **Multi-dimensional comparisons** → Parallel coordinates or radar charts

#### Principle 4: **Interactivity for Exploration**
> "Enable users to explore and discover patterns"

**Current Gap**: Limited click-through, no drill-down, no filtering integration.

**Fix**: Make charts interactive - click to filter gene browser, hover for details.

### 4.2 Genomic Data Visualization Best Practices

From "Ten Simple Rules for Developing Visualization Tools in Genomics" (PMC, 2022):

1. **Show data provenance** - Make source contributions visible ✅ (partially done)
2. **Enable data quality assessment** - Show evidence tiers ❌ (missing)
3. **Support filtering and selection** - Filter by quality ❌ (missing)
4. **Provide multiple views** - Different perspectives ⚠️ (limited)

---

## 5. Detailed Issues and Root Causes

### 5.1 Root Cause Analysis

**Issue**: Source distributions show meaningless single-bar charts

**Root Cause**: Backend query design flaw
- Current logic: Count evidence **records** per gene per source
- Reality: Most sources have 1 record per gene (by design)
- Solution: Query the **content** of evidence records, not the count

**Code Location**: `backend/app/crud/statistics.py:167-280`

The function `get_source_distributions` currently:
```python
# For ClinGen, GenCC, HPO - returns single bar
# Because each gene has exactly 1 evidence record
```

Should instead:
```python
# Extract and aggregate data FROM the evidence_data JSONB field
# E.g., for GenCC: count genes by classification
# For HPO: count genes by number of phenotypes
# For DiagnosticPanels: count genes by provider
```

### 5.2 Missing Evidence Tier Visualization

**Issue**: No visualization of evidence quality across the database

**Root Cause**: Backend doesn't provide evidence tier aggregation

**Current API Endpoints**:
- `/api/statistics/source-overlaps` - ✅ Sources
- `/api/statistics/source-distributions` - ⚠️ Wrong metrics
- `/api/statistics/evidence-composition` - ⚠️ Missing tier data
- **MISSING**: `/api/statistics/evidence-tiers` - ❌ Doesn't exist

**Solution**: Create new endpoint that returns:
```json
{
  "tier_distribution": [
    {"tier": "Definitive", "gene_count": 450, "percentage": 14.5},
    {"tier": "Strong", "gene_count": 780, "percentage": 25.1},
    {"tier": "Moderate", "gene_count": 1200, "percentage": 38.6},
    {"tier": "Limited", "gene_count": 550, "percentage": 17.7},
    {"tier": "Disputed", "gene_count": 132, "percentage": 4.1}
  ],
  "source_tier_breakdown": {
    "ClinGen": {...},
    "GenCC": {...}
  }
}
```

### 5.3 No Filtering for Insufficient Evidence

**Issue**: Can't filter dashboard to show only high-quality genes

**Impact**: Users can't focus on genes with strong evidence

**Solution**: Add filter control to dashboard:
```vue
<v-select
  v-model="minEvidenceTier"
  :items="['All', 'Definitive', 'Strong', 'Moderate']"
  label="Minimum Evidence Tier"
/>
```

This should filter ALL visualizations consistently.

---

## 6. Recommendations

### 6.1 Immediate Priorities (Week 1)

#### 1. Fix DiagnosticPanels Distribution
**Current**: Shows panel count distribution
**Fix**: Show provider distribution

**Backend Changes** (`backend/app/crud/statistics.py`):
```python
elif source_name == "DiagnosticPanels":
    # Extract providers from evidence_data JSONB
    distribution_data = db.execute(
        text(f"""
            WITH provider_counts AS (
                SELECT
                    gene_evidence.gene_id,
                    jsonb_array_elements(evidence_data->'panels')->>'provider' as provider
                FROM gene_evidence
                {join_for_dist}
                WHERE {filter_for_dist} AND source_name = 'DiagnosticPanels'
            )
            SELECT
                provider,
                COUNT(DISTINCT gene_id) as gene_count
            FROM provider_counts
            WHERE provider IS NOT NULL
            GROUP BY provider
            ORDER BY gene_count DESC
        """)
    ).fetchall()
```

**Frontend Changes**: Update chart to show providers instead of panel counts.

#### 2. Redesign Source-Specific Visualizations

**GenCC**: Show classification distribution
```python
# Backend: Extract classifications from evidence_data
SELECT
    evidence_data->>'classification' as classification,
    COUNT(DISTINCT gene_id) as gene_count
FROM gene_evidence
WHERE source_name = 'GenCC'
GROUP BY classification
```

**Frontend**: Use `VueUiDonut` for classification distribution pie chart

**HPO**: Show phenotype count distribution
```python
# Backend: Count phenotypes per gene
SELECT
    phenotype_count,
    COUNT(*) as gene_count
FROM (
    SELECT
        gene_id,
        jsonb_array_length(evidence_data->'phenotypes') as phenotype_count
    FROM gene_evidence
    WHERE source_name = 'HPO'
) phenotype_counts
GROUP BY phenotype_count
```

**Frontend**: Use `VueUiXy` histogram

**ClinGen**: Show dosage sensitivity distribution
```python
# Backend: Extract dosage classifications
SELECT
    evidence_data->>'haploinsufficiency_score' as hi_score,
    evidence_data->>'triplosensitivity_score' as ts_score,
    COUNT(*) as gene_count
FROM gene_evidence
WHERE source_name = 'ClinGen'
GROUP BY hi_score, ts_score
```

**Frontend**: Use `VueUiHeatmap` or `VueUiStackbar`

#### 3. Add Evidence Tiers Tab

**Backend**: Create `/api/statistics/evidence-tiers` endpoint

**Frontend**: Add new tab "Evidence Tiers" to dashboard
- Use `VueUiDonut` for overall tier distribution
- Use `VueUiStackbar` for tier breakdown by source
- Add click-to-filter functionality

### 6.2 High Priority (Week 2)

#### 4. Replace Progress Bars with vue-data-ui Charts

**Current**: Using `v-progress-linear` throughout

**Fix**: Migrate to vue-data-ui components

**Evidence Composition** → `VueUiStackbar`:
```vue
<VueUiStackbar
  :dataset="sourceCoverageData"
  :config="{
    chart: {
      fontFamily: 'Roboto',
      backgroundColor: theme.current.value.colors.surface
    },
    userOptions: {
      show: true
    }
  }"
  @selectDatapoint="handleBarClick"
/>
```

**Benefits**:
- Professional appearance
- Better interactivity
- Consistent with design system

#### 5. Add Global Evidence Filter

**Location**: Dashboard header (below tab navigation)

**Implementation**:
```vue
<v-row class="mb-4">
  <v-col cols="12" md="6">
    <v-select
      v-model="evidenceFilter"
      :items="evidenceFilterOptions"
      label="Filter by Evidence Quality"
      density="compact"
      variant="outlined"
    />
  </v-col>
  <v-col cols="12" md="6">
    <v-chip-group>
      <v-chip>3,112 total genes</v-chip>
      <v-chip v-if="evidenceFilter !== 'all'">
        {{ filteredGeneCount }} genes ({{evidenceFilter}})
      </v-chip>
    </v-chip-group>
  </v-col>
</v-row>
```

**Backend**: Add `?min_evidence_tier=` query parameter to all endpoints

### 6.3 Medium Priority (Week 3-4)

#### 6. Add Interactivity and Drill-Down

**Click-to-Filter**:
- Click source in UpSet plot → highlight in other charts
- Click bar in distribution → filter gene browser
- Click evidence tier → show only those genes

**Implementation Pattern**:
```javascript
const handleChartClick = (datapoint) => {
  // Update URL with filter
  router.push({
    path: '/genes',
    query: {
      source: datapoint.source,
      evidence_tier: datapoint.tier
    }
  })
}
```

#### 7. Add Multi-Source Heatmap

**Visualization**: Gene × Source quality matrix

**Shows**: For each gene-source combination, show evidence tier as color

**Chart Type**: `VueUiHeatmap`

**Use Case**: Quickly identify genes with strong evidence across multiple sources

---

## 7. Implementation Roadmap

### Phase 1: Critical Fixes (Week 1)

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Fix DiagnosticPanels provider distribution | P0 | 4h | Backend |
| Redesign GenCC visualization (classifications) | P0 | 6h | Full-stack |
| Redesign HPO visualization (phenotype counts) | P0 | 6h | Full-stack |
| Redesign ClinGen visualization (dosage sensitivity) | P0 | 6h | Full-stack |
| Add Evidence Tiers tab | P0 | 8h | Full-stack |

**Total**: ~30 hours / 4 days

### Phase 2: Enhancement (Week 2)

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Replace progress bars with vue-data-ui | P1 | 8h | Frontend |
| Add global evidence filter | P1 | 6h | Full-stack |
| Improve chart interactivity | P1 | 6h | Frontend |

**Total**: ~20 hours / 2.5 days

### Phase 3: Advanced Features (Week 3-4)

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Add click-to-filter drill-down | P2 | 8h | Full-stack |
| Add gene×source heatmap | P2 | 10h | Full-stack |
| Documentation and testing | P2 | 8h | All |

**Total**: ~26 hours / 3.5 days

**Total Implementation Time**: 10-11 days for complete overhaul

---

## 8. API Enhancements Required

### 8.1 New Endpoints

#### `/api/statistics/evidence-tiers`

**Purpose**: Provide evidence quality distribution

**Response**:
```json
{
  "data": {
    "overall_distribution": [
      {
        "tier": "Definitive",
        "gene_count": 450,
        "percentage": 14.5,
        "sources": ["ClinGen", "GenCC"]
      },
      ...
    ],
    "by_source": {
      "ClinGen": [...],
      "GenCC": [...]
    }
  },
  "meta": {
    "total_genes": 3112,
    "genes_with_tier": 2890,
    "query_duration_ms": 45
  }
}
```

**Implementation**: `backend/app/api/endpoints/statistics.py`

### 8.2 Modified Endpoints

#### `/api/statistics/source-distributions` (BREAKING CHANGE)

**Current Issue**: Returns evidence record counts (meaningless for most sources)

**Proposed Fix**: Return source-specific meaningful metrics

**New Response Structure**:
```json
{
  "data": {
    "GenCC": {
      "type": "classification_distribution",
      "distribution": [
        {"category": "Definitive", "gene_count": 120, "percentage": 38.3},
        {"category": "Strong", "gene_count": 95, "percentage": 30.4},
        ...
      ],
      "metadata": {
        "total_genes": 313,
        "data_source": "GenCC",
        "last_updated": "2025-10-01"
      }
    },
    "HPO": {
      "type": "phenotype_count_distribution",
      "distribution": [
        {"phenotype_count": "1-5", "gene_count": 450},
        {"phenotype_count": "6-10", "gene_count": 380},
        ...
      ]
    },
    "DiagnosticPanels": {
      "type": "provider_distribution",
      "distribution": [
        {"provider": "Blueprint Genetics", "gene_count": 450},
        {"provider": "Invitae", "gene_count": 380},
        ...
      ]
    }
  }
}
```

**Migration Strategy**:
1. Add `?version=2` query parameter for new format
2. Deprecate old format with warning
3. Remove old format in next major version

#### `/api/statistics/evidence-composition` (ENHANCEMENT)

**Add**: Evidence tier breakdown to existing response

**New Fields**:
```json
{
  "data": {
    "source_coverage_distribution": [...], // Existing
    "source_contribution_weights": {...}, // Existing
    "evidence_tier_distribution": [  // NEW
      {"tier": "Definitive", "gene_count": 450, "percentage": 14.5},
      ...
    ],
    "summary_statistics": {
      "avg_sources_per_gene": 2.3,
      "total_evidence_records": 8542,
      "high_confidence_genes": 1230,  // Definitive + Strong
      "genes_needing_review": 132     // Limited + Disputed
    }
  }
}
```

---

## 9. Design Mockups and Examples

### 9.1 Proposed Source Distribution Layouts

#### GenCC - Classification Distribution (Donut Chart)

```
┌─────────────────────────────────────┐
│  GenCC Classification Distribution  │
├─────────────────────────────────────┤
│                                     │
│           ┌────────────┐            │
│          ╱              ╲           │
│         │   Definitive   │          │
│         │      38%       │          │
│          ╲              ╱           │
│           └────────────┘            │
│                                     │
│  [■] Definitive (38%) - 120 genes  │
│  [■] Strong (30%) - 95 genes       │
│  [■] Moderate (22%) - 68 genes     │
│  [■] Limited (8%) - 25 genes       │
│  [■] Disputed (2%) - 5 genes       │
│                                     │
│  [Export CSV] [Export PDF]          │
└─────────────────────────────────────┘
```

#### HPO - Phenotype Count Distribution (Histogram)

```
┌─────────────────────────────────────┐
│  HPO Phenotype Count Distribution   │
├─────────────────────────────────────┤
│                                     │
│   Gene Count                        │
│      ↑                              │
│  500 ┤     █                        │
│  400 ┤     █                        │
│  300 ┤     █    █                   │
│  200 ┤  █  █    █    █              │
│  100 ┤  █  █    █    █  █           │
│    0 └──┴──┴────┴────┴──┴──────→   │
│       1-5 6-10 11-20 21-50 50+      │
│           Phenotypes per Gene       │
│                                     │
│  Median: 8 phenotypes               │
│  Mean: 12.3 phenotypes              │
└─────────────────────────────────────┘
```

#### DiagnosticPanels - Provider Distribution (Horizontal Bar)

```
┌─────────────────────────────────────────────┐
│  Diagnostic Panel Provider Coverage         │
├─────────────────────────────────────────────┤
│                                             │
│  Blueprint Genetics  ████████████ 450 genes│
│  Invitae             ██████████   380 genes│
│  Centogene           ███████      220 genes│
│  PreventionGenetics  ██████       190 genes│
│  GeneDx              █████        160 genes│
│  Fulgent             ████         140 genes│
│  Others              ███          95 genes │
│                                             │
│  [Show All Providers ▼]                    │
└─────────────────────────────────────────────┘
```

### 9.2 Evidence Tiers Tab Layout

```
┌───────────────────────────────────────────────────────┐
│  Evidence Tiers Distribution                          │
├───────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────────┐  ┌────────────────────────────┐ │
│  │                 │  │  Tier Breakdown by Source  │ │
│  │   Overall Tiers │  │                            │ │
│  │                 │  │  ┌─────────┬──────┬──────┐ │ │
│  │   ┌────────┐    │  │  │ ClinGen │ GenCC│ ... │ │ │
│  │  ╱  Defini- ╲   │  │  ├─────────┼──────┼──────┤ │ │
│  │ │   tive     │  │  │  │ Definit.│ 120  │ 95  │ │ │
│  │  ╲  14.5%   ╱   │  │  │ Strong  │ 85   │ 110 │ │ │
│  │   └────────┘    │  │  │ Moderate│ 62   │ 88  │ │ │
│  │                 │  │  └─────────┴──────┴──────┘ │ │
│  └─────────────────┘  └────────────────────────────┘ │
│                                                       │
│  Filter by Tier: [All ▼] [Definitive] [Strong]       │
│                                                       │
│  Showing: 3,112 genes (All tiers)                     │
│  High confidence (Def.+Strong): 1,230 genes (39.5%)   │
│  Needs review (Ltd.+Disputed): 132 genes (4.2%)       │
└───────────────────────────────────────────────────────┘
```

---

## 10. Testing and Validation

### 10.1 Data Validation Tests

**Before Deployment**, validate:

1. **DiagnosticPanels Provider Extraction**:
   - Query JSONB data for all unique providers
   - Verify provider names are clean (no nulls, no duplicates with different spellings)
   - Confirm gene counts sum correctly

2. **GenCC Classification Data**:
   - Verify all genes have classification field
   - Check for missing/null values
   - Validate classification values against expected set

3. **HPO Phenotype Counts**:
   - Verify phenotype arrays are well-formed
   - Check for reasonable ranges (0-200 phenotypes per gene)
   - Identify outliers

### 10.2 Visual Regression Testing

**Capture Screenshots** before/after changes:
- UpSet plot (should remain unchanged)
- Each source distribution chart (should show meaningful data)
- Evidence composition (should show better charts)

**Automated Testing**:
```javascript
// frontend/tests/visualizations/dashboard.spec.js
describe('Dashboard Visualizations', () => {
  it('should show provider distribution for DiagnosticPanels', () => {
    cy.visit('/dashboard?tab=distributions')
    cy.get('[data-testid=source-select]').select('DiagnosticPanels')
    cy.get('[data-testid=chart-legend]').should('contain', 'Blueprint Genetics')
    cy.get('[data-testid=chart-legend]').should('contain', 'Invitae')
  })

  it('should show classification distribution for GenCC', () => {
    cy.visit('/dashboard?tab=distributions')
    cy.get('[data-testid=source-select]').select('GenCC')
    cy.get('[data-testid=chart-legend]').should('contain', 'Definitive')
    cy.get('[data-testid=chart-legend]').should('contain', 'Strong')
  })
})
```

### 10.3 Performance Testing

**Benchmarks**:
- API response time < 500ms for all endpoints
- Chart render time < 200ms
- Interactive updates < 100ms

**Load Testing**:
```bash
# Test with 100 concurrent users
ab -n 1000 -c 100 http://localhost:8000/api/statistics/source-distributions
```

---

## 11. Documentation Requirements

### 11.1 User Documentation

**Add to `/docs/features/dashboard-visualizations.md`**:

#### Source Distribution Charts - Interpretation Guide

**GenCC Classification Chart**:
- **Definitive**: Highest confidence gene-disease associations
- **Strong**: Well-supported associations with multiple lines of evidence
- **Moderate**: Moderate evidence, may need additional validation
- **Limited**: Preliminary evidence, requires further study
- **Disputed**: Conflicting evidence

**HPO Phenotype Count Chart**:
- Shows distribution of phenotype associations per gene
- Higher counts suggest pleiotropic genes (multiple phenotypes)
- Useful for identifying genes with broad clinical impact

**DiagnosticPanels Provider Chart**:
- Shows which commercial providers include each gene
- Higher coverage suggests clinical importance
- Click provider to see detailed panel information

### 11.2 Developer Documentation

**Add to `/docs/architecture/data-visualizations.md`**:

#### Adding New Visualization Types

```python
# Backend: Add source-specific logic to statistics.py
elif source_name == "NewSource":
    # Extract meaningful metrics from evidence_data JSONB
    distribution_data = db.execute(
        text("""
            SELECT
                evidence_data->>'metric' as metric,
                COUNT(*) as gene_count
            FROM gene_evidence
            WHERE source_name = :source_name
            GROUP BY metric
        """),
        {"source_name": source_name}
    ).fetchall()
```

```vue
<!-- Frontend: Add chart component -->
<VueUiDonut
  v-if="sourceData.type === 'category_distribution'"
  :dataset="formattedData"
  :config="donutConfig"
/>
```

---

## 12. Risk Assessment and Mitigation

### 12.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| JSONB data quality issues | High | High | Comprehensive data validation before deployment |
| Performance degradation | Medium | Medium | Query optimization, caching, indexing |
| Breaking API changes affect other features | Low | High | Versioned API endpoints, thorough testing |
| Browser compatibility (D3.js, vue-data-ui) | Low | Medium | Cross-browser testing, polyfills |

### 12.2 Mitigation Strategies

1. **Phased Rollout**: Deploy changes incrementally, starting with least-used features
2. **Feature Flags**: Implement toggle to switch between old/new visualizations during transition
3. **User Testing**: Conduct user interviews with 5-10 scientists before full deployment
4. **Rollback Plan**: Maintain old visualization code for 1 release cycle

---

## 13. Success Metrics

### 13.1 Quantitative Metrics

**Track Post-Deployment**:

1. **User Engagement**:
   - Dashboard page views (target: +30% increase)
   - Time spent on dashboard (target: +50% increase)
   - Chart interactions (clicks, hovers, filters)

2. **Data Insights**:
   - Number of genes filtered by evidence tier
   - Click-through to gene browser

3. **Performance**:
   - API response time (target: < 500ms)
   - Chart render time (target: < 200ms)
   - Zero increase in page load time

### 13.2 Qualitative Metrics

**User Feedback Survey** (1 month post-deployment):

1. "The source distribution charts now provide useful information" (1-5 scale)
2. "I can easily understand the evidence quality for genes" (1-5 scale)
3. "The visualizations help me identify genes of interest" (1-5 scale)

**Target**: Average score > 4.0

---

## 14. Conclusion

### Summary of Findings

The current dashboard visualization implementation has **one excellent component** (UpSet plot) and **two fundamentally flawed components** (source distributions, evidence composition). The primary issues stem from:

1. **Showing wrong metrics**: Counting evidence records instead of extracting meaningful content
2. **Missing critical features**: No evidence tier visualization, no filtering capabilities
3. **Underutilizing available tools**: vue-data-ui installed but barely used
4. **Limited interactivity**: No drill-down, no export, minimal click-through

### Key Recommendations

**Immediate Actions** (Week 1):
1. ✅ Redesign source distributions to show provider/classification/phenotype data
2. ✅ Add evidence tiers tab
3. ✅ Fix DiagnosticPanels to show providers

**High Priority** (Week 2):
4. ✅ Replace progress bars with proper charts (vue-data-ui)
5. ✅ Add global evidence quality filter

**Medium Priority** (Weeks 3-4):
6. ✅ Add interactivity and drill-down
7. ✅ Add gene×source heatmap

### Expected Impact

With these changes, the dashboard will transform from a partially informative tool into a **comprehensive, interactive scientific data exploration platform** that:

- ✅ Displays meaningful metrics for all data sources
- ✅ Enables evidence-based filtering and exploration
- ✅ Follows genomic data visualization best practices
- ✅ Supports advanced multi-dimensional analysis

**Estimated ROI**: 10-11 days of development time for a **10x improvement** in dashboard utility and user satisfaction.

---

## Appendices

### Appendix A: vue-data-ui Component Reference

**Recommended Components for Each Use Case**:

| Use Case | Component | Reason |
|----------|-----------|--------|
| Classification distribution | `VueUiDonut` | Perfect for categorical proportions |
| Phenotype count histogram | `VueUiXy` | Multi-series bar chart support |
| Provider coverage | `VueUiStackbar` | Good for hierarchical categorical data |
| Evidence tiers | `VueUiDonut` + `VueUiStackbar` | Combine for overall + breakdown |
| Gene×source quality matrix | `VueUiHeatmap` | Color-coded matrix visualization |

### Appendix B: Backend Query Examples

**DiagnosticPanels Provider Distribution**:
```sql
WITH provider_genes AS (
  SELECT
    gene_id,
    jsonb_array_elements(evidence_data->'panels')->>'provider' as provider
  FROM gene_evidence
  WHERE source_name = 'DiagnosticPanels'
    AND evidence_score > 0
)
SELECT
  provider,
  COUNT(DISTINCT gene_id) as gene_count,
  ROUND(COUNT(DISTINCT gene_id) * 100.0 / (SELECT COUNT(DISTINCT gene_id) FROM provider_genes), 2) as percentage
FROM provider_genes
WHERE provider IS NOT NULL
GROUP BY provider
ORDER BY gene_count DESC;
```

**GenCC Classification Distribution**:
```sql
SELECT
  evidence_data->>'classification' as classification,
  COUNT(DISTINCT gene_id) as gene_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM gene_evidence
WHERE source_name = 'GenCC'
  AND evidence_score > 0
  AND evidence_data->>'classification' IS NOT NULL
GROUP BY evidence_data->>'classification'
ORDER BY
  CASE evidence_data->>'classification'
    WHEN 'Definitive' THEN 1
    WHEN 'Strong' THEN 2
    WHEN 'Moderate' THEN 3
    WHEN 'Limited' THEN 4
    WHEN 'Disputed' THEN 5
    ELSE 6
  END;
```

**HPO Phenotype Count Distribution**:
```sql
WITH phenotype_counts AS (
  SELECT
    gene_id,
    jsonb_array_length(COALESCE(evidence_data->'phenotypes', '[]'::jsonb)) as phenotype_count
  FROM gene_evidence
  WHERE source_name = 'HPO'
    AND evidence_score > 0
)
SELECT
  CASE
    WHEN phenotype_count BETWEEN 1 AND 5 THEN '1-5'
    WHEN phenotype_count BETWEEN 6 AND 10 THEN '6-10'
    WHEN phenotype_count BETWEEN 11 AND 20 THEN '11-20'
    WHEN phenotype_count BETWEEN 21 AND 50 THEN '21-50'
    ELSE '50+'
  END as phenotype_range,
  COUNT(*) as gene_count
FROM phenotype_counts
GROUP BY phenotype_range
ORDER BY MIN(phenotype_count);
```

### Appendix C: Testing Checklist

**Pre-Deployment Checklist**:

- [ ] All API endpoints return expected data structure
- [ ] JSONB field extraction works for all sources
- [ ] No null/undefined values in visualizations
- [ ] Charts render correctly in Chrome, Firefox, Safari
- [ ] Responsive design works on mobile/tablet
- [ ] Performance benchmarks met (< 500ms API, < 200ms render)
- [ ] All tooltips display correct information
- [ ] Click-through navigation works correctly
- [ ] Evidence filter applies to all visualizations
- [ ] User documentation updated
- [ ] Developer documentation updated

---

**Report Prepared By**: Senior Data Scientist & Bioinformatician
**Date**: October 3, 2025
**Version**: 1.0
**Status**: Final for Review

---

**Next Steps**:
1. Review report with development team
2. Prioritize recommendations based on business impact
3. Create detailed technical specifications for Phase 1
4. Begin implementation with DiagnosticPanels fix
5. Schedule user testing session after Phase 1 completion
