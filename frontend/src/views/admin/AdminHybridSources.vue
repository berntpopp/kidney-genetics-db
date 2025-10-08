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
              <v-icon :color="uploadResult.status === 'success' ? 'success' : 'error'">
                {{ uploadResult.status === 'success' ? 'mdi-check-circle' : 'mdi-alert-circle' }}
              </v-icon>
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

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000" location="top">
      {{ snackbarText }}
    </v-snackbar>
  </v-container>
</template>

<script setup>
/**
 * AdminHybridSources View
 * File upload interface for DiagnosticPanels and Literature sources
 */

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
const statsLoading = ref(true)

const diagnosticStats = ref({ unique_genes: 0, evidence_records: 0 })
const literatureStats = ref({ unique_genes: 0, evidence_records: 0 })

// Snackbar
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

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
      providerName.value || null
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

const formatFileSize = bytes => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

const showSnackbar = (text, color = 'success') => {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
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
