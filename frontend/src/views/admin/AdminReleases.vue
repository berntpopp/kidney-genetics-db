<template>
  <v-container>
    <AdminHeader
      title="Data Releases"
      subtitle="Create and manage CalVer data releases"
      :icon="Package"
      icon-color="indigo"
      :breadcrumbs="ADMIN_BREADCRUMBS.releases"
    />

    <!-- Stats Overview -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Total Releases"
          :value="stats.total"
          :loading="statsLoading"
          icon="mdi-package-variant"
          color="indigo"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Published"
          :value="stats.published"
          :loading="statsLoading"
          icon="mdi-check-circle"
          color="success"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Draft"
          :value="stats.draft"
          :loading="statsLoading"
          icon="mdi-pencil"
          color="warning"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Latest Version"
          :value="stats.latest || 'None'"
          :loading="statsLoading"
          icon="mdi-new-box"
          color="info"
        />
      </v-col>
    </v-row>

    <!-- Actions Bar -->
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="Search releases by version or notes"
          density="compact"
          variant="outlined"
          clearable
          hide-details
        />
      </v-col>
      <v-col cols="12" md="6" class="text-right">
        <v-btn color="indigo" prepend-icon="mdi-plus" size="small" @click="showCreateDialog = true">
          Create Release
        </v-btn>
      </v-col>
    </v-row>

    <!-- Releases Table -->
    <v-card>
      <v-data-table
        :headers="headers"
        :items="filteredReleases"
        :loading="loading"
        :search="search"
        density="compact"
        item-value="id"
        hover
        @click:row="viewReleaseDetails"
      >
        <!-- Version column -->
        <template #item.version="{ item }">
          <code class="text-caption">{{ item.version }}</code>
        </template>

        <!-- Status column -->
        <template #item.status="{ item }">
          <v-chip :color="item.status === 'published' ? 'success' : 'warning'" size="small" label>
            {{ item.status }}
          </v-chip>
        </template>

        <!-- Gene count column -->
        <template #item.gene_count="{ item }">
          <span v-if="item.gene_count">{{ item.gene_count.toLocaleString() }}</span>
          <span v-else class="text-medium-emphasis">—</span>
        </template>

        <!-- Published date column -->
        <template #item.published_at="{ item }">
          <span v-if="item.published_at">
            {{ formatDate(item.published_at) }}
          </span>
          <span v-else class="text-medium-emphasis">Not published</span>
        </template>

        <!-- Actions column -->
        <template #item.actions="{ item }">
          <v-btn
            v-if="item.status === 'draft'"
            icon="mdi-pencil"
            size="x-small"
            variant="text"
            color="primary"
            title="Edit release"
            @click.stop="editRelease(item)"
          />
          <v-btn
            v-if="item.status === 'draft'"
            icon="mdi-publish"
            size="x-small"
            variant="text"
            color="success"
            title="Publish release"
            @click.stop="confirmPublish(item)"
          />
          <v-btn
            v-if="item.status === 'draft'"
            icon="mdi-delete"
            size="x-small"
            variant="text"
            color="error"
            title="Delete release"
            @click.stop="confirmDelete(item)"
          />
          <v-btn
            v-if="item.status === 'published'"
            icon="mdi-download"
            size="x-small"
            variant="text"
            color="primary"
            title="Download export"
            @click.stop="downloadExport(item)"
          />
          <v-btn
            icon="mdi-information"
            size="x-small"
            variant="text"
            title="View details"
            @click.stop="viewReleaseDetails(null, { item })"
          />
        </template>
      </v-data-table>
    </v-card>

    <!-- Create/Edit Release Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="600">
      <v-card>
        <v-card-title>{{ editingRelease ? 'Edit Release' : 'Create New Release' }}</v-card-title>

        <v-card-text>
          <v-form ref="releaseForm" v-model="formValid">
            <v-text-field
              v-model="releaseFormData.version"
              label="Version (CalVer: YYYY.MM)"
              required
              :rules="calverRules"
              density="compact"
              variant="outlined"
              placeholder="2025.10"
              hint="Format: YYYY.MM (e.g., 2025.10 for October 2025)"
              persistent-hint
            />

            <v-textarea
              v-model="releaseFormData.release_notes"
              label="Release Notes"
              density="compact"
              variant="outlined"
              rows="4"
              class="mt-4"
              placeholder="Describe what's new in this release..."
            />
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="closeCreateDialog">Cancel</v-btn>
          <v-btn
            color="indigo"
            variant="flat"
            :loading="creating"
            :disabled="!formValid"
            @click="editingRelease ? updateRelease() : createRelease()"
          >
            {{ editingRelease ? 'Update' : 'Create Draft' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title>Delete Release?</v-card-title>
        <v-card-text>
          Are you sure you want to delete draft release
          <strong>{{ deletingRelease?.version }}</strong
          >? This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDeleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="flat" :loading="deleting" @click="deleteRelease">
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Publish Confirmation Dialog -->
    <v-dialog v-model="showPublishDialog" max-width="500">
      <v-card>
        <v-card-title>Publish Release {{ publishingRelease?.version }}?</v-card-title>
        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            <strong>This action will:</strong>
            <ul class="mt-2">
              <li>Close all current gene temporal ranges</li>
              <li>Export genes to JSON file</li>
              <li>Calculate SHA256 checksum</li>
              <li>Mark release as published</li>
            </ul>
          </v-alert>
          <p class="text-body-2">
            This operation cannot be undone. Are you sure you want to publish this release?
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showPublishDialog = false">Cancel</v-btn>
          <v-btn color="success" variant="flat" :loading="publishing" @click="publishRelease">
            Publish Release
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Release Details Dialog -->
    <v-dialog v-model="showDetailsDialog" max-width="700">
      <v-card v-if="selectedRelease">
        <v-card-title>
          Release {{ selectedRelease.version }}
          <v-chip
            :color="selectedRelease.status === 'published' ? 'success' : 'warning'"
            size="small"
            label
            class="ml-2"
          >
            {{ selectedRelease.status }}
          </v-chip>
        </v-card-title>

        <v-card-text>
          <!-- Release Information -->
          <v-list density="compact">
            <v-list-item>
              <template #prepend>
                <Package class="size-5 text-indigo-600 dark:text-indigo-400" />
              </template>
              <v-list-item-title>Version</v-list-item-title>
              <v-list-item-subtitle>
                <code>{{ selectedRelease.version }}</code>
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <template #prepend>
                <Calendar class="size-5" />
              </template>
              <v-list-item-title>Created</v-list-item-title>
              <v-list-item-subtitle>
                {{ formatDate(selectedRelease.created_at) }}
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="selectedRelease.published_at">
              <template #prepend>
                <CalendarCheck class="size-5 text-green-600 dark:text-green-400" />
              </template>
              <v-list-item-title>Published</v-list-item-title>
              <v-list-item-subtitle>
                {{ formatDate(selectedRelease.published_at) }}
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="selectedRelease.gene_count">
              <template #prepend>
                <Dna class="size-5" />
              </template>
              <v-list-item-title>Gene Count</v-list-item-title>
              <v-list-item-subtitle>
                {{ selectedRelease.gene_count.toLocaleString() }} genes
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="selectedRelease.export_checksum">
              <template #prepend>
                <ShieldCheck class="size-5 text-green-600 dark:text-green-400" />
              </template>
              <v-list-item-title>Checksum (SHA256)</v-list-item-title>
              <v-list-item-subtitle>
                <code class="text-caption">{{ selectedRelease.export_checksum }}</code>
                <v-btn
                  icon="mdi-content-copy"
                  size="x-small"
                  variant="text"
                  title="Copy checksum"
                  @click="copyToClipboard(selectedRelease.export_checksum)"
                />
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>

          <!-- Release Notes -->
          <v-divider class="my-4" />
          <h4 class="text-subtitle-1 mb-2">Release Notes</h4>
          <p v-if="selectedRelease.release_notes" class="text-body-2">
            {{ selectedRelease.release_notes }}
          </p>
          <p v-else class="text-body-2 text-medium-emphasis">No release notes provided.</p>

          <!-- Citation -->
          <v-divider class="my-4" />
          <h4 class="text-subtitle-1 mb-2">Citation</h4>
          <v-card variant="outlined" class="pa-3">
            <code class="text-caption">{{ generateCitation(selectedRelease) }}</code>
            <v-btn
              icon="mdi-content-copy"
              size="x-small"
              variant="text"
              title="Copy citation"
              class="float-right"
              @click="copyToClipboard(generateCitation(selectedRelease))"
            />
          </v-card>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDetailsDialog = false">Close</v-btn>
          <v-btn
            v-if="selectedRelease.status === 'published'"
            color="primary"
            variant="flat"
            prepend-icon="mdi-download"
            @click="downloadExport(selectedRelease)"
          >
            Download Export
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
/**
 * Data Releases Management View
 * Create and manage CalVer data releases with comprehensive UI/UX
 */

import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'
import { toast } from 'vue-sonner'
import { Calendar, CalendarCheck, Dna, Package, ShieldCheck } from 'lucide-vue-next'

const authStore = useAuthStore()

// State
const releases = ref([])
const loading = ref(false)
const statsLoading = ref(false)
const search = ref('')
const showCreateDialog = ref(false)
const showPublishDialog = ref(false)
const showDeleteDialog = ref(false)
const showDetailsDialog = ref(false)
const selectedRelease = ref(null)
const publishingRelease = ref(null)
const editingRelease = ref(null)
const deletingRelease = ref(null)
const creating = ref(false)
const publishing = ref(false)
const deleting = ref(false)
const formValid = ref(false)
const releaseForm = ref(null)

// Stats
const stats = ref({
  total: 0,
  published: 0,
  draft: 0,
  latest: null
})

// Form data
const releaseFormData = ref({
  version: '',
  release_notes: ''
})

// CalVer validation rules
const calverRules = [
  v => !!v || 'Version is required',
  v => /^\d{4}\.\d{1,2}$/.test(v) || 'Version must be CalVer format YYYY.MM (e.g., 2025.10)'
]

// Table configuration
const headers = [
  { title: 'Version', key: 'version', align: 'start' },
  { title: 'Status', key: 'status' },
  { title: 'Gene Count', key: 'gene_count', align: 'end' },
  { title: 'Published', key: 'published_at' },
  { title: 'Release Notes', key: 'release_notes' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'center' }
]

// Computed
const filteredReleases = computed(() => {
  if (!search.value) return releases.value

  const searchLower = search.value.toLowerCase()
  return releases.value.filter(
    release =>
      release.version?.toLowerCase().includes(searchLower) ||
      release.release_notes?.toLowerCase().includes(searchLower)
  )
})

// Methods
const loadReleases = async () => {
  loading.value = true
  try {
    const response = await fetch('/api/releases/', {
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })

    if (!response.ok) throw new Error('Failed to fetch releases')

    const data = await response.json()
    releases.value = data.data || []
    updateStats()
  } catch (error) {
    window.logService.error('Failed to load releases:', error)
    toast.error('Failed to load releases', { duration: Infinity })
  } finally {
    loading.value = false
  }
}

const updateStats = () => {
  statsLoading.value = true
  stats.value = {
    total: releases.value.length,
    published: releases.value.filter(r => r.status === 'published').length,
    draft: releases.value.filter(r => r.status === 'draft').length,
    latest:
      releases.value.length > 0
        ? releases.value.reduce((latest, r) => (r.version > latest.version ? r : latest)).version
        : null
  }
  statsLoading.value = false
}

const formatDate = dateString => {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

const createRelease = async () => {
  if (!formValid.value) return

  creating.value = true
  try {
    const response = await fetch(
      `/api/releases/?version=${encodeURIComponent(releaseFormData.value.version)}&release_notes=${encodeURIComponent(releaseFormData.value.release_notes || '')}`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authStore.accessToken}`
        }
      }
    )

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to create release')
    }

    const newRelease = await response.json()
    releases.value.push(newRelease)
    updateStats()

    toast.success(`Release ${newRelease.version} created successfully`, { duration: 5000 })
    closeCreateDialog()
  } catch (error) {
    window.logService.error('Failed to create release:', error)
    toast.error(error.message || 'Failed to create release', { duration: Infinity })
  } finally {
    creating.value = false
  }
}

const closeCreateDialog = () => {
  showCreateDialog.value = false
  editingRelease.value = null
  releaseFormData.value = {
    version: '',
    release_notes: ''
  }
  releaseForm.value?.reset()
}

const editRelease = release => {
  editingRelease.value = release
  releaseFormData.value = {
    version: release.version,
    release_notes: release.release_notes || ''
  }
  showCreateDialog.value = true
}

const updateRelease = async () => {
  if (!formValid.value || !editingRelease.value) return

  creating.value = true
  try {
    const response = await fetch(`/api/releases/${editingRelease.value.id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authStore.accessToken}`
      },
      body: JSON.stringify({
        version: releaseFormData.value.version,
        release_notes: releaseFormData.value.release_notes
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to update release')
    }

    const updated = await response.json()

    // Update local state
    const index = releases.value.findIndex(r => r.id === updated.id)
    if (index > -1) {
      releases.value[index] = updated
    }
    updateStats()

    toast.success(`Release ${updated.version} updated successfully`, { duration: 5000 })
    closeCreateDialog()
  } catch (error) {
    window.logService.error('Failed to update release:', error)
    toast.error(error.message || 'Failed to update release', { duration: Infinity })
  } finally {
    creating.value = false
  }
}

const confirmDelete = release => {
  deletingRelease.value = release
  showDeleteDialog.value = true
}

const deleteRelease = async () => {
  if (!deletingRelease.value) return

  deleting.value = true
  try {
    const response = await fetch(`/api/releases/${deletingRelease.value.id}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to delete release')
    }

    // Remove from local state
    releases.value = releases.value.filter(r => r.id !== deletingRelease.value.id)
    updateStats()

    toast.success(`Release ${deletingRelease.value.version} deleted successfully`, {
      duration: 5000
    })
    showDeleteDialog.value = false
    deletingRelease.value = null
  } catch (error) {
    window.logService.error('Failed to delete release:', error)
    toast.error(error.message || 'Failed to delete release', { duration: Infinity })
  } finally {
    deleting.value = false
  }
}

const confirmPublish = release => {
  publishingRelease.value = release
  showPublishDialog.value = true
}

const publishRelease = async () => {
  if (!publishingRelease.value) return

  publishing.value = true
  try {
    const response = await fetch(`/api/releases/${publishingRelease.value.id}/publish`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to publish release')
    }

    const published = await response.json()

    // Update local state
    const index = releases.value.findIndex(r => r.id === published.id)
    if (index > -1) {
      releases.value[index] = published
    }
    updateStats()

    toast.success(`Release ${published.version} published successfully`, { duration: 5000 })
    showPublishDialog.value = false
    publishingRelease.value = null
  } catch (error) {
    window.logService.error('Failed to publish release:', error)
    toast.error(error.message || 'Failed to publish release', { duration: Infinity })
  } finally {
    publishing.value = false
  }
}

const viewReleaseDetails = (event, { item }) => {
  selectedRelease.value = item
  showDetailsDialog.value = true
}

const downloadExport = async release => {
  try {
    const response = await fetch(`/api/releases/${release.version}/export`, {
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })

    if (!response.ok) throw new Error('Failed to download export')

    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `kidney-genetics-db_${release.version}.json`
    a.click()
    URL.revokeObjectURL(url)

    toast.success(`Export downloaded: ${release.version}`, { duration: 5000 })
  } catch (error) {
    window.logService.error('Failed to download export:', error)
    toast.error('Failed to download export', { duration: Infinity })
  }
}

const generateCitation = release => {
  const year = new Date(release.published_at).getFullYear()
  return `Kidney Genetics Database. (${year}). Release ${release.version}. [Data set]. Retrieved from ${window.location.origin}/releases/${release.version}. SHA256: ${release.export_checksum}`
}

const copyToClipboard = async text => {
  try {
    await navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard', { duration: 5000 })
  } catch (error) {
    window.logService.error('Failed to copy to clipboard:', error)
    toast.error('Failed to copy to clipboard', { duration: Infinity })
  }
}

// Lifecycle
onMounted(() => {
  loadReleases()
})
</script>
