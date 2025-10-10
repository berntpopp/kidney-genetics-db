# Annotation Source Management Refactor - Implementation Plan

**Issue**: [GitHub #6](https://github.com/berntpopp/kidney-genetics-db/issues/6)
**Status**: Active Planning
**Priority**: High (Security + UX)
**Created**: 2025-10-10
**Updated**: 2025-10-10

---

## 📋 Executive Summary

Move DataSourceProgress component from public Genes view to admin-only section, add proper admin authentication to all annotation/pipeline mutation endpoints, and consolidate annotation management into a unified AdminAnnotations interface.

### Problems Identified

1. **Security Critical** 🚨: Annotation pipeline endpoints missing admin authentication
2. **UX Issue**: DataSourceProgress shown to all users on main Genes view (Issue #6)
3. **Code Duplication**: Two separate systems for progress tracking and pipeline control
4. **Inconsistent Endpoints**: `/api/progress/*` vs `/api/annotations/pipeline/*`

---

## 🔍 Current State Analysis

### Frontend Components

#### 1. DataSourceProgress.vue
- **Location**: `frontend/src/components/DataSourceProgress.vue`
- **Currently Shown**: Main Genes view (`/genes`) - **visible to ALL users**
- **Features**:
  - Real-time WebSocket updates
  - Pause/Resume/Trigger controls for each source
  - Progress bars and status indicators
  - Auto-refresh with 3-second polling
  - Separates Data Sources from Internal Processes
- **API Calls**:
  - `GET /api/progress/status` - WebSocket + polling
  - `POST /api/progress/trigger/{source}` - **NOT PROTECTED** ❌
  - `POST /api/progress/pause/{source}` - **NOT PROTECTED** ❌
  - `POST /api/progress/resume/{source}` - **NOT PROTECTED** ❌

#### 2. AdminAnnotations.vue
- **Location**: `frontend/src/views/admin/AdminAnnotations.vue`
- **Route**: `/admin/annotations` - **Admin protected** ✅
- **Features**:
  - Annotation statistics dashboard
  - Pipeline control (Run/Pause/Resume)
  - Source-specific updates
  - Validation and cache refresh
  - Scheduled jobs management
  - Gene annotation lookup tool
- **API Calls**:
  - Multiple `/api/annotations/*` endpoints
  - `POST /api/progress/pause/annotation_pipeline` (for pause)
  - `POST /api/progress/resume/annotation_pipeline` (for resume)

### Backend Endpoints

#### System A: Progress Endpoints (`backend/app/api/endpoints/progress.py`)

| Endpoint | Method | Admin Required? | Issue |
|----------|--------|----------------|-------|
| `/api/progress/status` | GET | No | ✅ OK (read-only) |
| `/api/progress/status/{source}` | GET | No | ✅ OK (read-only) |
| `/api/progress/ws` | WebSocket | No | ✅ OK (read-only) |
| `/api/progress/trigger/{source}` | POST | **NO** | ❌ **SECURITY RISK** |
| `/api/progress/pause/{source}` | POST | **NO** | ❌ **SECURITY RISK** |
| `/api/progress/resume/{source}` | POST | **NO** | ❌ **SECURITY RISK** |
| `/api/progress/dashboard` | GET | No | ✅ OK (read-only) |

#### System B: Annotation Endpoints (`backend/app/api/endpoints/gene_annotations.py`)

| Endpoint | Method | Admin Required? | Issue |
|----------|--------|----------------|-------|
| `/api/annotations/genes/{id}/annotations` | GET | No | ✅ OK (read-only) |
| `/api/annotations/genes/{id}/annotations/summary` | GET | No | ✅ OK (read-only) |
| `/api/annotations/genes/{id}/annotations/update` | POST | **NO** | ❌ **SECURITY RISK** |
| `/api/annotations/sources` | GET | No | ✅ OK (read-only) |
| `/api/annotations/statistics` | GET | No | ✅ OK (read-only) |
| `/api/annotations/refresh-view` | POST | **NO** | ❌ **SECURITY RISK** |
| `/api/annotations/percentiles/refresh` | POST | **YES** ✅ | ✅ Protected |
| `/api/annotations/percentiles/validate/{source}` | GET | **YES** ✅ | ✅ Protected |
| `/api/annotations/pipeline/status` | GET | No | ✅ OK (read-only) |
| `/api/annotations/pipeline/update` | POST | **NO** | ❌ **SECURITY RISK** |
| `/api/annotations/pipeline/update-failed` | POST | **NO** | ❌ **SECURITY RISK** |
| `/api/annotations/pipeline/update-new` | POST | **NO** | ❌ **SECURITY RISK** |
| `/api/annotations/pipeline/update-missing/{source}` | POST | **NO** | ❌ **SECURITY RISK** |
| `/api/annotations/pipeline/validate` | POST | **NO** | ⚠️ Maybe OK (validation) |
| `/api/annotations/scheduler/jobs` | GET | No | ✅ OK (read-only) |
| `/api/annotations/scheduler/trigger/{job_id}` | POST | **NO** | ❌ **SECURITY RISK** |
| `/api/annotations/batch` | POST | No | ✅ OK (batch read) |
| `/api/annotations/reset` | DELETE | **YES** ✅ | ✅ Protected |

---

## 🎯 Implementation Plan

### Phase 1: Backend Security (CRITICAL - Do First) 🔒

**Objective**: Add admin authentication to all mutation endpoints

#### 1.1 Update Progress Endpoints (`backend/app/api/endpoints/progress.py`)

Add `require_admin` dependency to mutation endpoints:

```python
from app.core.dependencies import require_admin
from app.models.user import User

@router.post("/trigger/{source_name}", dependencies=[Depends(require_admin)])
async def trigger_update(
    source_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> dict[str, Any]:
    # ... existing code ...

@router.post("/pause/{source_name}", dependencies=[Depends(require_admin)])
async def pause_source(
    source_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> dict[str, Any]:
    # ... existing code ...

@router.post("/resume/{source_name}", dependencies=[Depends(require_admin)])
async def resume_source(
    source_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> dict[str, Any]:
    # ... existing code ...
```

**Files to modify:**
- `backend/app/api/endpoints/progress.py:245` - trigger_update
- `backend/app/api/endpoints/progress.py:298` - pause_source
- `backend/app/api/endpoints/progress.py:333` - resume_source

#### 1.2 Update Annotation Endpoints (`backend/app/api/endpoints/gene_annotations.py`)

Add `require_admin` to these endpoints:

```python
# Line 182 - update_gene_annotations
@router.post("/genes/{gene_id}/annotations/update", dependencies=[Depends(require_admin)])

# Line 482 - refresh_materialized_view
@router.post("/refresh-view", dependencies=[Depends(require_admin)])

# Line 643 - trigger_pipeline_update
@router.post("/pipeline/update", dependencies=[Depends(require_admin)])

# Line 700 - update_failed_annotations
@router.post("/pipeline/update-failed", dependencies=[Depends(require_admin)])

# Line 772 - update_new_genes
@router.post("/pipeline/update-new", dependencies=[Depends(require_admin)])

# Line 839 - update_missing_source
@router.post("/pipeline/update-missing/{source_name}", dependencies=[Depends(require_admin)])

# Line 1069 - trigger_scheduled_job
@router.post("/scheduler/trigger/{job_id}", dependencies=[Depends(require_admin)])
```

**Optional** - Consider protecting validation endpoint:
```python
# Line 1027 - validate_annotations (consider if admins-only or public is OK)
@router.post("/pipeline/validate", dependencies=[Depends(require_admin)])
```

**Files to modify:**
- `backend/app/api/endpoints/gene_annotations.py`
  - Lines: 182, 482, 643, 700, 772, 839, 1027, 1069

#### 1.3 Add Logging for Admin Actions

Add audit logging to critical operations:

```python
await logger.info(
    "Admin action: Pipeline update triggered",
    user_id=current_user.id,
    username=current_user.username,
    strategy=strategy,
    sources=sources,
    force=force
)
```

---

### Phase 2: Frontend - Remove from Public View

**Objective**: Remove DataSourceProgress from Genes view (Issue #6)

#### 2.1 Remove Component from Genes.vue

**File**: `frontend/src/views/Genes.vue`

**Before** (lines 6, 15):
```vue
<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Gene Browser</h1>
        <DataSourceProgress />  <!-- REMOVE THIS -->
        <GeneTable />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import GeneTable from '../components/GeneTable.vue'
import DataSourceProgress from '../components/DataSourceProgress.vue'  // REMOVE THIS
</script>
```

**After**:
```vue
<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Gene Browser</h1>
        <GeneTable />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import GeneTable from '../components/GeneTable.vue'
</script>
```

---

### Phase 3: Frontend - Enhance AdminAnnotations

**Objective**: Integrate DataSourceProgress functionality into AdminAnnotations view

#### 3.1 Add Real-time Progress Section to AdminAnnotations.vue

**Location**: After the "Annotation Sources" section (around line 448)

Add new section:

```vue
<!-- Real-time Progress Monitor -->
<v-card class="mb-6">
  <v-card-title class="d-flex align-center justify-space-between">
    <div class="d-flex align-center">
      <v-icon class="mr-2">mdi-clock-time-four-outline</v-icon>
      Real-time Progress Monitor
      <v-chip v-if="liveProgressSummary.running > 0" size="x-small" color="primary" label class="ml-2 pulse">
        <v-icon size="x-small" start>mdi-circle</v-icon>
        Live
      </v-chip>
    </div>
    <v-tooltip text="Auto-refresh">
      <template #activator="{ props }">
        <v-btn
          icon
          variant="text"
          size="small"
          v-bind="props"
          :color="liveProgressAutoRefresh ? 'primary' : 'grey'"
          @click="toggleLiveProgressAutoRefresh"
        >
          <v-icon>{{ liveProgressAutoRefresh ? 'mdi-refresh-auto' : 'mdi-refresh' }}</v-icon>
        </v-btn>
      </template>
    </v-tooltip>
  </v-card-title>

  <v-card-text>
    <!-- Summary Stats -->
    <v-row class="mb-4">
      <v-col cols="6" sm="3">
        <div class="text-center">
          <v-chip color="success" size="small" label>
            {{ liveProgressSummary.completed }} Completed
          </v-chip>
        </div>
      </v-col>
      <v-col cols="6" sm="3">
        <div class="text-center">
          <v-chip color="primary" size="small" label>
            {{ liveProgressSummary.running }} Running
          </v-chip>
        </div>
      </v-col>
      <v-col cols="6" sm="3">
        <div class="text-center">
          <v-chip color="error" size="small" label>
            {{ liveProgressSummary.failed }} Failed
          </v-chip>
        </div>
      </v-col>
      <v-col cols="6" sm="3">
        <div class="text-center">
          <v-chip color="grey" size="small" label>
            {{ liveProgressSummary.idle }} Idle
          </v-chip>
        </div>
      </v-col>
    </v-row>

    <!-- Active Sources with Progress Bars -->
    <div v-if="liveProgressSources.length > 0">
      <v-expansion-panels>
        <!-- Data Sources Panel -->
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon class="mr-2">mdi-database-sync</v-icon>
            Data Sources ({{ liveDataSources.length }})
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-list density="compact">
              <v-list-item
                v-for="source in liveDataSources"
                :key="source.source_name"
                class="px-0 py-2"
              >
                <v-list-item-title class="d-flex align-center mb-1">
                  <span class="font-weight-medium">{{ source.source_name }}</span>
                  <v-chip :color="getStatusColor(source.status)" size="x-small" label class="ml-2">
                    {{ source.status }}
                  </v-chip>
                  <span v-if="source.current_operation" class="text-caption ml-2 text-grey">
                    {{ source.current_operation }}
                  </span>
                </v-list-item-title>

                <v-progress-linear
                  :model-value="source.progress_percentage"
                  :color="getStatusColor(source.status)"
                  height="18"
                  rounded
                  class="my-2"
                  :indeterminate="source.status === 'running' && source.progress_percentage === 0"
                >
                  <template #default>
                    <span class="text-caption font-weight-medium">
                      {{ Math.ceil(source.progress_percentage) }}%
                    </span>
                  </template>
                </v-progress-linear>

                <div class="d-flex align-center text-caption">
                  <span v-if="source.items_added > 0" class="mr-3">
                    <v-icon size="x-small" color="success" class="mr-1">mdi-plus</v-icon>
                    {{ source.items_added }}
                  </span>
                  <span v-if="source.items_updated > 0" class="mr-3">
                    <v-icon size="x-small" color="info" class="mr-1">mdi-update</v-icon>
                    {{ source.items_updated }}
                  </span>
                  <span v-if="source.items_failed > 0" class="mr-3">
                    <v-icon size="x-small" color="error" class="mr-1">mdi-alert</v-icon>
                    {{ source.items_failed }}
                  </span>
                  <v-spacer />

                  <!-- Control Buttons -->
                  <v-btn
                    v-if="source.status === 'idle' || source.status === 'failed'"
                    icon
                    size="x-small"
                    variant="text"
                    color="primary"
                    :loading="liveProgressTriggering[source.source_name]"
                    @click="triggerLiveSource(source.source_name)"
                  >
                    <v-icon size="small">mdi-play</v-icon>
                  </v-btn>
                  <v-btn
                    v-else-if="source.status === 'running'"
                    icon
                    size="x-small"
                    variant="text"
                    color="warning"
                    @click="pauseLiveSource(source.source_name)"
                  >
                    <v-icon size="small">mdi-pause</v-icon>
                  </v-btn>
                  <v-btn
                    v-else-if="source.status === 'paused'"
                    icon
                    size="x-small"
                    variant="text"
                    color="success"
                    @click="resumeLiveSource(source.source_name)"
                  >
                    <v-icon size="small">mdi-play</v-icon>
                  </v-btn>
                </div>

                <div v-if="source.last_error" class="text-caption text-error mt-1">
                  Error: {{ source.last_error }}
                </div>
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- Internal Processes Panel -->
        <v-expansion-panel v-if="liveInternalProcesses.length > 0">
          <v-expansion-panel-title>
            <v-icon class="mr-2">mdi-cog-outline</v-icon>
            Internal Processes ({{ liveInternalProcesses.length }})
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <!-- Similar structure as Data Sources -->
            <v-list density="compact">
              <v-list-item
                v-for="source in liveInternalProcesses"
                :key="source.source_name"
                class="px-0 py-2"
              >
                <!-- Similar content as data sources -->
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </div>

    <div v-else class="text-center text-medium-emphasis py-4">
      <v-icon size="large" color="grey">mdi-information-outline</v-icon>
      <p class="mt-2">No active operations</p>
    </div>
  </v-card-text>
</v-card>
```

#### 3.2 Add Script Logic for Live Progress

**Add to script section** (around line 580):

```javascript
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as annotationsApi from '@/api/admin/annotations'
import axios from 'axios'

// ... existing data ...

// Live Progress State
const liveProgressSources = ref([])
const liveProgressTriggering = ref({})
const liveProgressWs = ref(null)
const liveProgressReconnectInterval = ref(null)
const liveProgressPollInterval = ref(null)
const liveProgressAutoRefresh = ref(true)
const liveProgressLastUpdate = ref(new Date())

// Live Progress Computed
const liveDataSources = computed(() => {
  return liveProgressSources.value
    .filter(s =>
      s.category === 'data_source' ||
      (!s.category && ['PubTator', 'PanelApp', 'HPO', 'ClinGen', 'GenCC', 'OMIM', 'Literature'].includes(s.source_name))
    )
    .sort((a, b) => a.source_name.localeCompare(b.source_name))
})

const liveInternalProcesses = computed(() => {
  return liveProgressSources.value
    .filter(s =>
      s.category === 'internal_process' ||
      (!s.category && ['Evidence_Aggregation', 'HGNC_Normalization', 'annotation_pipeline'].includes(s.source_name))
    )
    .sort((a, b) => a.source_name.localeCompare(b.source_name))
})

const liveProgressSummary = computed(() => {
  return {
    running: liveProgressSources.value.filter(s => s.status === 'running').length,
    completed: liveProgressSources.value.filter(s => s.status === 'completed').length,
    failed: liveProgressSources.value.filter(s => s.status === 'failed').length,
    idle: liveProgressSources.value.filter(s => s.status === 'idle').length,
    paused: liveProgressSources.value.filter(s => s.status === 'paused').length
  }
})

// Live Progress Methods
const getStatusColor = status => {
  const colors = {
    running: 'primary',
    completed: 'success',
    failed: 'error',
    idle: 'grey',
    paused: 'warning'
  }
  return colors[status] || 'grey'
}

const toggleLiveProgressAutoRefresh = () => {
  liveProgressAutoRefresh.value = !liveProgressAutoRefresh.value
  if (liveProgressAutoRefresh.value) {
    startLiveProgressPolling()
  } else {
    stopLiveProgressPolling()
  }
}

const fetchLiveProgressStatus = async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/progress/status')
    liveProgressSources.value = response.data.data
    liveProgressLastUpdate.value = new Date()
  } catch (error) {
    window.logService.error('Failed to fetch live progress status:', error)
  }
}

const startLiveProgressPolling = () => {
  stopLiveProgressPolling()
  liveProgressPollInterval.value = setInterval(() => {
    if (liveProgressSummary.value.running > 0 || liveProgressAutoRefresh.value) {
      fetchLiveProgressStatus()
    }
  }, 3000)
}

const stopLiveProgressPolling = () => {
  if (liveProgressPollInterval.value) {
    clearInterval(liveProgressPollInterval.value)
    liveProgressPollInterval.value = null
  }
}

const connectLiveProgressWebSocket = () => {
  const wsUrl = 'ws://localhost:8000/api/progress/ws'
  liveProgressWs.value = new WebSocket(wsUrl)

  liveProgressWs.value.onopen = () => {
    window.logService.info('Live progress WebSocket connected')
    if (liveProgressReconnectInterval.value) {
      clearInterval(liveProgressReconnectInterval.value)
      liveProgressReconnectInterval.value = null
    }
  }

  liveProgressWs.value.onmessage = event => {
    const message = JSON.parse(event.data)

    if (message.type === 'initial_status') {
      liveProgressSources.value = message.data
    } else if (message.type === 'progress_update') {
      message.data.forEach(update => {
        const index = liveProgressSources.value.findIndex(s => s.source_name === update.source_name)
        if (index >= 0) {
          liveProgressSources.value[index] = update
        }
      })
    } else if (message.type === 'status_change') {
      const index = liveProgressSources.value.findIndex(s => s.source_name === message.source)
      if (index >= 0) {
        liveProgressSources.value[index] = message.data
      }
    }
  }

  liveProgressWs.value.onerror = error => {
    window.logService.error('Live progress WebSocket error:', error)
  }

  liveProgressWs.value.onclose = () => {
    window.logService.info('Live progress WebSocket disconnected')
    if (!liveProgressReconnectInterval.value) {
      liveProgressReconnectInterval.value = setInterval(() => {
        window.logService.info('Attempting to reconnect live progress WebSocket...')
        connectLiveProgressWebSocket()
      }, 5000)
    }
  }
}

const triggerLiveSource = async sourceName => {
  liveProgressTriggering.value[sourceName] = true
  try {
    await axios.post(`http://localhost:8000/api/progress/trigger/${sourceName}`)
    showSnackbar(`Triggered update for ${sourceName}`, 'success')
  } catch (error) {
    window.logService.error(`Failed to trigger ${sourceName}:`, error)
    showSnackbar(`Failed to trigger ${sourceName}: ${error.message}`, 'error')
  } finally {
    liveProgressTriggering.value[sourceName] = false
  }
}

const pauseLiveSource = async sourceName => {
  try {
    await axios.post(`http://localhost:8000/api/progress/pause/${sourceName}`)
    showSnackbar(`Paused ${sourceName}`, 'success')
  } catch (error) {
    window.logService.error(`Failed to pause ${sourceName}:`, error)
    showSnackbar(`Failed to pause ${sourceName}: ${error.message}`, 'error')
  }
}

const resumeLiveSource = async sourceName => {
  try {
    await axios.post(`http://localhost:8000/api/progress/resume/${sourceName}`)
    showSnackbar(`Resumed ${sourceName}`, 'success')
  } catch (error) {
    window.logService.error(`Failed to resume ${sourceName}:`, error)
    showSnackbar(`Failed to resume ${sourceName}: ${error.message}`, 'error')
  }
}

// Update onMounted to initialize live progress
onMounted(() => {
  loadData()

  // Initialize live progress monitoring
  fetchLiveProgressStatus()
  connectLiveProgressWebSocket()
  if (liveProgressAutoRefresh.value) {
    startLiveProgressPolling()
  }
})

// Update onUnmounted to cleanup
onUnmounted(() => {
  if (liveProgressWs.value) {
    liveProgressWs.value.close()
  }
  if (liveProgressReconnectInterval.value) {
    clearInterval(liveProgressReconnectInterval.value)
  }
  if (liveProgressPollInterval.value) {
    clearInterval(liveProgressPollInterval.value)
  }
})
```

#### 3.3 Add Pulsing Animation Style

Add to `<style scoped>` section:

```css
/* Pulsing animation for live indicator */
.pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* Respect motion preferences */
@media (prefers-reduced-motion: reduce) {
  .pulse {
    animation: none;
  }
}
```

---

### Phase 4: Optional Cleanup

**Objective**: Consider removing DataSourceProgress.vue entirely if no longer used

#### 4.1 Check for Other Uses

Search codebase for imports:
```bash
grep -r "DataSourceProgress" frontend/src/
```

If only used in Genes.vue (which we removed), consider:
1. **Option A**: Keep the file for future reference (move to `components/admin/`)
2. **Option B**: Delete the file completely

**Recommendation**: Move to `frontend/src/components/admin/DataSourceProgress.vue` and update documentation that it's a legacy component now integrated into AdminAnnotations.

---

## 📝 Implementation Checklist

### Phase 1: Backend Security (CRITICAL) 🔒

- [ ] **1.1** Add `require_admin` to `/api/progress/trigger/{source}`
- [ ] **1.2** Add `require_admin` to `/api/progress/pause/{source}`
- [ ] **1.3** Add `require_admin` to `/api/progress/resume/{source}`
- [ ] **1.4** Add `require_admin` to `/api/annotations/genes/{id}/annotations/update`
- [ ] **1.5** Add `require_admin` to `/api/annotations/refresh-view`
- [ ] **1.6** Add `require_admin` to `/api/annotations/pipeline/update`
- [ ] **1.7** Add `require_admin` to `/api/annotations/pipeline/update-failed`
- [ ] **1.8** Add `require_admin` to `/api/annotations/pipeline/update-new`
- [ ] **1.9** Add `require_admin` to `/api/annotations/pipeline/update-missing/{source}`
- [ ] **1.10** Add `require_admin` to `/api/annotations/scheduler/trigger/{job_id}`
- [ ] **1.11** (Optional) Add `require_admin` to `/api/annotations/pipeline/validate`
- [ ] **1.12** Add audit logging to critical admin actions
- [ ] **1.13** Test all endpoints return 401/403 without admin auth
- [ ] **1.14** Test all endpoints work correctly with admin auth

### Phase 2: Frontend - Remove from Public View

- [ ] **2.1** Remove `<DataSourceProgress />` from Genes.vue template
- [ ] **2.2** Remove import statement from Genes.vue
- [ ] **2.3** Test `/genes` route loads correctly
- [ ] **2.4** Verify no console errors on Genes page

### Phase 3: Frontend - Enhance AdminAnnotations

- [ ] **3.1** Add "Real-time Progress Monitor" card section
- [ ] **3.2** Add live progress state variables
- [ ] **3.3** Add live progress computed properties
- [ ] **3.4** Add live progress methods
- [ ] **3.5** Add WebSocket connection for live updates
- [ ] **3.6** Add polling fallback mechanism
- [ ] **3.7** Add pulse animation styles
- [ ] **3.8** Test real-time updates work correctly
- [ ] **3.9** Test pause/resume/trigger controls
- [ ] **3.10** Test WebSocket reconnection
- [ ] **3.11** Verify auto-refresh toggle works
- [ ] **3.12** Check responsive layout on mobile

### Phase 4: Optional Cleanup

- [ ] **4.1** Search for other uses of DataSourceProgress
- [ ] **4.2** Move or delete DataSourceProgress.vue
- [ ] **4.3** Update documentation if moved

---

## 🧪 Testing Strategy

### Backend API Testing

#### Test Admin Protection
```bash
# Without authentication - should return 401/403
curl -X POST http://localhost:8000/api/progress/trigger/PubTator

# With user (non-admin) token - should return 403
curl -X POST http://localhost:8000/api/progress/trigger/PubTator \
  -H "Authorization: Bearer <user-token>"

# With admin token - should return 200
curl -X POST http://localhost:8000/api/progress/trigger/PubTator \
  -H "Authorization: Bearer <admin-token>"
```

#### Test Each Protected Endpoint
```bash
# Create test script
cat > test-admin-protection.sh << 'EOF'
#!/bin/bash

ENDPOINTS=(
  "POST /api/progress/trigger/PubTator"
  "POST /api/progress/pause/PubTator"
  "POST /api/progress/resume/PubTator"
  "POST /api/annotations/pipeline/update"
  "POST /api/annotations/pipeline/update-failed"
  "POST /api/annotations/pipeline/update-new"
  "POST /api/annotations/pipeline/update-missing/hgnc"
  "POST /api/annotations/scheduler/trigger/test-job"
  "POST /api/annotations/refresh-view"
)

for endpoint in "${ENDPOINTS[@]}"; do
  method=$(echo $endpoint | awk '{print $1}')
  path=$(echo $endpoint | awk '{print $2}')

  echo "Testing: $endpoint"

  # Test without auth
  status=$(curl -s -o /dev/null -w "%{http_code}" -X $method http://localhost:8000$path)
  if [ "$status" = "401" ] || [ "$status" = "403" ]; then
    echo "  ✅ No auth: $status (correct)"
  else
    echo "  ❌ No auth: $status (WRONG - should be 401/403)"
  fi
done
EOF

chmod +x test-admin-protection.sh
./test-admin-protection.sh
```

### Frontend Testing

#### Manual Testing Checklist
1. **Public Genes View**
   - [ ] Visit `/genes` page
   - [ ] Verify DataSourceProgress is NOT shown
   - [ ] Verify GeneTable displays correctly
   - [ ] No console errors

2. **Admin Annotations View (Not Logged In)**
   - [ ] Try to visit `/admin/annotations`
   - [ ] Should redirect to `/login`

3. **Admin Annotations View (Logged in as User)**
   - [ ] Login as regular user
   - [ ] Try to visit `/admin/annotations`
   - [ ] Should redirect to home page

4. **Admin Annotations View (Logged in as Admin)**
   - [ ] Login as admin
   - [ ] Visit `/admin/annotations`
   - [ ] Verify "Real-time Progress Monitor" section appears
   - [ ] Verify WebSocket connection established (check console)
   - [ ] Verify live sources display with progress bars
   - [ ] Test pause button on running source
   - [ ] Test resume button on paused source
   - [ ] Test trigger button on idle source
   - [ ] Verify auto-refresh toggle works
   - [ ] Verify progress updates in real-time
   - [ ] Check responsive layout

5. **Integration Testing**
   - [ ] Start annotation pipeline update
   - [ ] Verify progress appears in Admin Annotations
   - [ ] Pause the pipeline
   - [ ] Resume the pipeline
   - [ ] Wait for completion
   - [ ] Verify final state is correct

---

## 🔍 Code Review Checklist

### Backend
- [ ] All mutation endpoints have `dependencies=[Depends(require_admin)]`
- [ ] User parameter added where needed: `current_user: User = Depends(require_admin)`
- [ ] Audit logging added to critical operations
- [ ] Imports added: `from app.core.dependencies import require_admin`
- [ ] Imports added: `from app.models.user import User`
- [ ] No breaking changes to read-only endpoints
- [ ] Error messages don't leak sensitive information

### Frontend
- [ ] DataSourceProgress removed from Genes.vue
- [ ] No unused imports in Genes.vue
- [ ] AdminAnnotations has live progress section
- [ ] WebSocket connection properly established
- [ ] WebSocket properly cleaned up on unmount
- [ ] Polling fallback works correctly
- [ ] Error handling for API calls
- [ ] Loading states for buttons
- [ ] User feedback via snackbar
- [ ] Responsive design for mobile
- [ ] Accessibility (ARIA labels, keyboard navigation)
- [ ] Code follows existing patterns (Vuetify 3, Composition API)

---

## 📊 Success Metrics

### Security
- ✅ All annotation mutation endpoints require admin authentication
- ✅ Non-admin users get 403 Forbidden on admin endpoints
- ✅ Audit logs capture admin actions

### UX
- ✅ Regular users no longer see admin controls on Genes page
- ✅ Admin users have unified annotation management interface
- ✅ Real-time progress updates work reliably
- ✅ Pause/Resume controls work as expected

### Code Quality
- ✅ No code duplication between components
- ✅ Consistent API endpoint naming
- ✅ Proper error handling throughout
- ✅ Clean separation of concerns

---

## 🚨 Potential Issues & Mitigations

### Issue 1: WebSocket Authentication
**Problem**: WebSocket endpoints currently don't check authentication
**Mitigation**: Phase 1 implementation adds auth to POST endpoints, WebSocket is read-only so lower priority. Can add token-based auth to WebSocket in follow-up if needed.

### Issue 2: Breaking Changes for Existing Users
**Problem**: Users might have bookmarked `/genes` with DataSourceProgress visible
**Mitigation**: No bookmark impact - removing component doesn't change URL or major functionality

### Issue 3: API Clients Breaking
**Problem**: If any external tools call these endpoints, they'll break
**Mitigation**: This is internal admin tool, unlikely external consumers. Document breaking change in release notes.

### Issue 4: Performance with Live Updates
**Problem**: WebSocket + polling might consume resources
**Mitigation**:
- Only admins access this page
- Polling only active when auto-refresh enabled
- WebSocket is event-driven (optimized)
- Can disable auto-refresh manually

---

## 📚 Related Documentation

- [GitHub Issue #6](https://github.com/berntpopp/kidney-genetics-db/issues/6)
- [Authentication Implementation](../completed/authentication-implementation.md)
- [Admin Panel Architecture](../../architecture/backend.md#admin-endpoints)
- [Progress Tracking System](../../features/progress-tracking.md)

---

## ✅ Definition of Done

1. All backend mutation endpoints require admin authentication
2. DataSourceProgress component removed from public Genes view
3. AdminAnnotations view includes integrated live progress monitoring
4. All tests pass (manual testing checklist completed)
5. Code review completed
6. Documentation updated
7. GitHub Issue #6 closed
8. Release notes prepared

---

## 🎯 Next Steps After Completion

1. **Consider consolidating endpoints**: `/api/progress/*` and `/api/annotations/pipeline/*` serve similar purposes - could be unified
2. **Add unit/integration tests**: Currently relying on manual testing
3. **WebSocket authentication**: Add token-based auth to WebSocket endpoint
4. **Rate limiting**: Consider adding rate limits to admin endpoints
5. **Audit log viewer**: Create UI to view admin action logs

---

## 📌 Notes

- This refactor addresses both security (admin protection) and UX (Issue #6)
- Maintains backward compatibility for read-only endpoints
- Follows existing patterns (Vuetify 3, Composition API, admin router protection)
- Reuses existing WebSocket infrastructure from DataSourceProgress
- No database migrations required
- No new dependencies required

---

**Last Updated**: 2025-10-10
**Status**: Ready for Implementation
**Estimated Effort**: 4-6 hours (2h backend, 2h frontend, 2h testing)
