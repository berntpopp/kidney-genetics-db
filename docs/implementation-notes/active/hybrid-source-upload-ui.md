# Hybrid Source Upload UI Implementation Plan

## Executive Summary

Implement proper UI for uploading hybrid source files (DiagnosticPanels and Literature) in the admin panel, fixing the current broken `/ingestion` route and misplaced user menu item.

**Status**: 🔄 Planning
**Priority**: High
**Estimated Effort**: 4-6 hours

## Problem Statement

### Current Issues

1. **Broken Route**: UserMenu.vue references `/ingestion` (line 100) but no route exists → Vue Router warning
2. **Wrong Location**: "Data Ingestion" link in user menu (curator-only) should be in admin panel
3. **Missing UI**: No view component exists for file upload functionality
4. **Incomplete Documentation**: No user guide for uploading DiagnosticPanels/Literature files
5. **API Works**: Backend `/api/ingestion` endpoints are fully functional and well-implemented

### User Impact

- Curators cannot upload DiagnosticPanels or Literature files through the UI
- Console warnings about missing routes affect user experience
- Inconsistent with admin panel design patterns (all admin functions should be cards in admin dashboard)

## Technical Analysis

### Backend API (Already Implemented ✅)

**File**: `backend/app/api/endpoints/ingestion.py`

```python
# Available endpoints:
POST   /api/ingestion/{source_name}/upload  # Upload file for DiagnosticPanels or Literature
GET    /api/ingestion/{source_name}/status  # Get source statistics
GET    /api/ingestion/                      # List available hybrid sources

# Supported sources: DiagnosticPanels, Literature
# Supported formats: json, csv, tsv, xlsx, xls
# Max file size: 50MB
# Auth required: Curator role (via require_curator dependency)
```

**Features**:
- Gene normalization and auto-creation
- Evidence merging (avoids duplicates)
- Provider name support
- Comprehensive logging
- File validation
- Progress tracking integration

### Frontend Gaps (To Be Implemented)

1. **No API Client**: Missing `frontend/src/api/admin/ingestion.js`
2. **No View Component**: Missing `frontend/src/views/admin/AdminHybridSources.vue`
3. **No Route**: `/admin/hybrid-sources` not in router
4. **Wrong Menu Item**: Curator menu item needs to be removed

## Implementation Plan

### Phase 1: Frontend Infrastructure

#### 1.1 Create API Client

**File**: `frontend/src/api/admin/ingestion.js`

```javascript
/**
 * Hybrid Source Ingestion API
 * Handles DiagnosticPanels and Literature file uploads
 */

import apiClient from '@/api/client'

/**
 * Get list of available hybrid sources
 * @returns {Promise<Object>} List of sources with capabilities
 */
export const getHybridSources = () => apiClient.get('/api/ingestion/')

/**
 * Get status and statistics for a hybrid source
 * @param {string} sourceName - DiagnosticPanels or Literature
 * @returns {Promise<Object>} Source status and stats
 */
export const getSourceStatus = sourceName => apiClient.get(`/api/ingestion/${sourceName}/status`)

/**
 * Upload file for hybrid source
 * @param {string} sourceName - DiagnosticPanels or Literature
 * @param {File} file - File to upload
 * @param {string} providerName - Optional provider identifier
 * @returns {Promise<Object>} Upload result with statistics
 */
export const uploadSourceFile = async (sourceName, file, providerName = null) => {
  const formData = new FormData()
  formData.append('file', file)
  if (providerName) {
    formData.append('provider_name', providerName)
  }

  return apiClient.post(`/api/ingestion/${sourceName}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export default {
  getHybridSources,
  getSourceStatus,
  uploadSourceFile
}
```

**Pattern**: Follows existing `frontend/src/api/admin/pipeline.js` structure

#### 1.2 Add Router Configuration

**File**: `frontend/src/router/index.js`

```javascript
{
  path: '/admin/hybrid-sources',
  name: 'admin-hybrid-sources',
  component: () => import('../views/admin/AdminHybridSources.vue'),
  meta: { requiresAuth: true, requiresAdmin: true }
}
```

**Note**: Requires admin role (not just curator) for consistency with admin panel access

### Phase 2: Admin Panel Integration

#### 2.1 Add Card to AdminDashboard

**File**: `frontend/src/views/admin/AdminDashboard.vue`

Add to `adminSections` array (around line 274):

```javascript
{
  id: 'hybrid-sources',
  title: 'Hybrid Sources',
  description: 'Upload DiagnosticPanels and Literature data',
  icon: 'mdi-database-import',
  color: 'cyan',
  route: '/admin/hybrid-sources',
  features: [
    'Upload diagnostic panel files',
    'Upload literature evidence',
    'View upload statistics',
    'Manage provider data'
  ]
}
```

**Design**: Matches existing card pattern, uses cyan color to differentiate from data pipeline (green)

#### 2.2 Remove from UserMenu

**File**: `frontend/src/components/auth/UserMenu.vue`

**Action**: Delete lines 45-50 (Data Ingestion menu item)

```vue
<!-- REMOVE THIS BLOCK -->
<v-list-item v-if="authStore.isCurator" @click="goToDataIngestion">
  <template #prepend>
    <v-icon size="small">mdi-database-import</v-icon>
  </template>
  <v-list-item-title>Data Ingestion</v-list-item-title>
</v-list-item>
```

**Also remove**: `goToDataIngestion` method (lines 98-101)

**Rationale**: Admin functions belong in admin panel, not user menu

### Phase 3: Upload UI Component

#### 3.1 Create AdminHybridSources View

**File**: `frontend/src/views/admin/AdminHybridSources.vue`

**Key Features**:
1. **Source Selection**: Tabs for DiagnosticPanels vs Literature
2. **Drag & Drop Upload**: Modern file drop zone with visual feedback
3. **File Validation**: Client-side validation before upload
4. **Progress Tracking**: Upload progress bar with status
5. **Statistics Display**: Show current source stats (genes, providers, panels)
6. **Upload History**: Recent uploads table with results
7. **Provider Input**: Optional provider name field

**UI Structure**:

```vue
<template>
  <v-container fluid class="pa-4">
    <AdminHeader
      title="Hybrid Source Upload"
      subtitle="Upload DiagnosticPanels and Literature evidence files"
      back-route="/admin"
    />

    <!-- Source Statistics Cards -->
    <v-row class="mb-6">
      <v-col cols="12" md="4">
        <AdminStatsCard
          title="DiagnosticPanels Genes"
          :value="diagnosticStats.unique_genes"
          icon="mdi-medical-bag"
          color="cyan"
        />
      </v-col>
      <v-col cols="12" md="4">
        <AdminStatsCard
          title="Literature Genes"
          :value="literatureStats.unique_genes"
          icon="mdi-book-open-page-variant"
          color="purple"
        />
      </v-col>
      <v-col cols="12" md="4">
        <AdminStatsCard
          title="Total Evidence Records"
          :value="totalRecords"
          icon="mdi-database"
          color="primary"
        />
      </v-col>
    </v-row>

    <!-- Upload Interface -->
    <v-card class="mb-6">
      <v-tabs v-model="selectedSource" bg-color="primary">
        <v-tab value="DiagnosticPanels">
          <v-icon start>mdi-medical-bag</v-icon>
          Diagnostic Panels
        </v-tab>
        <v-tab value="Literature">
          <v-icon start>mdi-book-open-page-variant</v-icon>
          Literature
        </v-tab>
      </v-tabs>

      <v-card-text>
        <!-- Provider Name Input -->
        <v-text-field
          v-model="providerName"
          label="Provider Name (optional)"
          hint="Leave empty to use filename as provider"
          persistent-hint
          density="compact"
          class="mb-4"
        />

        <!-- Drag & Drop Zone -->
        <div
          class="upload-zone"
          :class="{ 'upload-zone--dragging': isDragging }"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="handleFileDrop"
        >
          <v-icon size="64" :color="isDragging ? 'primary' : 'grey'">
            mdi-cloud-upload
          </v-icon>
          <h3 class="text-h6 mt-4">
            {{ isDragging ? 'Drop file here' : 'Drag & drop file here' }}
          </h3>
          <p class="text-body-2 text-medium-emphasis mt-2">
            or
          </p>
          <v-btn
            color="primary"
            variant="tonal"
            prepend-icon="mdi-file-search"
            @click="$refs.fileInput.click()"
          >
            Browse Files
          </v-btn>
          <input
            ref="fileInput"
            type="file"
            hidden
            accept=".json,.csv,.tsv,.xlsx,.xls"
            @change="handleFileSelect"
          />
          <p class="text-caption text-medium-emphasis mt-4">
            Supported: JSON, CSV, TSV, Excel (max 50MB)
          </p>
        </div>

        <!-- Selected File Info -->
        <v-alert v-if="selectedFile" type="info" density="compact" class="mt-4">
          <div class="d-flex align-center">
            <v-icon start>mdi-file-document</v-icon>
            <span>{{ selectedFile.name }} ({{ formatFileSize(selectedFile.size) }})</span>
            <v-spacer />
            <v-btn
              icon="mdi-close"
              variant="text"
              size="small"
              @click="selectedFile = null"
            />
          </div>
        </v-alert>

        <!-- Upload Button -->
        <v-btn
          :disabled="!selectedFile"
          :loading="uploading"
          color="success"
          size="large"
          block
          prepend-icon="mdi-upload"
          class="mt-4"
          @click="uploadFile"
        >
          Upload {{ selectedSource }} File
        </v-btn>

        <!-- Upload Progress -->
        <v-progress-linear
          v-if="uploading"
          :model-value="uploadProgress"
          color="primary"
          height="20"
          class="mt-4"
          rounded
        >
          <template #default>
            <strong>{{ uploadProgress }}%</strong>
          </template>
        </v-progress-linear>
      </v-card-text>
    </v-card>

    <!-- Upload Results -->
    <v-card v-if="uploadResult">
      <v-card-title>Upload Results</v-card-title>
      <v-card-text>
        <v-list density="compact">
          <v-list-item>
            <template #prepend>
              <v-icon color="success">mdi-check-circle</v-icon>
            </template>
            <v-list-item-title>Status</v-list-item-title>
            <template #append>
              <v-chip :color="uploadResult.status === 'success' ? 'success' : 'error'" size="small">
                {{ uploadResult.status }}
              </v-chip>
            </template>
          </v-list-item>
          <v-list-item>
            <template #prepend>
              <v-icon>mdi-counter</v-icon>
            </template>
            <v-list-item-title>Genes Processed</v-list-item-title>
            <template #append>
              {{ uploadResult.genes_processed }}
            </template>
          </v-list-item>
          <v-list-item>
            <template #prepend>
              <v-icon color="success">mdi-plus</v-icon>
            </template>
            <v-list-item-title>Created</v-list-item-title>
            <template #append>
              {{ uploadResult.storage_stats?.created || 0 }}
            </template>
          </v-list-item>
          <v-list-item>
            <template #prepend>
              <v-icon color="info">mdi-merge</v-icon>
            </template>
            <v-list-item-title>Merged</v-list-item-title>
            <template #append>
              {{ uploadResult.storage_stats?.merged || 0 }}
            </template>
          </v-list-item>
        </v-list>
        <v-alert v-if="uploadResult.message" type="success" density="compact" class="mt-3">
          {{ uploadResult.message }}
        </v-alert>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as ingestionApi from '@/api/admin/ingestion'

// State
const selectedSource = ref('DiagnosticPanels')
const providerName = ref('')
const selectedFile = ref(null)
const isDragging = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadResult = ref(null)

const diagnosticStats = ref({ unique_genes: 0, evidence_records: 0 })
const literatureStats = ref({ unique_genes: 0, evidence_records: 0 })

// Computed
const totalRecords = computed(() =>
  diagnosticStats.value.evidence_records + literatureStats.value.evidence_records
)

// Methods
const loadStatistics = async () => {
  try {
    const [diagStats, litStats] = await Promise.all([
      ingestionApi.getSourceStatus('DiagnosticPanels'),
      ingestionApi.getSourceStatus('Literature')
    ])
    diagnosticStats.value = diagStats.data?.data || {}
    literatureStats.value = litStats.data?.data || {}
  } catch (error) {
    window.logService.error('Failed to load statistics:', error)
  }
}

const handleFileDrop = event => {
  isDragging.value = false
  const file = event.dataTransfer.files[0]
  if (file) validateAndSetFile(file)
}

const handleFileSelect = event => {
  const file = event.target.files[0]
  if (file) validateAndSetFile(file)
}

const validateAndSetFile = file => {
  // Validate file size (50MB limit)
  if (file.size > 50 * 1024 * 1024) {
    window.logService.error('File too large. Maximum size is 50MB.')
    return
  }

  // Validate file type
  const validExtensions = ['json', 'csv', 'tsv', 'xlsx', 'xls']
  const extension = file.name.split('.').pop().toLowerCase()
  if (!validExtensions.includes(extension)) {
    window.logService.error(`Invalid file type. Supported: ${validExtensions.join(', ')}`)
    return
  }

  selectedFile.value = file
  uploadResult.value = null
}

const uploadFile = async () => {
  if (!selectedFile.value) return

  uploading.value = true
  uploadProgress.value = 0

  try {
    // Simulate progress (FormData upload progress not easily trackable)
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10
      }
    }, 200)

    const response = await ingestionApi.uploadSourceFile(
      selectedSource.value,
      selectedFile.value,
      providerName.value || null
    )

    clearInterval(progressInterval)
    uploadProgress.value = 100

    uploadResult.value = response.data?.data || response.data
    selectedFile.value = null
    providerName.value = ''

    // Reload statistics
    await loadStatistics()

    window.logService.success('Upload successful!')
  } catch (error) {
    window.logService.error('Upload failed:', error)
    uploadResult.value = {
      status: 'failed',
      message: error.response?.data?.detail || 'Upload failed'
    }
  } finally {
    uploading.value = false
  }
}

const formatFileSize = bytes => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

// Lifecycle
onMounted(() => {
  loadStatistics()
})
</script>

<style scoped>
.upload-zone {
  border: 2px dashed rgb(var(--v-theme-grey-lighten-2));
  border-radius: 8px;
  padding: 48px;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
}

.upload-zone:hover {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.upload-zone--dragging {
  border-color: rgb(var(--v-theme-primary));
  background-color: rgba(var(--v-theme-primary), 0.1);
  transform: scale(1.02);
}
</style>
```

**Design Principles**:
- ✅ **DRY**: Reuses AdminHeader, AdminStatsCard components
- ✅ **KISS**: Simple drag-drop interface, minimal complexity
- ✅ **Modular**: Separate concerns (stats, upload, results)
- ✅ **Consistent**: Matches AdminPipeline.vue, AdminCacheManagement.vue patterns
- ✅ **Accessible**: Keyboard navigation, screen reader friendly

### Phase 4: Documentation

#### 4.1 Create User Guide

**File**: `docs/guides/administrator/hybrid-source-upload.md`

```markdown
# Hybrid Source Upload Guide

## Overview

Upload DiagnosticPanels and Literature evidence files through the admin panel to supplement automated data sources.

## Supported Sources

### DiagnosticPanels
Commercial diagnostic panel data from providers like:
- Blueprint Genetics
- Invitae
- GeneDx
- CeGaT
- Custom lab panels

### Literature
Manually curated literature evidence from:
- Research publications
- Case reports
- Expert reviews

## Upload Process

### 1. Access Upload Interface

1. Log in as Admin user
2. Navigate to **Admin Panel** → **Hybrid Sources**
3. Select source type tab (DiagnosticPanels or Literature)

### 2. Prepare Your File

**Supported Formats**:
- JSON (.json)
- CSV (.csv)
- TSV (.tsv)
- Excel (.xlsx, .xls)

**File Size Limit**: 50MB

**Required Fields** (CSV/TSV/Excel):
- `gene_symbol` - HGNC gene symbol
- Additional fields vary by source

**Example CSV**:
```csv
gene_symbol,panel_name,confidence
PKD1,Polycystic Kidney Disease,high
PKD2,Polycystic Kidney Disease,high
NPHS1,Congenital Nephrotic Syndrome,definitive
```

### 3. Upload File

**Method 1: Drag & Drop**
1. Drag file from your computer
2. Drop onto the upload zone
3. File automatically validated

**Method 2: Browse**
1. Click "Browse Files" button
2. Select file from file picker
3. Confirm selection

### 4. Configure Upload

**Provider Name** (optional):
- Enter provider identifier (e.g., "blueprint_genetics")
- If empty, filename used as provider name
- Used for evidence attribution

### 5. Review Results

Upload results show:
- **Status**: Success or failure
- **Genes Processed**: Total genes in file
- **Created**: New gene records added
- **Merged**: Evidence merged into existing genes

## File Format Examples

### DiagnosticPanels JSON
```json
{
  "provider": "blueprint_genetics",
  "genes": [
    {
      "gene_symbol": "PKD1",
      "panels": ["Polycystic Kidney Disease"],
      "confidence": "high"
    }
  ]
}
```

### Literature CSV
```csv
gene_symbol,pmid,publication_year,evidence_type
NPHS1,12345678,2020,case_report
NPHS2,87654321,2021,cohort_study
```

## Troubleshooting

### File Rejected
- **Issue**: "Unsupported file type"
- **Solution**: Ensure file extension is .json, .csv, .tsv, .xlsx, or .xls

### File Too Large
- **Issue**: "File size exceeds 50MB limit"
- **Solution**: Split file into smaller chunks, upload separately

### Upload Failed
- **Issue**: "Processing failed"
- **Solution**: Check file format, ensure required fields present

### Gene Not Found
- **Issue**: Gene symbol not recognized
- **Solution**: System attempts HGNC normalization, check symbol validity

## Best Practices

1. **Validate Data First**: Review file contents before upload
2. **Use Provider Names**: Helps track data sources
3. **Small Batches**: Upload 100-500 genes at a time for better tracking
4. **Check Results**: Review created/merged counts
5. **Document Sources**: Keep records of upload dates and providers

## API Integration

For automated uploads, use the REST API:

```bash
curl -X POST http://localhost:8000/api/ingestion/DiagnosticPanels/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@diagnostic_panels.csv" \
  -F "provider_name=blueprint_genetics"
```

See API documentation: `/api/docs#/ingestion`
```

#### 4.2 Update Architecture Documentation

**File**: `docs/architecture/data-sources/active-sources.md`

Update "Pending Implementation" section (lines 68-78):

```markdown
## Hybrid Sources (Upload-Based)

### 6. DiagnosticPanels
- **Status**: ✅ Fully Operational (Upload Interface)
- **Sources**: Blueprint Genetics, Invitae, GeneDx, CeGaT, custom labs
- **Upload Method**: Admin panel file upload
- **Formats**: JSON, CSV, TSV, Excel
- **Features**:
  - Provider attribution
  - Evidence merging (no duplicates)
  - Auto gene normalization

### 7. Literature (Manual)
- **Status**: ✅ Fully Operational (Upload Interface)
- **Type**: Manual curation upload
- **Format**: Excel/CSV/JSON upload
- **Use Case**: Research publications, case reports
```

## Testing Plan

### Unit Tests (Backend - Already Exists)
- File validation ✅
- Gene normalization ✅
- Evidence merging ✅

### Integration Tests (Frontend - New)

**Test File**: `frontend/src/views/admin/__tests__/AdminHybridSources.spec.js`

```javascript
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AdminHybridSources from '../AdminHybridSources.vue'

describe('AdminHybridSources', () => {
  it('renders upload interface', () => {
    const wrapper = mount(AdminHybridSources)
    expect(wrapper.find('.upload-zone').exists()).toBe(true)
  })

  it('validates file size', async () => {
    const wrapper = mount(AdminHybridSources)
    const largeFile = new File(['x'.repeat(51 * 1024 * 1024)], 'large.csv')

    await wrapper.vm.validateAndSetFile(largeFile)
    expect(wrapper.vm.selectedFile).toBeNull()
  })

  it('accepts valid file types', async () => {
    const wrapper = mount(AdminHybridSources)
    const validFile = new File(['gene_symbol\nPKD1'], 'test.csv', { type: 'text/csv' })

    await wrapper.vm.validateAndSetFile(validFile)
    expect(wrapper.vm.selectedFile).toBe(validFile)
  })
})
```

### Manual Testing Checklist

- [ ] Drag & drop CSV file → File selected
- [ ] Browse and select Excel file → File selected
- [ ] Drop 60MB file → Error shown
- [ ] Upload valid diagnostic panel → Success result
- [ ] Upload valid literature file → Success result
- [ ] Upload with provider name → Name included in evidence
- [ ] View statistics after upload → Counts updated
- [ ] Switch between tabs → UI updates correctly
- [ ] Test on mobile viewport → Responsive layout

## Deployment Steps

### 1. Code Changes
```bash
# Create new files
touch frontend/src/api/admin/ingestion.js
touch frontend/src/views/admin/AdminHybridSources.vue
touch docs/guides/administrator/hybrid-source-upload.md

# Modify existing files
# - frontend/src/router/index.js (add route)
# - frontend/src/views/admin/AdminDashboard.vue (add card)
# - frontend/src/components/auth/UserMenu.vue (remove item)
# - docs/architecture/data-sources/active-sources.md (update status)
```

### 2. Testing
```bash
# Frontend
cd frontend
npm run lint
npm run test  # Once tests written

# Backend (already tested)
cd backend
uv run pytest tests/
```

### 3. Commit Strategy
```bash
# Commit 1: API client and route
git add frontend/src/api/admin/ingestion.js
git add frontend/src/router/index.js
git commit -m "feat(admin): Add hybrid source ingestion API client and route"

# Commit 2: Remove broken user menu item
git add frontend/src/components/auth/UserMenu.vue
git commit -m "fix(ui): Remove broken /ingestion link from user menu"

# Commit 3: Admin panel integration
git add frontend/src/views/admin/AdminDashboard.vue
git add frontend/src/views/admin/AdminHybridSources.vue
git commit -m "feat(admin): Add Hybrid Sources upload UI to admin panel"

# Commit 4: Documentation
git add docs/guides/administrator/hybrid-source-upload.md
git add docs/architecture/data-sources/active-sources.md
git commit -m "docs: Add hybrid source upload user guide and update architecture"
```

### 4. Verification
- [ ] No console errors
- [ ] No router warnings
- [ ] Upload successfully processes files
- [ ] Statistics update after upload
- [ ] Admin panel card navigates correctly

## Success Metrics

### Technical
- ✅ No Vue Router warnings
- ✅ All admin functions in admin panel
- ✅ File upload works for all supported formats
- ✅ Statistics display correctly
- ✅ Evidence properly merged (no duplicates)

### User Experience
- ✅ Intuitive drag & drop interface
- ✅ Clear error messages
- ✅ Upload progress feedback
- ✅ Results clearly displayed
- ✅ Documentation comprehensive

## Future Enhancements

### Phase 2 (Optional)
1. **Upload History Table**: Show last 10 uploads with timestamps
2. **Batch Upload**: Multiple files at once
3. **Template Download**: Download CSV/Excel templates
4. **Validation Preview**: Preview parsed data before upload
5. **WebSocket Progress**: Real-time upload progress via WebSocket
6. **File Management**: View/delete uploaded files

### Phase 3 (Advanced)
1. **Automated Scraping**: Schedule scraper jobs from UI
2. **Data Diff View**: Compare new upload with existing data
3. **Rollback**: Undo specific uploads
4. **Export**: Download current hybrid source data

## References

### Code References
- Backend API: `backend/app/api/endpoints/ingestion.py`
- Existing admin views: `frontend/src/views/admin/Admin*.vue`
- API client pattern: `frontend/src/api/admin/pipeline.js`
- Vuetify file input: [VFileUpload docs](https://vuetifyjs.com/en/components/file-upload/)

### Design References
- Material Design 3: File upload patterns
- Existing admin cards: AdminDashboard.vue lines 171-274
- Upload patterns: AdminBackups.vue (similar drag-drop needs)

### Documentation
- Data sources: `docs/architecture/data-sources/`
- Admin guides: `docs/guides/administrator/`
- API docs: `/api/docs#/ingestion`
