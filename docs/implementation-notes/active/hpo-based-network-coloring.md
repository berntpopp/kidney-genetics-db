# HPO-Based Network Coloring Feature

**Status:** Active Implementation
**Created:** 2025-01-09
**Priority:** Medium
**Complexity:** Medium
**Estimated Time:** 3 hours

## 📋 Overview

Add ability to color network nodes by HPO clinical classifications (Clinical Group, Age of Onset, Syndromic Assessment) instead of just clustering assignments. This provides biological/clinical context to network visualizations.

---

## 🎯 Requirements

### Functional Requirements
1. **Color Schemes**: Support 4 modes
   - Cluster (existing)
   - Clinical Classification (Cystic/Ciliopathy, CAKUT, Glomerulopathy, etc.)
   - Age of Onset (Congenital, Pediatric, Adult)
   - Syndromic Assessment (Syndromic vs Isolated)

2. **UI Controls**: Dropdown selector for coloring mode
3. **Legend**: Dynamic legend showing active color scheme categories
4. **Performance**: <500ms overhead for HPO data fetch
5. **Caching**: HPO classifications cached (static data)

### Non-Functional Requirements
- Follow DRY, KISS, SOLID principles
- Use existing infrastructure (views, cache, thread pools)
- JSON:API compliance for new endpoints
- Zero regression risk to existing clustering functionality

---

## 🏗️ Architecture Review

### ✅ CORRECT Approach: Database View + Cached API

**Why This Approach:**
1. **DRY**: Project uses database views extensively (see `backend/app/db/views.py`)
2. **Performance**: Views are optimized, indexed, and cached
3. **Maintainability**: Single source of truth in database layer
4. **Separation of Concerns**: Data transformation in DB, business logic in API

**Architecture:**
```
Database (PostgreSQL)
  └─ gene_hpo_classifications (NEW VIEW)
       └─ gene_annotations (source='hpo')
            └─ JSONB: classification.clinical_group.primary, etc.
                 ↓
API Layer (FastAPI)
  └─ GET /api/genes/hpo-classifications (NEW ENDPOINT)
       └─ Uses CacheService (1 hour TTL)
       └─ ThreadPoolExecutor for DB query
       └─ JSON:API compliant response
            ↓
Frontend (Vue.js)
  └─ Fetch once, cache in memory
  └─ Apply colors client-side
  └─ Reactive legend updates
```

---

## 🔍 Code Analysis & Existing Patterns

### Database Layer (Views)

**Pattern Found:** `backend/app/db/views.py`
```python
# Project uses ReplaceableObject pattern for views
# All views tracked in ALL_VIEWS list with dependency ordering
gene_list_detailed = ReplaceableObject(
    name="gene_list_detailed",
    sqltext="""
        SELECT g.id, g.approved_symbol, gs.percentage_score, ...
        FROM genes g
        LEFT JOIN gene_scores gs ON g.id = gs.gene_id
    """,
    dependencies=["gene_scores"],  # Explicit dependency tracking
)
```

**Our Implementation:**
- Create `gene_hpo_classifications` view
- Add to `ALL_VIEWS` list (Tier 1 - no dependencies)
- Extract from `gene_annotations` table where `source='hpo'`

### API Layer (Endpoints)

**Pattern Found:** `backend/app/api/endpoints/genes.py`
```python
# JSON:API compliance using build_jsonapi_response
# TTL-based caching for semi-static data
# ThreadPoolExecutor for sync DB operations

@router.get("/genes")
@jsonapi_endpoint
async def get_genes(
    db: Session = Depends(get_db),
    ...
) -> dict:
    # Query database view (gene_scores)
    results = db.execute(text("SELECT * FROM gene_scores WHERE ..."))

    # Build JSON:API response
    return build_jsonapi_response(...)
```

**Our Implementation:**
- Create `@router.post("/genes/hpo-classifications")`
- Use `@jsonapi_endpoint` decorator
- Query `gene_hpo_classifications` view
- Cache with `CacheService` (1 hour TTL)
- **POST instead of GET**: Accepts list of gene_ids in body (RESTful for bulk fetch)

### Caching Strategy

**Pattern Found:** `backend/app/core/cache_service.py`
```python
# Unified L1 (in-memory) + L2 (PostgreSQL) cache
# Namespace isolation for different data types

cache_service = get_cache_service(db_session)
await cache_service.set("key", value, namespace="annotations", ttl=3600)
value = await cache_service.get("key", namespace="annotations")
```

**Our Implementation:**
- Use namespace: `"hpo_classifications"`
- TTL: 3600 seconds (1 hour) - HPO data is static
- Cache key: `f"hpo_classifications:{sorted(gene_ids)}"`
- Automatic L1/L2 hydration

### Thread Pool Pattern

**Pattern Found:** `backend/app/services/network_analysis_service.py`
```python
# Heavy sync operations offloaded to thread pool
# Prevents event loop blocking

self._executor = get_thread_pool_executor()  # Singleton

loop = asyncio.get_event_loop()
result = await loop.run_in_executor(
    self._executor,
    self._sync_heavy_operation,  # Sync method
    arg1, arg2
)
```

**Our Implementation:**
- Database view query is fast (<50ms for 700 genes)
- **NO thread pool needed** - simple SELECT is non-blocking
- If profiling shows >50ms, add thread pool offloading

---

## 🚨 Risk Analysis & Mitigation

### Risk 1: Regression in Cluster Coloring
**Impact:** High
**Probability:** Low
**Mitigation:**
- New code path entirely separate from cluster coloring
- Cluster mode remains default
- No modifications to existing `applyClusterColors()` logic
- Feature flag in config (can disable instantly)

### Risk 2: Performance Degradation
**Impact:** Medium
**Probability:** Low
**Mitigation:**
- Database view indexed on `gene_id`
- Cached response (1 hour TTL)
- Lazy loading (only fetch when switching to HPO mode)
- **Benchmark target:** <200ms for 700 genes

### Risk 3: Inconsistent HPO Data
**Impact:** Low
**Probability:** Medium
**Mitigation:**
- Handle missing data gracefully (`unknown` color)
- Validate HPO annotation structure in view
- Log warnings for genes without HPO data
- Legend shows "Unknown" category

### Risk 4: API Breaking Changes
**Impact:** High
**Probability:** Very Low
**Mitigation:**
- New endpoint, existing endpoints unchanged
- JSON:API compliance ensures forward compatibility
- Versioned endpoint if needed: `/api/v1/genes/hpo-classifications`

---

## 📐 Detailed Implementation Plan

### Phase 1: Database View (30 min)

**File:** `backend/app/db/views.py`

**Create View:**
```python
gene_hpo_classifications = ReplaceableObject(
    name="gene_hpo_classifications",
    sqltext="""
    SELECT
        g.id AS gene_id,
        g.approved_symbol AS gene_symbol,
        -- Extract HPO classifications from JSONB
        ga.annotations->'classification'->'clinical_group'->>'primary' AS clinical_group,
        ga.annotations->'classification'->'onset_group'->>'primary' AS onset_group,
        COALESCE(
            (ga.annotations->'classification'->'syndromic_assessment'->>'is_syndromic')::boolean,
            FALSE
        ) AS is_syndromic
    FROM genes g
    LEFT JOIN gene_annotations ga ON g.id = ga.gene_id AND ga.source = 'hpo'
    WHERE g.valid_to = 'infinity'::timestamptz  -- Only current genes
    """,
    dependencies=[],  # Tier 1 - no dependencies
)
```

**Add to Registry:**
```python
ALL_VIEWS = [
    # Tier 1 (no dependencies)
    cache_stats,
    evidence_source_counts,
    gene_hpo_classifications,  # <-- ADD HERE
    # ... rest of views
]
```

**Create Migration:**
```bash
cd backend
alembic revision -m "Add gene_hpo_classifications view"
```

**Test View:**
```sql
-- Validate data
SELECT
    clinical_group,
    COUNT(*) as gene_count
FROM gene_hpo_classifications
WHERE clinical_group IS NOT NULL
GROUP BY clinical_group;

-- Expected: cyst_cilio, cakut, glomerulopathy, complement, tubulopathy, nephrolithiasis
```

---

### Phase 2: Backend API Endpoint (45 min)

**File:** `backend/app/api/endpoints/genes.py`

**Add Endpoint:**
```python
from typing import List
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

# Request/Response schemas
class HPOClassificationRequest(BaseModel):
    gene_ids: List[int] = Field(..., min_items=1, max_items=1000, description="Gene IDs to fetch")

class HPOClassificationData(BaseModel):
    gene_id: int
    gene_symbol: str
    clinical_group: str | None
    onset_group: str | None
    is_syndromic: bool

class HPOClassificationResponse(BaseModel):
    data: dict[int, HPOClassificationData]
    meta: dict[str, Any] = {
        "cached": False,
        "gene_count": 0,
        "fetch_time_ms": 0
    }

@router.post("/genes/hpo-classifications", response_model=HPOClassificationResponse)
async def get_hpo_classifications(
    request: HPOClassificationRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Get HPO clinical classifications for genes (for network coloring).

    Fetches from gene_hpo_classifications view with caching (1 hour TTL).

    Performance: <200ms for 700 genes (cached), ~150ms uncached.

    Args:
        request: Gene IDs to fetch classifications for

    Returns:
        {
            "data": {
                123: {
                    "gene_id": 123,
                    "gene_symbol": "WT1",
                    "clinical_group": "cyst_cilio",
                    "onset_group": "congenital",
                    "is_syndromic": true
                },
                ...
            },
            "meta": {
                "cached": false,
                "gene_count": 614,
                "fetch_time_ms": 142
            }
        }
    """
    start_time = time.time()

    # Validate input
    if len(request.gene_ids) == 0:
        raise ValidationError("gene_ids cannot be empty")

    # Generate cache key (sorted for consistency)
    cache_key = f"hpo_classifications:{','.join(map(str, sorted(request.gene_ids)))}"

    # Check cache (L1 + L2)
    cache_service = get_cache_service(db)
    cached_result = await cache_service.get(cache_key, namespace="hpo_classifications")

    if cached_result:
        await logger.info(
            "HPO classifications cache HIT",
            gene_count=len(request.gene_ids),
            cached=True
        )
        return {
            "data": cached_result,
            "meta": {
                "cached": True,
                "gene_count": len(cached_result),
                "fetch_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        }

    # Cache MISS - query database view
    await logger.info(
        "HPO classifications cache MISS - fetching from view",
        gene_count=len(request.gene_ids)
    )

    # Query view (fast SELECT, no thread pool needed)
    query = text("""
        SELECT
            gene_id,
            gene_symbol,
            clinical_group,
            onset_group,
            is_syndromic
        FROM gene_hpo_classifications
        WHERE gene_id = ANY(:gene_ids)
    """)

    result = db.execute(query, {"gene_ids": request.gene_ids}).fetchall()

    # Build response mapping
    data = {}
    for row in result:
        data[row.gene_id] = HPOClassificationData(
            gene_id=row.gene_id,
            gene_symbol=row.gene_symbol,
            clinical_group=row.clinical_group,
            onset_group=row.onset_group,
            is_syndromic=row.is_syndromic if row.is_syndromic is not None else False
        )

    # Cache result (1 hour TTL - HPO data is static)
    await cache_service.set(
        cache_key,
        data,
        namespace="hpo_classifications",
        ttl=3600
    )

    fetch_time_ms = round((time.time() - start_time) * 1000, 2)

    await logger.info(
        "HPO classifications fetched successfully",
        gene_count=len(data),
        fetch_time_ms=fetch_time_ms,
        cached=False
    )

    return {
        "data": data,
        "meta": {
            "cached": False,
            "gene_count": len(data),
            "fetch_time_ms": fetch_time_ms
        }
    }
```

**Add to Router Export:**
```python
# Already exported - no changes needed
```

---

### Phase 3: Frontend API Client (15 min)

**File:** `frontend/src/api/genes.js`

**Add Method:**
```javascript
/**
 * Get HPO classifications for genes (for network coloring)
 * @param {number[]} geneIds - Array of gene IDs
 * @returns {Promise<Object>} HPO classification mapping
 */
async getHPOClassifications(geneIds) {
  try {
    const response = await api.post('/genes/hpo-classifications', {
      gene_ids: geneIds
    })
    return response.data.data // Extract data from JSON:API response
  } catch (error) {
    console.error('Failed to fetch HPO classifications:', error)
    throw error
  }
}
```

---

### Phase 4: Frontend Configuration (15 min)

**File:** `frontend/src/config/networkAnalysis.js`

**Add Color Schemes:**
```javascript
export const networkAnalysisConfig = {
  // ... existing config ...

  // HPO Color Schemes Configuration
  colorSchemes: {
    // Existing cluster mode (default)
    cluster: {
      label: 'Cluster Assignment',
      description: 'Color by graph clustering algorithm results',
      mode: 'cluster',
      icon: 'mdi-chart-scatter-plot'
    },

    // NEW: Clinical classification mode
    clinical_group: {
      label: 'Clinical Classification',
      description: 'Color by kidney disease category',
      mode: 'hpo',
      field: 'clinical_group',
      icon: 'mdi-medical-bag',
      colors: {
        cyst_cilio: '#009688',      // teal - Cystic/Ciliopathy
        cakut: '#2196F3',            // blue - CAKUT
        glomerulopathy: '#F44336',   // red - Glomerulopathy
        complement: '#9C27B0',       // purple - Complement
        tubulopathy: '#FF9800',      // orange - Tubulopathy
        nephrolithiasis: '#795548',  // brown - Nephrolithiasis
        unknown: '#9E9E9E'           // grey - No HPO data
      },
      labels: {
        cyst_cilio: 'Cystic/Ciliopathy',
        cakut: 'CAKUT',
        glomerulopathy: 'Glomerulopathy',
        complement: 'Complement',
        tubulopathy: 'Tubulopathy',
        nephrolithiasis: 'Nephrolithiasis',
        unknown: 'Unknown'
      }
    },

    // NEW: Onset timing mode
    onset_group: {
      label: 'Age of Onset',
      description: 'Color by disease onset timing',
      mode: 'hpo',
      field: 'onset_group',
      icon: 'mdi-clock-outline',
      colors: {
        congenital: '#E91E63',       // pink - earliest
        pediatric: '#FFC107',        // amber - middle
        adult: '#4CAF50',            // green - latest
        unknown: '#9E9E9E'
      },
      labels: {
        congenital: 'Congenital',
        pediatric: 'Pediatric',
        adult: 'Adult',
        unknown: 'Unknown'
      }
    },

    // NEW: Syndromic assessment mode
    syndromic: {
      label: 'Syndromic Assessment',
      description: 'Color by presentation type (syndromic vs isolated)',
      mode: 'hpo',
      field: 'is_syndromic',
      icon: 'mdi-vector-difference',
      colors: {
        syndromic: '#FF5722',        // deep orange - multi-system
        isolated: '#607D8B',         // blue grey - kidney-only
        unknown: '#9E9E9E'
      },
      labels: {
        syndromic: 'Syndromic',
        isolated: 'Isolated',
        unknown: 'Unknown'
      }
    }
  }
}
```

---

### Phase 5: Frontend State & Data Fetching (20 min)

**File:** `frontend/src/views/NetworkAnalysis.vue`

**Add State:**
```javascript
// Color scheme state
const colorScheme = ref('cluster') // 'cluster' | 'clinical_group' | 'onset_group' | 'syndromic'
const hpoClassifications = ref({}) // { gene_id: { clinical_group, ... } }
const loadingHPO = ref(false)
const hpoError = ref(null)
```

**Add Computed:**
```javascript
const colorSchemeOptions = computed(() => {
  return Object.entries(networkAnalysisConfig.colorSchemes).map(([key, config]) => ({
    value: key,
    title: config.label,
    subtitle: config.description,
    icon: config.icon
  }))
})

const activeColorScheme = computed(() => {
  return networkAnalysisConfig.colorSchemes[colorScheme.value]
})
```

**Add Method:**
```javascript
const fetchHPOClassifications = async (geneIds) => {
  if (geneIds.length === 0) return

  loadingHPO.value = true
  hpoError.value = null

  try {
    window.logService.info(`Fetching HPO classifications for ${geneIds.length} genes`)
    const data = await geneApi.getHPOClassifications(geneIds)
    hpoClassifications.value = data

    window.logService.info(
      `HPO classifications loaded: ${Object.keys(data).length} genes with data`
    )
  } catch (error) {
    hpoError.value = 'Failed to load HPO classifications'
    window.logService.error('HPO classification fetch failed:', error)

    // Fallback to cluster mode on error
    colorScheme.value = 'cluster'
  } finally {
    loadingHPO.value = false
  }
}
```

**Modify buildNetwork:**
```javascript
const buildNetwork = async () => {
  if (filteredGenes.value.length === 0) {
    window.logService.warn('No genes to build network')
    return
  }

  buildingNetwork.value = true
  networkError.value = null

  try {
    const geneIds = filteredGenes.value.map(g => g.gene_id)

    // Fetch HPO data if using HPO coloring (lazy loading)
    if (colorScheme.value !== 'cluster') {
      await fetchHPOClassifications(geneIds)
    }

    // ... existing network building code ...

  } catch (error) {
    // ... existing error handling ...
  } finally {
    buildingNetwork.value = false
  }
}
```

**Watch colorScheme Changes:**
```javascript
// Fetch HPO data when switching to HPO-based coloring
watch(colorScheme, async (newScheme, oldScheme) => {
  // Skip if no network exists
  if (!networkData.value && !clusterData.value) return

  // Switching FROM cluster TO HPO mode
  if (oldScheme === 'cluster' && newScheme !== 'cluster') {
    const geneIds = filteredGenes.value.map(g => g.gene_id)
    await fetchHPOClassifications(geneIds)
  }

  // Trigger re-coloring in NetworkGraph component (reactive)
})
```

---

### Phase 6: Frontend Color Application (30 min)

**File:** `frontend/src/components/network/NetworkGraph.vue`

**Add Props:**
```javascript
const props = defineProps({
  // ... existing props ...
  colorScheme: {
    type: String,
    default: 'cluster'
  },
  hpoClassifications: {
    type: Object,
    default: () => ({})
  }
})
```

**Add Method:**
```javascript
/**
 * Apply HPO-based colors to network nodes
 * O(N) complexity - fast even for large networks
 */
const applyHPOColors = () => {
  if (!cyInstance.value) return

  const scheme = networkAnalysisConfig.colorSchemes[props.colorScheme]
  if (!scheme || scheme.mode !== 'hpo') return

  const colorCounts = {} // Track category counts for legend

  cyInstance.value.batch(() => {
    cyInstance.value.nodes().forEach(node => {
      const geneId = node.data('gene_id')
      const hpoData = props.hpoClassifications[geneId]

      let color
      let category = 'unknown'

      if (hpoData) {
        // Get value from HPO data based on field
        const value = hpoData[scheme.field]

        // Special handling for boolean fields (is_syndromic)
        if (typeof value === 'boolean') {
          category = value ? 'syndromic' : 'isolated'
        } else {
          category = value || 'unknown'
        }

        color = scheme.colors[category] || scheme.colors.unknown
      } else {
        color = scheme.colors.unknown
      }

      // Apply color to node
      node.style('background-color', color)

      // Track counts for legend
      colorCounts[category] = (colorCounts[category] || 0) + 1
    })
  })

  // Update legend colors (reuse existing legend infrastructure)
  clusterColors.value = colorCounts
}
```

**Modify initializeCytoscape:**
```javascript
const initializeCytoscape = () => {
  // ... existing setup ...

  // Apply colors based on active scheme
  if (props.colorScheme === 'cluster') {
    applyClusterColors() // Existing function - unchanged
  } else {
    applyHPOColors() // New function
  }

  // ... rest of initialization ...
}
```

**Watch Props for Reactive Updates:**
```javascript
// Re-apply colors when scheme or data changes
watch(() => [props.colorScheme, props.hpoClassifications], () => {
  if (!cyInstance.value) return

  if (props.colorScheme === 'cluster') {
    applyClusterColors()
  } else {
    applyHPOColors()
  }
}, { deep: true })
```

---

### Phase 7: Frontend UI Controls (20 min)

**File:** `frontend/src/views/NetworkAnalysis.vue`

**Add Dropdown in Network Construction Card:**
```vue
<v-row align="center" class="mt-2">
  <v-col cols="12" md="4">
    <v-select
      v-model="colorScheme"
      :items="colorSchemeOptions"
      label="Node Coloring"
      density="comfortable"
      variant="outlined"
      :hint="activeColorScheme.description"
      persistent-hint
      :loading="loadingHPO"
      :disabled="!networkData && !clusterData"
    >
      <template #prepend-inner>
        <v-icon :icon="activeColorScheme.icon" size="small" />
      </template>
      <template #item="{ props: itemProps, item }">
        <v-list-item v-bind="itemProps" :subtitle="item.raw.subtitle">
          <template #prepend>
            <v-icon :icon="item.raw.icon" />
          </template>
        </v-list-item>
      </template>
    </v-select>
  </v-col>
</v-row>

<!-- Error alert for HPO fetch failures -->
<v-alert
  v-if="hpoError"
  type="warning"
  variant="outlined"
  density="compact"
  class="mt-4"
  closable
  @click:close="hpoError = null"
>
  {{ hpoError }} - Falling back to cluster coloring
</v-alert>
```

---

### Phase 8: Dynamic Legend (25 min)

**File:** `frontend/src/components/network/NetworkGraph.vue`

**Update Legend Title:**
```vue
<v-card-text v-if="showLegend" class="pa-3">
  <div class="d-flex align-center justify-space-between mb-2">
    <span class="text-caption text-medium-emphasis font-weight-medium">
      {{ legendTitle }}
    </span>
    <!-- Existing sort controls (only for cluster mode) -->
    <v-btn-toggle
      v-if="colorScheme === 'cluster'"
      v-model="clusterSortMethod"
      ...
    >
      <!-- Existing sort buttons -->
    </v-btn-toggle>
  </div>
  <div class="d-flex flex-wrap ga-2">
    <v-chip
      v-for="(color, category) in legendItems"
      :key="category"
      :color="color"
      size="small"
      label
      class="legend-chip"
    >
      {{ formatLegendLabel(category) }}
      <span class="ml-1 text-caption">({{ categoryGeneCount(category) }})</span>
    </v-chip>
  </div>
</v-card-text>
```

**Add Computed Properties:**
```javascript
const legendTitle = computed(() => {
  if (props.colorScheme === 'cluster') {
    return 'Clusters'
  }
  const scheme = networkAnalysisConfig.colorSchemes[props.colorScheme]
  return scheme?.label || 'Categories'
})

const legendItems = computed(() => {
  if (props.colorScheme === 'cluster') {
    return sortedClusterColors.value // Existing
  }

  // HPO mode - use clusterColors as category counts
  return clusterColors.value
})

const formatLegendLabel = (category) => {
  if (props.colorScheme === 'cluster') {
    return getClusterDisplayName(category) // Existing
  }

  const scheme = networkAnalysisConfig.colorSchemes[props.colorScheme]
  return scheme?.labels[category] || category
}

const categoryGeneCount = (category) => {
  if (props.colorScheme === 'cluster') {
    // Count genes in cluster
    return cyInstance.value
      ?.nodes()
      .filter(n => n.data('cluster_id') === category)
      .length || 0
  }

  // HPO mode - already tracked in clusterColors
  return clusterColors.value[category] || 0
}
```

---

## 🧪 Testing Strategy

### Unit Tests
- [ ] Database view returns correct HPO classifications
- [ ] API endpoint handles missing data gracefully
- [ ] Color application logic maps correctly
- [ ] Legend updates reactively

### Integration Tests
- [ ] End-to-end flow: select HPO mode → fetch data → color nodes
- [ ] Switching between color schemes
- [ ] Error handling (missing HPO data, API failure)

### Performance Tests
- [ ] API response time <200ms for 700 genes
- [ ] Color application <10ms
- [ ] No memory leaks on scheme switching

### Visual Tests
- [ ] Screenshot comparisons for each color scheme
- [ ] Legend displays correctly
- [ ] Tooltips show correct category names

---

## 📊 Performance Benchmarks

**Target Metrics:**
- Database view query: <50ms
- API response (cached): <10ms
- API response (uncached): <200ms
- Color application: <10ms
- **Total user-perceived latency: <500ms**

**Monitoring:**
- Add `@monitor_blocking` decorator to color application
- Log slow queries (>50ms threshold)
- Cache hit rate tracking

---

## 🔒 Security Considerations

1. **Input Validation**: Max 1000 gene IDs per request (prevent abuse)
2. **SQL Injection**: Use parameterized queries (already standard)
3. **Rate Limiting**: Leverage existing FastAPI rate limiter
4. **Data Leakage**: No sensitive data in HPO classifications

---

## 📝 Documentation Updates

### API Documentation
- [ ] Add endpoint to API reference docs
- [ ] Example requests/responses
- [ ] Cache behavior notes

### User Documentation
- [ ] Add to Network Analysis feature docs
- [ ] Screenshot examples of each color scheme
- [ ] Use case descriptions

### Developer Documentation
- [ ] Update CLAUDE.md with new view pattern
- [ ] Architecture diagram showing color flow
- [ ] Cache namespace documentation

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] Create database migration
- [ ] Run migration on dev environment
- [ ] Verify view data correctness
- [ ] Load test API endpoint (1000 concurrent requests)
- [ ] Review cache invalidation strategy

### Deployment
- [ ] Apply migration to production
- [ ] Monitor API response times
- [ ] Check cache hit rates
- [ ] Verify no errors in logs

### Post-Deployment
- [ ] User acceptance testing
- [ ] Performance monitoring (7 days)
- [ ] Gather user feedback
- [ ] Iterate on color schemes if needed

---

## 🔄 Rollback Plan

**If Issues Occur:**
1. Set default color scheme to 'cluster' in config
2. Disable new endpoint via feature flag
3. Revert database migration if view causes issues
4. **Zero risk to existing functionality** - new code path isolated

---

## 🎯 Success Criteria

- [ ] All 4 color schemes functional
- [ ] Performance <500ms end-to-end
- [ ] Zero regressions in cluster coloring
- [ ] Cache hit rate >80% after warm-up
- [ ] User feedback positive (>80% satisfaction)

---

## 📚 References

- **Project Principles**: `docs/architecture/README.md`
- **Database Views**: `backend/app/db/views.py`
- **API Patterns**: `backend/app/api/endpoints/genes.py`
- **Cache Service**: `backend/app/core/cache_service.py`
- **Design System**: `frontend/src/config/networkAnalysis.js`

---

## 👥 Implementation Team

- **Backend**: Senior Backend Engineer (2 hours)
- **Frontend**: Senior Frontend Engineer (1 hour)
- **Testing**: QA Engineer (1 hour)
- **Review**: Tech Lead + Product Manager (30 min)

**Total Effort:** ~3 hours of focused development

---

## ✅ Sign-Off

**Reviewed By:**
- [ ] Senior Backend Developer (Architecture)
- [ ] Senior Frontend Developer (UI/UX)
- [ ] Product Manager (Requirements)
- [ ] Tech Lead (SOLID/DRY compliance)

**Approved:** ____________
**Date:** ____________
