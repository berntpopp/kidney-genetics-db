<template>
  <div class="container mx-auto px-4 py-6">
    <AdminHeader
      title="Data Releases"
      subtitle="Create and manage CalVer data releases"
      :icon="Package"
      icon-color="indigo"
      :breadcrumbs="ADMIN_BREADCRUMBS.releases"
    />

    <!-- Stats Overview -->
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <AdminStatsCard
        title="Total Releases"
        :value="stats.total"
        :loading="statsLoading"
        icon="mdi-package-variant"
        color="indigo"
      />
      <AdminStatsCard
        title="Published"
        :value="stats.published"
        :loading="statsLoading"
        icon="mdi-check-circle"
        color="success"
      />
      <AdminStatsCard
        title="Draft"
        :value="stats.draft"
        :loading="statsLoading"
        icon="mdi-pencil"
        color="warning"
      />
      <AdminStatsCard
        title="Latest Version"
        :value="stats.latest || 'None'"
        :loading="statsLoading"
        icon="mdi-new-box"
        color="info"
      />
    </div>

    <!-- Actions Bar -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
      <div class="space-y-2">
        <Input v-model="search" placeholder="Search releases by version or notes..." />
      </div>
      <div class="flex justify-end items-end">
        <Button @click="showCreateDialog = true">
          <PlusCircle class="size-4 mr-2" />
          Create Release
        </Button>
      </div>
    </div>

    <!-- Releases Table -->
    <Card>
      <CardContent class="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Version</TableHead>
              <TableHead>Status</TableHead>
              <TableHead class="text-right">Gene Count</TableHead>
              <TableHead>Published</TableHead>
              <TableHead>Release Notes</TableHead>
              <TableHead class="text-center">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-if="loading">
              <TableCell colspan="6" class="text-center py-8 text-muted-foreground">
                Loading...
              </TableCell>
            </TableRow>
            <TableRow v-else-if="filteredReleases.length === 0">
              <TableCell colspan="6" class="text-center py-8 text-muted-foreground">
                No releases found
              </TableCell>
            </TableRow>
            <TableRow
              v-for="item in filteredReleases"
              :key="item.id"
              class="cursor-pointer hover:bg-muted/50"
              @click="viewReleaseDetails(item)"
            >
              <TableCell>
                <code class="text-xs">{{ item.version }}</code>
              </TableCell>
              <TableCell>
                <Badge :variant="item.status === 'published' ? 'default' : 'secondary'">
                  {{ item.status }}
                </Badge>
              </TableCell>
              <TableCell class="text-right">
                <span v-if="item.gene_count">{{ item.gene_count.toLocaleString() }}</span>
                <span v-else class="text-muted-foreground">&mdash;</span>
              </TableCell>
              <TableCell>
                <span v-if="item.published_at">{{ formatDate(item.published_at) }}</span>
                <span v-else class="text-muted-foreground">Not published</span>
              </TableCell>
              <TableCell>
                <span class="text-sm truncate block max-w-[200px]">{{ item.release_notes }}</span>
              </TableCell>
              <TableCell class="text-center" @click.stop>
                <Button
                  v-if="item.status === 'draft'"
                  variant="ghost"
                  size="icon"
                  class="h-7 w-7"
                  title="Edit release"
                  @click="editRelease(item)"
                >
                  <Pencil class="size-4" />
                </Button>
                <Button
                  v-if="item.status === 'draft'"
                  variant="ghost"
                  size="icon"
                  class="h-7 w-7 text-green-600"
                  title="Publish release"
                  @click="confirmPublish(item)"
                >
                  <Send class="size-4" />
                </Button>
                <Button
                  v-if="item.status === 'draft'"
                  variant="ghost"
                  size="icon"
                  class="h-7 w-7 text-destructive"
                  title="Delete release"
                  @click="confirmDelete(item)"
                >
                  <Trash2 class="size-4" />
                </Button>
                <Button
                  v-if="item.status === 'published'"
                  variant="ghost"
                  size="icon"
                  class="h-7 w-7"
                  title="Download export"
                  @click="downloadExport(item)"
                >
                  <Download class="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  class="h-7 w-7"
                  title="View details"
                  @click="viewReleaseDetails(item)"
                >
                  <Info class="size-4" />
                </Button>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>

    <!-- Create/Edit Release Dialog -->
    <Dialog v-model:open="showCreateDialog">
      <DialogContent class="max-w-[600px]">
        <DialogHeader>
          <DialogTitle>{{ editingRelease ? 'Edit Release' : 'Create New Release' }}</DialogTitle>
        </DialogHeader>
        <div class="space-y-4">
          <div class="space-y-2">
            <Label>Version (CalVer: YYYY.MM)</Label>
            <Input v-model="releaseFormData.version" placeholder="2025.10" />
            <p class="text-xs text-muted-foreground">
              Format: YYYY.MM (e.g., 2025.10 for October 2025)
            </p>
            <p v-if="versionError" class="text-xs text-destructive">{{ versionError }}</p>
          </div>

          <div class="space-y-2">
            <Label>Release Notes</Label>
            <textarea
              v-model="releaseFormData.release_notes"
              class="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              rows="4"
              placeholder="Describe what's new in this release..."
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="closeCreateDialog">Cancel</Button>
          <Button
            :disabled="creating || !isFormValid"
            @click="editingRelease ? updateRelease() : createRelease()"
          >
            {{ creating ? 'Saving...' : editingRelease ? 'Update' : 'Create Draft' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Delete Confirmation Dialog -->
    <AlertDialog v-model:open="showDeleteDialog">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete Release?</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to delete draft release
            <strong>{{ deletingRelease?.version }}</strong
            >? This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            :disabled="deleting"
            @click="deleteRelease"
          >
            {{ deleting ? 'Deleting...' : 'Delete' }}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <!-- Publish Confirmation Dialog -->
    <AlertDialog v-model:open="showPublishDialog">
      <AlertDialogContent class="max-w-[500px]">
        <AlertDialogHeader>
          <AlertDialogTitle>Publish Release {{ publishingRelease?.version }}?</AlertDialogTitle>
          <AlertDialogDescription as="div">
            <Alert variant="destructive" class="mb-4">
              <AlertDescription>
                <strong>This action will:</strong>
                <ul class="mt-2 list-disc list-inside">
                  <li>Close all current gene temporal ranges</li>
                  <li>Export genes to JSON file</li>
                  <li>Calculate SHA256 checksum</li>
                  <li>Mark release as published</li>
                </ul>
              </AlertDescription>
            </Alert>
            <p class="text-sm">
              This operation cannot be undone. Are you sure you want to publish this release?
            </p>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction :disabled="publishing" @click="publishRelease">
            {{ publishing ? 'Publishing...' : 'Publish Release' }}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <!-- Release Details Dialog -->
    <Dialog v-model:open="showDetailsDialog">
      <DialogContent class="max-w-[700px]">
        <DialogHeader>
          <DialogTitle class="flex items-center gap-2">
            Release {{ selectedRelease?.version }}
            <Badge
              v-if="selectedRelease"
              :variant="selectedRelease.status === 'published' ? 'default' : 'secondary'"
            >
              {{ selectedRelease.status }}
            </Badge>
          </DialogTitle>
        </DialogHeader>

        <div v-if="selectedRelease" class="space-y-4">
          <!-- Release Information -->
          <div class="space-y-3">
            <div class="flex items-center gap-3 border-b pb-2">
              <Package class="size-5 text-indigo-600 dark:text-indigo-400" />
              <div>
                <div class="text-xs text-muted-foreground">Version</div>
                <code>{{ selectedRelease.version }}</code>
              </div>
            </div>

            <div class="flex items-center gap-3 border-b pb-2">
              <Calendar class="size-5" />
              <div>
                <div class="text-xs text-muted-foreground">Created</div>
                <span class="text-sm">{{ formatDate(selectedRelease.created_at) }}</span>
              </div>
            </div>

            <div v-if="selectedRelease.published_at" class="flex items-center gap-3 border-b pb-2">
              <CalendarCheck class="size-5 text-green-600 dark:text-green-400" />
              <div>
                <div class="text-xs text-muted-foreground">Published</div>
                <span class="text-sm">{{ formatDate(selectedRelease.published_at) }}</span>
              </div>
            </div>

            <div v-if="selectedRelease.gene_count" class="flex items-center gap-3 border-b pb-2">
              <Dna class="size-5" />
              <div>
                <div class="text-xs text-muted-foreground">Gene Count</div>
                <span class="text-sm">{{ selectedRelease.gene_count.toLocaleString() }} genes</span>
              </div>
            </div>

            <div
              v-if="selectedRelease.export_checksum"
              class="flex items-center gap-3 border-b pb-2"
            >
              <ShieldCheck class="size-5 text-green-600 dark:text-green-400" />
              <div class="flex-1">
                <div class="text-xs text-muted-foreground">Checksum (SHA256)</div>
                <div class="flex items-center gap-1">
                  <code class="text-xs">{{ selectedRelease.export_checksum }}</code>
                  <Button
                    variant="ghost"
                    size="icon"
                    class="h-6 w-6"
                    title="Copy checksum"
                    @click="copyToClipboard(selectedRelease.export_checksum)"
                  >
                    <Copy class="size-3" />
                  </Button>
                </div>
              </div>
            </div>
          </div>

          <!-- Release Notes -->
          <Separator />
          <div>
            <h4 class="text-sm font-semibold mb-2">Release Notes</h4>
            <p v-if="selectedRelease.release_notes" class="text-sm">
              {{ selectedRelease.release_notes }}
            </p>
            <p v-else class="text-sm text-muted-foreground">No release notes provided.</p>
          </div>

          <!-- Citation -->
          <Separator />
          <div>
            <h4 class="text-sm font-semibold mb-2">Citation</h4>
            <div class="rounded-md border p-3 relative">
              <code class="text-xs">{{ generateCitation(selectedRelease) }}</code>
              <Button
                variant="ghost"
                size="icon"
                class="h-6 w-6 absolute top-2 right-2"
                title="Copy citation"
                @click="copyToClipboard(generateCitation(selectedRelease))"
              >
                <Copy class="size-3" />
              </Button>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" @click="showDetailsDialog = false">Close</Button>
          <Button
            v-if="selectedRelease?.status === 'published'"
            @click="downloadExport(selectedRelease)"
          >
            <Download class="size-4 mr-2" />
            Download Export
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
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
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '@/components/ui/alert-dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import {
  Calendar,
  CalendarCheck,
  Copy,
  Dna,
  Download,
  Info,
  Package,
  Pencil,
  PlusCircle,
  Send,
  ShieldCheck,
  Trash2
} from 'lucide-vue-next'

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

// CalVer validation
const versionError = computed(() => {
  if (!releaseFormData.value.version) return 'Version is required'
  if (!/^\d{4}\.\d{1,2}$/.test(releaseFormData.value.version)) {
    return 'Version must be CalVer format YYYY.MM (e.g., 2025.10)'
  }
  return null
})

const isFormValid = computed(() => {
  return releaseFormData.value.version && !versionError.value
})

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
  if (!isFormValid.value) return

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
  if (!isFormValid.value || !editingRelease.value) return

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

const viewReleaseDetails = item => {
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
