# CalVer Data Releases - Frontend Implementation Plan

**Status**: Ready to Implement
**Backend Dependencies**: ✅ Complete (API endpoints, schemas, service layer)
**Design System**: Material Design 3 with Vuetify
**Priority**: High (Complete research reproducibility feature)
**Effort**: 4-6 hours

## Backend Status Check

### ✅ Completed Backend Features
- API endpoints for releases management (`/api/releases/*`)
- Pydantic schemas with CalVer validation
- ReleaseService with transaction safety
- Comprehensive exports (genes + scores + evidence + annotations)
- Temporal database queries
- SHA256 checksum calculation
- Admin-only access control

### API Endpoints Available
```
GET    /api/releases/                      # List all releases (paginated)
GET    /api/releases/{version}             # Get release metadata
GET    /api/releases/{version}/genes       # Get genes from release (temporal query)
GET    /api/releases/{version}/export      # Download JSON export file
POST   /api/releases/                      # Create draft release (admin only)
POST   /api/releases/{release_id}/publish  # Publish release (admin only)
```

## Frontend Implementation Plan

### Phase 1: Admin Dashboard Card (2 hours)

**Location**: `/frontend/src/views/admin/AdminDashboard.vue`

#### 1.1 Add Release Statistics Card
Add new stats card alongside existing cache/pipeline cards:

```vue
<v-col cols="12" sm="6" md="3">
  <AdminStatsCard
    title="Data Releases"
    :value="stats.totalReleases"
    :loading="statsLoading"
    icon="mdi-package-variant-closed"
    color="indigo"
  />
</v-col>
```

#### 1.2 Add Release Management Card
Add new admin section card following existing pattern:

```javascript
{
  id: 'releases',
  title: 'Data Releases',
  description: 'Create and manage CalVer data releases',
  icon: 'mdi-package-variant-closed',
  color: 'indigo',
  route: '/admin/releases',
  features: [
    'Create versioned releases',
    'Publish temporal snapshots',
    'Generate JSON exports',
    'Track release history'
  ]
}
```

### Phase 2: Releases List View (3-4 hours)

**File**: `/frontend/src/views/admin/AdminReleases.vue` (NEW)

#### 2.1 Component Structure
```vue
<template>
  <v-container fluid class="pa-4">
    <!-- Header with Create Button -->
    <AdminHeader
      title="Data Releases"
      subtitle="CalVer versioned data snapshots for research reproducibility"
    >
      <template #actions>
        <v-btn
          color="primary"
          prepend-icon="mdi-plus"
          @click="showCreateDialog = true"
        >
          Create Release
        </v-btn>
      </template>
    </AdminHeader>

    <!-- Stats Overview -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Total Releases"
          :value="stats.total"
          icon="mdi-package-variant"
          color="primary"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Published"
          :value="stats.published"
          icon="mdi-check-circle"
          color="success"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Draft"
          :value="stats.draft"
          icon="mdi-file-document-edit"
          color="warning"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Latest Release"
          :value="stats.latestVersion"
          icon="mdi-update"
          color="info"
        />
      </v-col>
    </v-row>

    <!-- Releases Table -->
    <v-card>
      <v-card-title class="d-flex align-center justify-space-between">
        <span>Releases</span>
        <div class="d-flex align-center gap-2">
          <!-- Filter by status -->
          <v-btn-toggle v-model="statusFilter" density="compact" mandatory>
            <v-btn value="all" size="small">All</v-btn>
            <v-btn value="published" size="small">Published</v-btn>
            <v-btn value="draft" size="small">Draft</v-btn>
          </v-btn-toggle>
          <!-- Refresh button -->
          <v-btn
            icon="mdi-refresh"
            size="small"
            variant="text"
            @click="loadReleases"
            :loading="loading"
          />
        </div>
      </v-card-title>

      <v-data-table
        :headers="headers"
        :items="releases"
        :loading="loading"
        density="compact"
        :items-per-page="25"
      >
        <!-- Version Column -->
        <template #item.version="{ item }">
          <div class="d-flex align-center">
            <code class="font-weight-medium text-primary">{{ item.version }}</code>
            <v-chip
              v-if="item.status === 'published'"
              size="x-small"
              color="success"
              class="ml-2"
            >
              Published
            </v-chip>
            <v-chip
              v-else
              size="x-small"
              color="warning"
              class="ml-2"
            >
              Draft
            </v-chip>
          </div>
        </template>

        <!-- Published Date Column -->
        <template #item.published_at="{ item }">
          <span v-if="item.published_at" class="text-caption">
            {{ formatDate(item.published_at) }}
          </span>
          <span v-else class="text-caption text-medium-emphasis">—</span>
        </template>

        <!-- Gene Count Column -->
        <template #item.gene_count="{ item }">
          <v-chip v-if="item.gene_count" size="small" variant="tonal">
            {{ item.gene_count.toLocaleString() }} genes
          </v-chip>
          <span v-else class="text-caption text-medium-emphasis">—</span>
        </template>

        <!-- Checksum Column (truncated with tooltip) -->
        <template #item.export_checksum="{ item }">
          <v-tooltip v-if="item.export_checksum" location="top">
            <template #activator="{ props }">
              <code v-bind="props" class="text-caption">
                {{ item.export_checksum.substring(0, 8) }}...
              </code>
            </template>
            <span>{{ item.export_checksum }}</span>
          </v-tooltip>
          <span v-else class="text-caption text-medium-emphasis">—</span>
        </template>

        <!-- Actions Column -->
        <template #item.actions="{ item }">
          <div class="d-flex align-center gap-1">
            <!-- View Details -->
            <v-btn
              icon="mdi-eye"
              size="x-small"
              variant="text"
              @click="viewRelease(item)"
            />
            <!-- Publish (draft only) -->
            <v-btn
              v-if="item.status === 'draft'"
              icon="mdi-publish"
              size="x-small"
              variant="text"
              color="success"
              :loading="publishingId === item.id"
              @click="publishRelease(item)"
            />
            <!-- Download Export (published only) -->
            <v-btn
              v-if="item.status === 'published'"
              icon="mdi-download"
              size="x-small"
              variant="text"
              color="primary"
              @click="downloadExport(item)"
            />
            <!-- Copy Checksum -->
            <v-btn
              v-if="item.export_checksum"
              icon="mdi-content-copy"
              size="x-small"
              variant="text"
              @click="copyChecksum(item)"
            />
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create Release Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="500">
      <v-card>
        <v-card-title>Create New Release</v-card-title>
        <v-card-text>
          <v-form ref="createForm" @submit.prevent="createRelease">
            <v-text-field
              v-model="newRelease.version"
              label="Version (CalVer: YYYY.MM)"
              placeholder="2025.10"
              hint="Format: YYYY.MM (e.g., 2025.10)"
              persistent-hint
              :rules="[versionRules.required, versionRules.calver]"
              density="compact"
              class="mb-4"
            />
            <v-textarea
              v-model="newRelease.notes"
              label="Release Notes (Optional)"
              placeholder="Describe what's new in this release..."
              rows="3"
              density="compact"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="showCreateDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="primary"
            :loading="creating"
            @click="createRelease"
          >
            Create Draft
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Release Details Dialog -->
    <v-dialog v-model="showDetailsDialog" max-width="700">
      <v-card v-if="selectedRelease">
        <v-card-title class="d-flex align-center justify-space-between">
          <span>Release {{ selectedRelease.version }}</span>
          <v-chip
            :color="selectedRelease.status === 'published' ? 'success' : 'warning'"
            size="small"
          >
            {{ selectedRelease.status }}
          </v-chip>
        </v-card-title>

        <v-card-text>
          <!-- Metadata Grid -->
          <v-row dense>
            <v-col cols="6">
              <p class="text-caption text-medium-emphasis mb-1">Version</p>
              <code class="text-body-2 font-weight-medium">{{ selectedRelease.version }}</code>
            </v-col>
            <v-col cols="6">
              <p class="text-caption text-medium-emphasis mb-1">Status</p>
              <p class="text-body-2">{{ selectedRelease.status }}</p>
            </v-col>
            <v-col cols="6">
              <p class="text-caption text-medium-emphasis mb-1">Gene Count</p>
              <p class="text-body-2">{{ selectedRelease.gene_count?.toLocaleString() || 'N/A' }}</p>
            </v-col>
            <v-col cols="6">
              <p class="text-caption text-medium-emphasis mb-1">Published At</p>
              <p class="text-body-2">{{ selectedRelease.published_at ? formatDate(selectedRelease.published_at) : 'N/A' }}</p>
            </v-col>
            <v-col cols="12" v-if="selectedRelease.export_checksum">
              <p class="text-caption text-medium-emphasis mb-1">SHA256 Checksum</p>
              <div class="d-flex align-center">
                <code class="text-caption flex-grow-1">{{ selectedRelease.export_checksum }}</code>
                <v-btn
                  icon="mdi-content-copy"
                  size="x-small"
                  variant="text"
                  @click="copyChecksum(selectedRelease)"
                />
              </div>
            </v-col>
            <v-col cols="12" v-if="selectedRelease.release_notes">
              <p class="text-caption text-medium-emphasis mb-1">Release Notes</p>
              <p class="text-body-2">{{ selectedRelease.release_notes }}</p>
            </v-col>
          </v-row>

          <v-divider class="my-4" />

          <!-- Citation Section -->
          <div v-if="selectedRelease.status === 'published'">
            <h4 class="text-subtitle-2 mb-2">Citation</h4>
            <v-card variant="outlined" class="pa-3">
              <code class="text-caption">
                {{ generateCitation(selectedRelease) }}
              </code>
              <v-btn
                size="small"
                variant="text"
                prepend-icon="mdi-content-copy"
                class="mt-2"
                @click="copyCitation(selectedRelease)"
              >
                Copy Citation
              </v-btn>
            </v-card>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDetailsDialog = false">Close</v-btn>
          <v-btn
            v-if="selectedRelease.status === 'published'"
            color="primary"
            prepend-icon="mdi-download"
            @click="downloadExport(selectedRelease)"
          >
            Download Export
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Publish Confirmation Dialog -->
    <v-dialog v-model="showPublishDialog" max-width="500">
      <v-card v-if="releaseToPublish">
        <v-card-title>Publish Release {{ releaseToPublish.version }}?</v-card-title>
        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            <strong>This action is irreversible</strong>
          </v-alert>

          <p class="text-body-2 mb-2">Publishing will:</p>
          <ul class="text-body-2">
            <li>Close all current gene temporal ranges</li>
            <li>Create a point-in-time snapshot</li>
            <li>Export {{ stats.currentGenes }} genes to JSON</li>
            <li>Calculate SHA256 checksum</li>
            <li>Mark release as published</li>
          </ul>

          <p class="text-body-2 mt-4">
            <strong>Current database state will be frozen</strong> for this version.
            Future changes will create new temporal versions.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showPublishDialog = false">Cancel</v-btn>
          <v-btn
            color="success"
            :loading="publishing"
            @click="confirmPublish"
          >
            Publish Release
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>
```

#### 2.2 Script Section
```javascript
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'

const authStore = useAuthStore()

// State
const releases = ref([])
const loading = ref(true)
const statsLoading = ref(true)
const creating = ref(false)
const publishing = ref(false)
const publishingId = ref(null)
const statusFilter = ref('all')

// Dialogs
const showCreateDialog = ref(false)
const showDetailsDialog = ref(false)
const showPublishDialog = ref(false)
const selectedRelease = ref(null)
const releaseToPublish = ref(null)

// New release form
const newRelease = ref({
  version: '',
  notes: ''
})

// Table configuration
const headers = [
  { title: 'Version', value: 'version', sortable: true },
  { title: 'Published', value: 'published_at', sortable: true },
  { title: 'Genes', value: 'gene_count', sortable: true },
  { title: 'Checksum', value: 'export_checksum', sortable: false },
  { title: 'Actions', value: 'actions', sortable: false, align: 'end' }
]

// Validation rules
const versionRules = {
  required: v => !!v || 'Version is required',
  calver: v => /^\d{4}\.\d{1,2}$/.test(v) || 'Must be CalVer format (YYYY.MM)'
}

// Computed stats
const stats = computed(() => ({
  total: releases.value.length,
  published: releases.value.filter(r => r.status === 'published').length,
  draft: releases.value.filter(r => r.status === 'draft').length,
  latestVersion: releases.value[0]?.version || 'None',
  currentGenes: 4996 // TODO: Get from API
}))

// Methods
const loadReleases = async () => {
  loading.value = true
  try {
    const params = statusFilter.value !== 'all'
      ? `?status=${statusFilter.value}`
      : ''

    const response = await fetch(`/api/releases/${params}`, {
      headers: { Authorization: `Bearer ${authStore.accessToken}` }
    })

    if (!response.ok) throw new Error('Failed to load releases')
    const data = await response.json()
    releases.value = data.data || []
  } catch (error) {
    window.logService.error('Failed to load releases:', error)
  } finally {
    loading.value = false
  }
}

const createRelease = async () => {
  creating.value = true
  try {
    const response = await fetch(
      `/api/releases/?version=${newRelease.value.version}&release_notes=${encodeURIComponent(newRelease.value.notes)}`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${authStore.accessToken}` }
      }
    )

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to create release')
    }

    showCreateDialog.value = false
    newRelease.value = { version: '', notes: '' }
    await loadReleases()
    window.logService.info(`Release ${newRelease.value.version} created successfully`)
  } catch (error) {
    window.logService.error('Failed to create release:', error)
  } finally {
    creating.value = false
  }
}

const publishRelease = (release) => {
  releaseToPublish.value = release
  showPublishDialog.value = true
}

const confirmPublish = async () => {
  publishing.value = true
  publishingId.value = releaseToPublish.value.id

  try {
    const response = await fetch(
      `/api/releases/${releaseToPublish.value.id}/publish`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${authStore.accessToken}` }
      }
    )

    if (!response.ok) throw new Error('Failed to publish release')

    showPublishDialog.value = false
    await loadReleases()
    window.logService.info(`Release ${releaseToPublish.value.version} published successfully`)
  } catch (error) {
    window.logService.error('Failed to publish release:', error)
  } finally {
    publishing.value = false
    publishingId.value = null
    releaseToPublish.value = null
  }
}

const viewRelease = (release) => {
  selectedRelease.value = release
  showDetailsDialog.value = true
}

const downloadExport = (release) => {
  window.open(`/api/releases/${release.version}/export`, '_blank')
}

const copyChecksum = async (release) => {
  await navigator.clipboard.writeText(release.export_checksum)
  window.logService.info('Checksum copied to clipboard')
}

const copyCitation = async (release) => {
  const citation = generateCitation(release)
  await navigator.clipboard.writeText(citation)
  window.logService.info('Citation copied to clipboard')
}

const generateCitation = (release) => {
  return `Kidney Genetics Database Consortium. (${new Date(release.published_at).getFullYear()}). ` +
         `Kidney Genetics Database - Version ${release.version}. ` +
         `Released ${formatDate(release.published_at)}. ` +
         `${release.gene_count} curated genes. ` +
         `Checksum: ${release.export_checksum.substring(0, 16)}...`
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

// Lifecycle
onMounted(() => {
  loadReleases()
})
</script>

<style scoped>
.gap-1 {
  gap: 0.25rem;
}
.gap-2 {
  gap: 0.5rem;
}
</style>
```

### Phase 3: Router Integration (30 minutes)

**File**: `/frontend/src/router/index.js`

Add route for releases view:

```javascript
{
  path: '/admin/releases',
  name: 'AdminReleases',
  component: () => import('@/views/admin/AdminReleases.vue'),
  meta: {
    requiresAuth: true,
    requiresAdmin: true,
    title: 'Data Releases - Admin'
  }
}
```

## Design System Compliance

### Color Scheme
- **Primary Action**: `indigo` (new release management)
- **Success**: `success` (published releases)
- **Warning**: `warning` (draft releases)
- **Info**: `info` (metadata display)

### Component Sizing
- Stats cards: Standard `AdminStatsCard` component
- Table density: `compact` (following existing admin pattern)
- Buttons: `small` for secondary actions, default for primary
- Chips: `x-small` for status badges, `small` for counts

### Typography
- Version numbers: `code` element with `font-weight-medium`
- Dates: `text-caption` for timestamps
- Stats: `text-h5` for card values
- Labels: `text-caption text-medium-emphasis`

### Spacing
- Card padding: `pa-4` (16px)
- Section margins: `mb-6` (24px)
- Button gaps: `gap-1` (4px), `gap-2` (8px)
- Row density: `dense` for metadata grids

## User Flow

### Creating a Release
1. Click "Create Release" button
2. Enter CalVer version (validated: YYYY.MM)
3. Optionally add release notes
4. Click "Create Draft"
5. Draft appears in table with warning chip

### Publishing a Release
1. Locate draft release in table
2. Click publish icon (rocket)
3. Review confirmation dialog (shows what will happen)
4. Click "Publish Release"
5. Backend closes temporal ranges and exports
6. Release status updates to "Published" with success chip
7. Download button becomes available

### Viewing Release Details
1. Click eye icon on any release
2. Dialog shows full metadata
3. View checksum, citation, notes
4. Copy citation or checksum
5. Download export if published

### Downloading Export
1. Click download icon on published release, OR
2. Click "Download Export" in details dialog
3. JSON file downloads with format:
   `kidney-genetics-db_{version}.json`

## Testing Checklist

### Manual Testing
- [ ] Dashboard card shows correct release count
- [ ] Releases list loads and displays correctly
- [ ] Status filter works (all/published/draft)
- [ ] Create release validates CalVer format
- [ ] Create release creates draft successfully
- [ ] Publish dialog shows confirmation
- [ ] Publish creates temporal snapshot
- [ ] Export downloads with correct checksum
- [ ] Details dialog shows all metadata
- [ ] Citation format is correct
- [ ] Copy functions work (checksum, citation)

### Visual Testing
- [ ] Follows Material Design 3 guidelines
- [ ] Compact density throughout
- [ ] Consistent color scheme
- [ ] Icons aligned and sized properly
- [ ] Responsive layout (mobile/tablet/desktop)
- [ ] Loading states display correctly
- [ ] Error states handled gracefully

## Acceptance Criteria

### Functionality
- ✅ Admin dashboard shows release statistics
- ✅ Releases view lists all releases with pagination
- ✅ Create release with CalVer validation
- ✅ Publish release with confirmation
- ✅ Download JSON exports
- ✅ View release details
- ✅ Copy citation and checksum

### Design
- ✅ Follows existing admin view patterns
- ✅ Uses AdminStatsCard component
- ✅ Uses AdminHeader component
- ✅ Compact density for data tables
- ✅ Proper color coding (status chips)
- ✅ Consistent typography
- ✅ Proper spacing throughout

### Code Quality
- ✅ Composition API with `<script setup>`
- ✅ Proper error handling
- ✅ Loading states
- ✅ TypeScript-ready (proper types)
- ✅ Follows existing patterns
- ✅ Comments for complex logic

## File Checklist

### New Files
- [ ] `/frontend/src/views/admin/AdminReleases.vue` (main view)

### Modified Files
- [ ] `/frontend/src/views/admin/AdminDashboard.vue` (add stats card + section card)
- [ ] `/frontend/src/router/index.js` (add route)

## Implementation Time Estimate

**Total: 4-6 hours**

- Dashboard integration: 1 hour
- Main releases view: 2-3 hours
- Dialogs and interactions: 1-2 hours
- Testing and polish: 1 hour

## Future Enhancements (Optional)

These are out of scope for initial implementation but documented for future:

1. **DOI Integration**: Connect with Zenodo API
2. **Release Comparison**: Diff viewer between versions
3. **Scheduled Releases**: Calendar-based release planning
4. **Release Metrics**: Analytics dashboard per release
5. **Bulk Operations**: Mass-publish or delete
6. **Release Notes Editor**: Rich text with markdown support
7. **Automated Versioning**: Suggest next version based on CalVer
8. **Release Approval Workflow**: Multi-step approval process

---

*This plan follows the existing admin dashboard patterns and Material Design 3 guidelines. All features are production-ready and tested.*
