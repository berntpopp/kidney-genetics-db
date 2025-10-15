<template>
  <v-container>
    <AdminHeader
      title="Hybrid Source Management"
      subtitle="Upload and manage DiagnosticPanels and Literature evidence"
      icon="mdi-database-import"
      icon-color="cyan"
      :breadcrumbs="ADMIN_BREADCRUMBS.hybridSources"
    />

    <!-- Source Statistics Cards -->
    <v-row class="mb-6">
      <v-col cols="12" md="4">
        <AdminStatsCard
          title="DiagnosticPanels Genes"
          :value="diagnosticStats.unique_genes"
          :loading="statsLoading"
          icon="mdi-medical-bag"
          color="cyan"
        />
      </v-col>
      <v-col cols="12" md="4">
        <AdminStatsCard
          title="Literature Genes"
          :value="literatureStats.unique_genes"
          :loading="statsLoading"
          icon="mdi-book-open-page-variant"
          color="purple"
        />
      </v-col>
      <v-col cols="12" md="4">
        <AdminStatsCard
          title="Total Evidence Records"
          :value="totalRecords"
          :loading="statsLoading"
          icon="mdi-database"
          color="primary"
        />
      </v-col>
    </v-row>

    <!-- Main Tabbed Interface -->
    <v-card>
      <!-- Source Selector Tabs -->
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

      <!-- View Selector Tabs -->
      <v-tabs v-model="activeTab" color="secondary">
        <v-tab value="upload">
          <v-icon start>mdi-upload</v-icon>
          Upload
        </v-tab>
        <v-tab value="history">
          <v-icon start>mdi-history</v-icon>
          History
        </v-tab>
        <v-tab value="audit">
          <v-icon start>mdi-shield-account</v-icon>
          Audit Trail
        </v-tab>
        <v-tab value="manage">
          <v-icon start>mdi-cog</v-icon>
          Manage
        </v-tab>
      </v-tabs>

      <!-- Tab Content -->
      <v-window v-model="activeTab">
        <!-- Upload Tab -->
        <v-window-item value="upload">
          <v-card-text>
            <!-- Upload Mode Selection -->
            <v-radio-group v-model="uploadMode" inline class="mb-4">
              <template #label>
                <span class="text-subtitle-2 font-weight-bold">Upload Mode:</span>
              </template>
              <v-radio label="Merge (add to existing data)" value="merge" />
              <v-radio label="Replace (overwrite existing data)" value="replace" color="warning" />
            </v-radio-group>

            <v-alert v-if="uploadMode === 'replace'" type="warning" density="compact" class="mb-4">
              <strong>Warning:</strong> Replace mode will delete all existing data for this
              provider/publication before uploading new data.
            </v-alert>

            <!-- Provider Name Input -->
            <v-text-field
              v-model="providerName"
              :label="
                selectedSource === 'DiagnosticPanels'
                  ? 'Provider Name (optional)'
                  : 'Publication ID (optional)'
              "
              :hint="
                selectedSource === 'DiagnosticPanels'
                  ? 'Leave empty to use filename as provider'
                  : 'Leave empty to use filename as publication ID'
              "
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
              <v-icon size="64" :color="isDragging ? 'primary' : 'grey'"> mdi-cloud-upload </v-icon>
              <h3 class="text-h6 mt-4">
                {{ isDragging ? 'Drop file here' : 'Drag & drop file here' }}
              </h3>
              <p class="text-body-2 text-medium-emphasis mt-2">or</p>
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
                <v-btn icon="mdi-close" variant="text" size="small" @click="selectedFile = null" />
              </div>
            </v-alert>

            <!-- Upload Button -->
            <v-btn
              :disabled="!selectedFile"
              :loading="uploading"
              :color="uploadMode === 'replace' ? 'warning' : 'success'"
              size="large"
              block
              prepend-icon="mdi-upload"
              class="mt-4"
              @click="uploadFile"
            >
              {{ uploadMode === 'replace' ? 'Replace' : 'Upload' }} {{ selectedSource }} File
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

            <!-- Upload Results -->
            <v-alert
              v-if="uploadResult"
              :type="uploadResult.status === 'success' ? 'success' : 'error'"
              class="mt-4"
            >
              <div class="text-subtitle-2 font-weight-bold mb-2">Upload Results</div>
              <v-list density="compact" bg-color="transparent">
                <v-list-item>
                  <template #prepend>
                    <v-icon>mdi-counter</v-icon>
                  </template>
                  <v-list-item-title>Genes Processed</v-list-item-title>
                  <template #append>
                    {{ uploadResult.genes_processed || 0 }}
                  </template>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon>mdi-plus</v-icon>
                  </template>
                  <v-list-item-title>Created</v-list-item-title>
                  <template #append>
                    {{ uploadResult.storage_stats?.created || 0 }}
                  </template>
                </v-list-item>
                <v-list-item>
                  <template #prepend>
                    <v-icon>mdi-merge</v-icon>
                  </template>
                  <v-list-item-title>Merged</v-list-item-title>
                  <template #append>
                    {{ uploadResult.storage_stats?.merged || 0 }}
                  </template>
                </v-list-item>
              </v-list>
              <p v-if="uploadResult.message" class="mt-2 mb-0">{{ uploadResult.message }}</p>
            </v-alert>
          </v-card-text>
        </v-window-item>

        <!-- History Tab -->
        <v-window-item value="history">
          <v-card-text>
            <div class="d-flex justify-end mb-4">
              <v-btn
                color="primary"
                prepend-icon="mdi-refresh"
                variant="tonal"
                @click="loadUploads"
              >
                Refresh
              </v-btn>
            </div>

            <v-data-table
              :headers="uploadHeaders"
              :items="uploads"
              :loading="uploadsLoading"
              item-value="id"
            >
              <template #item.uploaded_at="{ item }">
                {{ formatDate(item.uploaded_at) }}
              </template>
              <template #item.upload_status="{ item }">
                <v-chip :color="getStatusColor(item.upload_status)" size="small">
                  {{ item.upload_status }}
                </v-chip>
              </template>
              <template #item.actions="{ item }">
                <v-btn
                  v-if="item.upload_status !== 'deleted'"
                  icon="mdi-delete"
                  variant="text"
                  size="small"
                  color="error"
                  @click="confirmSoftDelete(item)"
                />
              </template>
              <template #no-data>
                <div class="text-center pa-4">No upload history found</div>
              </template>
            </v-data-table>
          </v-card-text>
        </v-window-item>

        <!-- Audit Tab -->
        <v-window-item value="audit">
          <v-card-text>
            <div class="d-flex justify-end mb-4">
              <v-btn
                color="primary"
                prepend-icon="mdi-refresh"
                variant="tonal"
                @click="loadAuditTrail"
              >
                Refresh
              </v-btn>
            </div>

            <v-data-table
              :headers="auditHeaders"
              :items="auditRecords"
              :loading="auditLoading"
              item-value="id"
            >
              <template #item.performed_at="{ item }">
                {{ formatDate(item.performed_at) }}
              </template>
              <template #item.action="{ item }">
                <v-chip :color="getActionColor(item.action)" size="small">
                  {{ item.action }}
                </v-chip>
              </template>
              <template #item.details="{ item }">
                <span class="text-caption">{{ JSON.stringify(item.details) }}</span>
              </template>
              <template #no-data>
                <div class="text-center pa-4">No audit records found</div>
              </template>
            </v-data-table>
          </v-card-text>
        </v-window-item>

        <!-- Manage Tab -->
        <v-window-item value="manage">
          <v-card-text>
            <div class="d-flex justify-end mb-4">
              <v-btn
                color="primary"
                prepend-icon="mdi-refresh"
                variant="tonal"
                @click="loadIdentifiers"
              >
                Refresh
              </v-btn>
            </div>

            <v-data-table
              :headers="identifierHeaders"
              :items="identifiers"
              :loading="identifiersLoading"
              item-value="identifier"
            >
              <template #item.last_updated="{ item }">
                {{ formatDate(item.last_updated) }}
              </template>
              <template #item.actions="{ item }">
                <v-btn
                  icon="mdi-delete"
                  variant="text"
                  size="small"
                  color="error"
                  @click="confirmDelete(item)"
                />
              </template>
              <template #no-data>
                <div class="text-center pa-4">
                  No {{ selectedSource === 'DiagnosticPanels' ? 'providers' : 'publications' }}
                  found
                </div>
              </template>
            </v-data-table>
          </v-card-text>
        </v-window-item>
      </v-window>
    </v-card>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="500">
      <v-card>
        <v-card-title class="bg-error">
          <v-icon start>mdi-alert</v-icon>
          Confirm Deletion
        </v-card-title>
        <v-card-text class="pt-4">
          <p>
            Are you sure you want to delete
            <strong>{{ deleteTarget?.identifier }}</strong
            >?
          </p>
          <p class="text-warning">
            This will remove <strong>{{ deleteTarget?.gene_count }} genes</strong> from
            {{ selectedSource }}.
          </p>
          <p class="text-error font-weight-bold">This action cannot be undone!</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="flat" :loading="deleting" @click="executeDelete">
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Soft Delete Confirmation Dialog -->
    <v-dialog v-model="softDeleteDialog" max-width="500">
      <v-card>
        <v-card-title class="bg-warning">
          <v-icon start>mdi-alert</v-icon>
          Soft Delete Upload
        </v-card-title>
        <v-card-text class="pt-4">
          <p>
            Mark upload <strong>{{ softDeleteTarget?.evidence_name }}</strong> as deleted?
          </p>
          <p class="text-medium-emphasis">
            This will not delete the actual data, only mark the upload record as deleted.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="softDeleteDialog = false">Cancel</v-btn>
          <v-btn color="warning" variant="flat" :loading="deleting" @click="executeSoftDelete">
            Mark as Deleted
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000" location="top">
      {{ snackbarText }}
    </v-snackbar>
  </v-container>
</template>

<script setup>
/**
 * AdminHybridSources View
 * Complete CRUD interface for DiagnosticPanels and Literature sources
 */

import { ref, computed, onMounted, watch } from 'vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as ingestionApi from '@/api/admin/ingestion'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'

// State
const selectedSource = ref('DiagnosticPanels')
const activeTab = ref('upload')
const uploadMode = ref('merge')
const providerName = ref('')
const selectedFile = ref(null)
const isDragging = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadResult = ref(null)
const statsLoading = ref(true)

const diagnosticStats = ref({ unique_genes: 0, evidence_records: 0 })
const literatureStats = ref({ unique_genes: 0, evidence_records: 0 })

// History tab
const uploads = ref([])
const uploadsLoading = ref(false)

// Audit tab
const auditRecords = ref([])
const auditLoading = ref(false)

// Manage tab
const identifiers = ref([])
const identifiersLoading = ref(false)

// Dialogs
const deleteDialog = ref(false)
const deleteTarget = ref(null)
const softDeleteDialog = ref(false)
const softDeleteTarget = ref(null)
const deleting = ref(false)

// Snackbar
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

// Table headers
const uploadHeaders = [
  { title: 'Name', key: 'evidence_name', sortable: true },
  { title: 'File', key: 'original_filename', sortable: true },
  { title: 'Status', key: 'upload_status', sortable: true },
  { title: 'Uploaded By', key: 'uploaded_by', sortable: true },
  { title: 'Uploaded', key: 'uploaded_at', sortable: true },
  { title: 'Genes', key: 'gene_count', sortable: true },
  { title: 'Normalized', key: 'genes_normalized', sortable: true },
  { title: 'Failed', key: 'genes_failed', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'center' }
]

const auditHeaders = [
  { title: 'Action', key: 'action', sortable: true },
  { title: 'Performed By', key: 'performed_by', sortable: true },
  { title: 'When', key: 'performed_at', sortable: true },
  { title: 'Details', key: 'details', sortable: false }
]

const identifierHeaders = computed(() => [
  {
    title: selectedSource.value === 'DiagnosticPanels' ? 'Provider' : 'Publication ID',
    key: 'identifier',
    sortable: true
  },
  { title: 'Genes', key: 'gene_count', sortable: true },
  { title: 'Last Updated', key: 'last_updated', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'center' }
])

// Computed
const totalRecords = computed(
  () => diagnosticStats.value.evidence_records + literatureStats.value.evidence_records
)

// Methods
const loadStatistics = async () => {
  statsLoading.value = true
  try {
    const [diagStats, litStats] = await Promise.all([
      ingestionApi.getSourceStatus('DiagnosticPanels'),
      ingestionApi.getSourceStatus('Literature')
    ])
    diagnosticStats.value = diagStats.data?.data || {}
    literatureStats.value = litStats.data?.data || {}
  } catch (error) {
    window.logService.error('Failed to load statistics:', error)
    showSnackbar('Failed to load statistics', 'error')
  } finally {
    statsLoading.value = false
  }
}

const loadUploads = async () => {
  uploadsLoading.value = true
  try {
    const response = await ingestionApi.listUploads(selectedSource.value)
    uploads.value = response.data?.data?.uploads || []
  } catch (error) {
    window.logService.error('Failed to load uploads:', error)
    showSnackbar('Failed to load upload history', 'error')
  } finally {
    uploadsLoading.value = false
  }
}

const loadAuditTrail = async () => {
  auditLoading.value = true
  try {
    const response = await ingestionApi.getAuditTrail(selectedSource.value)
    auditRecords.value = response.data?.data?.audit_records || []
  } catch (error) {
    window.logService.error('Failed to load audit trail:', error)
    showSnackbar('Failed to load audit trail', 'error')
  } finally {
    auditLoading.value = false
  }
}

const loadIdentifiers = async () => {
  identifiersLoading.value = true
  try {
    const response = await ingestionApi.listIdentifiers(selectedSource.value)
    identifiers.value = response.data?.data?.identifiers || []
  } catch (error) {
    window.logService.error('Failed to load identifiers:', error)
    showSnackbar('Failed to load identifiers', 'error')
  } finally {
    identifiersLoading.value = false
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
    showSnackbar('File too large. Maximum size is 50MB.', 'error')
    return
  }

  // Validate file type
  const validExtensions = ['json', 'csv', 'tsv', 'xlsx', 'xls']
  const extension = file.name.split('.').pop().toLowerCase()
  if (!validExtensions.includes(extension)) {
    showSnackbar(`Invalid file type. Supported: ${validExtensions.join(', ')}`, 'error')
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
      providerName.value || null,
      uploadMode.value
    )

    clearInterval(progressInterval)
    uploadProgress.value = 100

    uploadResult.value = response.data?.data || response.data
    selectedFile.value = null
    providerName.value = ''

    // Reload statistics
    await loadStatistics()

    showSnackbar('Upload successful!', 'success')
  } catch (error) {
    window.logService.error('Upload failed:', error)
    uploadResult.value = {
      status: 'failed',
      message: error.response?.data?.detail || 'Upload failed'
    }
    showSnackbar(`Upload failed: ${error.response?.data?.detail || error.message}`, 'error')
  } finally {
    uploading.value = false
  }
}

const confirmDelete = item => {
  deleteTarget.value = item
  deleteDialog.value = true
}

const executeDelete = async () => {
  if (!deleteTarget.value) return

  deleting.value = true
  try {
    await ingestionApi.deleteByIdentifier(selectedSource.value, deleteTarget.value.identifier)
    showSnackbar('Successfully deleted', 'success')
    deleteDialog.value = false
    await loadIdentifiers()
    await loadStatistics()
  } catch (error) {
    window.logService.error('Delete failed:', error)
    showSnackbar(`Delete failed: ${error.response?.data?.detail || error.message}`, 'error')
  } finally {
    deleting.value = false
  }
}

const confirmSoftDelete = item => {
  softDeleteTarget.value = item
  softDeleteDialog.value = true
}

const executeSoftDelete = async () => {
  if (!softDeleteTarget.value) return

  deleting.value = true
  try {
    await ingestionApi.softDeleteUpload(selectedSource.value, softDeleteTarget.value.id)
    showSnackbar('Upload marked as deleted', 'success')
    softDeleteDialog.value = false
    await loadUploads()
  } catch (error) {
    window.logService.error('Soft delete failed:', error)
    showSnackbar(`Soft delete failed: ${error.response?.data?.detail || error.message}`, 'error')
  } finally {
    deleting.value = false
  }
}

const formatFileSize = bytes => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

const formatDate = dateStr => {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleString()
}

const getStatusColor = status => {
  const colors = {
    completed: 'success',
    processing: 'info',
    failed: 'error',
    deleted: 'grey'
  }
  return colors[status] || 'default'
}

const getActionColor = action => {
  const colors = {
    upload: 'success',
    delete: 'error',
    soft_delete_upload: 'warning',
    merge: 'info',
    replace: 'warning'
  }
  return colors[action] || 'default'
}

const showSnackbar = (text, color = 'success') => {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

// Watch for source change to reload data
watch(selectedSource, () => {
  if (activeTab.value === 'history') loadUploads()
  if (activeTab.value === 'audit') loadAuditTrail()
  if (activeTab.value === 'manage') loadIdentifiers()
})

// Watch for tab change to load data
watch(activeTab, newTab => {
  if (newTab === 'history') loadUploads()
  if (newTab === 'audit') loadAuditTrail()
  if (newTab === 'manage') loadIdentifiers()
})

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
