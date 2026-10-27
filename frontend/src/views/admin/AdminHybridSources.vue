<template>
  <div :class="PAGE_CONTAINER">
    <AdminHeader
      title="Hybrid Sources"
      subtitle="Upload and manage diagnostic panel and literature evidence"
    />

    <!-- Source Statistics Cards -->
    <div class="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
      <AdminStatsCard
        :title="`${sourceDisplayName('DiagnosticPanels')}: genes`"
        :value="diagnosticStats.unique_genes"
        :loading="statsLoading"
        :icon="BriefcaseMedical"
      />
      <AdminStatsCard
        :title="`${sourceDisplayName('Literature')}: genes`"
        :value="literatureStats.unique_genes"
        :loading="statsLoading"
        :icon="BookOpen"
      />
      <AdminStatsCard
        title="Evidence records"
        :value="totalRecords"
        :loading="statsLoading"
        :icon="Database"
      />
    </div>

    <!-- Source selector, then the view tabs for the selected source -->
    <Card>
      <Tabs v-model="selectedSource" class="w-full">
        <div class="border-b px-4 pt-4">
          <TabsList>
            <TabsTrigger v-for="src in SOURCES" :key="src.key" :value="src.key">
              <component :is="src.icon" class="size-4" aria-hidden="true" />
              {{ sourceDisplayName(src.key) }}
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent v-for="src in SOURCES" :key="src.key" :value="src.key" class="m-0 p-0">
          <Tabs v-model="activeTab">
            <div class="border-b px-4">
              <TabsList class="h-auto flex-wrap bg-transparent">
                <TabsTrigger value="upload">
                  <Upload class="size-4" aria-hidden="true" />
                  Upload
                </TabsTrigger>
                <TabsTrigger value="history">
                  <History class="size-4" aria-hidden="true" />
                  History
                </TabsTrigger>
                <TabsTrigger value="audit">
                  <ShieldCheck class="size-4" aria-hidden="true" />
                  Audit Trail
                </TabsTrigger>
                <TabsTrigger value="manage">
                  <Cog class="size-4" aria-hidden="true" />
                  Manage
                </TabsTrigger>
              </TabsList>
            </div>

            <!-- Upload -->
            <TabsContent value="upload" class="space-y-4 p-6">
              <fieldset>
                <legend class="mb-2 text-sm font-semibold">Upload mode</legend>
                <RadioGroup v-model="uploadMode" class="grid gap-2 sm:grid-cols-2">
                  <Label
                    v-for="mode in UPLOAD_MODES"
                    :key="mode.value"
                    :for="`mode-${mode.value}`"
                    class="flex cursor-pointer items-start gap-3 rounded-lg border p-3 font-normal has-[[data-state=checked]]:border-primary"
                  >
                    <RadioGroupItem :id="`mode-${mode.value}`" :value="mode.value" class="mt-0.5" />
                    <span>
                      <span class="block text-sm font-medium">{{ mode.title }}</span>
                      <span class="block text-xs text-muted-foreground">{{ mode.hint }}</span>
                    </span>
                  </Label>
                </RadioGroup>
              </fieldset>

              <div class="space-y-2">
                <Label for="provider-name">{{ identifierLabel }} (optional)</Label>
                <Input
                  id="provider-name"
                  v-model="providerName"
                  :placeholder="`Leave empty to use the filename as ${identifierLabel.toLowerCase()}`"
                />
              </div>

              <!-- Drag & drop zone; the Browse button is the keyboard path -->
              <div
                class="cursor-pointer rounded-lg border-2 border-dashed p-10 text-center transition-colors"
                :class="isDragging ? 'border-primary bg-primary/5' : 'border-border'"
                @click="openFilePicker"
                @dragover.prevent="isDragging = true"
                @dragleave.prevent="isDragging = false"
                @drop.prevent="handleFileDrop"
              >
                <CloudUpload
                  class="mx-auto mb-3 size-12"
                  :class="isDragging ? 'text-primary' : 'text-muted-foreground'"
                  aria-hidden="true"
                />
                <p class="text-base font-medium">
                  {{ isDragging ? 'Drop file here' : 'Drag and drop a file here' }}
                </p>
                <p class="mt-1 text-sm text-muted-foreground">or</p>
                <Button variant="outline" class="mt-2" @click.stop="openFilePicker">
                  Browse files
                </Button>
                <input
                  ref="fileInput"
                  type="file"
                  class="hidden"
                  accept=".json,.csv,.tsv,.xlsx,.xls"
                  @change="handleFileSelect"
                />
                <p class="mt-3 text-xs text-muted-foreground">
                  JSON, CSV, TSV or Excel, up to 50 MB
                </p>
              </div>

              <div
                v-if="selectedFile"
                class="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm"
              >
                <FileText class="size-4 text-muted-foreground" aria-hidden="true" />
                <span class="min-w-0 flex-1 truncate">
                  {{ selectedFile.name }}
                  <span class="text-muted-foreground tabular-nums"
                    >({{ formatFileSize(selectedFile.size) }})</span
                  >
                </span>
                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label="Remove selected file"
                      @click="selectedFile = null"
                    >
                      <X class="size-4" aria-hidden="true" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Remove selected file</TooltipContent>
                </Tooltip>
              </div>

              <Button
                :disabled="!selectedFile || uploading"
                :variant="uploadMode === 'replace' ? 'destructive' : 'default'"
                class="w-full"
                size="lg"
                @click="requestUpload"
              >
                <Upload class="size-4" aria-hidden="true" />
                {{ uploading ? 'Uploading…' : uploadLabel }}
              </Button>

              <!-- Indeterminate: the API reports no byte progress -->
              <p
                v-if="uploading"
                role="status"
                class="flex items-center justify-center gap-2 text-xs text-muted-foreground"
              >
                <Loader2 class="size-4 motion-safe:animate-spin" aria-hidden="true" />
                Uploading and processing file…
              </p>

              <div
                v-if="uploadResult"
                class="rounded-lg border p-4 text-sm"
                :class="uploadResult.status === 'failed' && 'border-danger/30 bg-danger-subtle'"
              >
                <div class="mb-2 flex items-center gap-2 font-semibold">
                  Upload result
                  <StatusBadge :status="uploadResult.status" />
                </div>
                <dl v-if="uploadResult.status !== 'failed'" class="grid grid-cols-3 gap-2">
                  <div>
                    <dt class="text-xs text-muted-foreground">Genes processed</dt>
                    <dd class="font-medium tabular-nums">
                      {{ uploadResult.genes_processed || 0 }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-xs text-muted-foreground">Created</dt>
                    <dd class="font-medium tabular-nums">
                      {{ uploadResult.storage_stats?.created || 0 }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-xs text-muted-foreground">Merged</dt>
                    <dd class="font-medium tabular-nums">
                      {{ uploadResult.storage_stats?.merged || 0 }}
                    </dd>
                  </div>
                </dl>
                <p v-if="uploadResult.message" class="mt-2">{{ uploadResult.message }}</p>
              </div>
            </TabsContent>

            <!-- History -->
            <TabsContent value="history" class="p-6">
              <div class="mb-4 flex justify-end">
                <Button variant="outline" size="sm" :disabled="uploadsLoading" @click="loadUploads">
                  <RefreshCw class="size-4" aria-hidden="true" />
                  Refresh
                </Button>
              </div>
              <DataState
                :loading="uploadsLoading && !uploads.length"
                :error="uploadsError"
                error-title="Could not load upload history"
                :empty="!uploads.length"
                empty-message="No uploads yet."
                @retry="loadUploads"
              >
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>File</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Uploaded by</TableHead>
                      <TableHead>Uploaded</TableHead>
                      <TableHead class="text-right">Genes</TableHead>
                      <TableHead class="text-right">Normalized</TableHead>
                      <TableHead class="text-right">Failed</TableHead>
                      <TableHead><span class="sr-only">Actions</span></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow v-for="item in uploads" :key="item.id">
                      <TableCell>{{ item.evidence_name }}</TableCell>
                      <TableCell>{{ item.original_filename }}</TableCell>
                      <TableCell><StatusBadge :status="item.upload_status" /></TableCell>
                      <TableCell>{{ item.uploaded_by }}</TableCell>
                      <TableCell class="tabular-nums">{{ formatDate(item.uploaded_at) }}</TableCell>
                      <TableCell class="text-right tabular-nums">{{ item.gene_count }}</TableCell>
                      <TableCell class="text-right tabular-nums">{{
                        item.genes_normalized
                      }}</TableCell>
                      <TableCell class="text-right tabular-nums">{{ item.genes_failed }}</TableCell>
                      <TableCell>
                        <div class="flex justify-end">
                          <Tooltip v-if="item.upload_status !== 'deleted'">
                            <TooltipTrigger as-child>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                class="text-danger hover:text-danger"
                                :aria-label="`Mark upload ${item.evidence_name} as deleted`"
                                @click="confirmSoftDelete(item)"
                              >
                                <Trash2 class="size-4" aria-hidden="true" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Mark upload as deleted</TooltipContent>
                          </Tooltip>
                        </div>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </DataState>
            </TabsContent>

            <!-- Audit trail -->
            <TabsContent value="audit" class="p-6">
              <div class="mb-4 flex justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  :disabled="auditLoading"
                  @click="loadAuditTrail"
                >
                  <RefreshCw class="size-4" aria-hidden="true" />
                  Refresh
                </Button>
              </div>
              <DataState
                :loading="auditLoading && !auditRecords.length"
                :error="auditError"
                error-title="Could not load the audit trail"
                :empty="!auditRecords.length"
                empty-message="No audit records yet."
                @retry="loadAuditTrail"
              >
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Action</TableHead>
                      <TableHead>Performed by</TableHead>
                      <TableHead>When</TableHead>
                      <TableHead>Details</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow v-for="item in auditRecords" :key="item.id">
                      <TableCell>
                        <Chip kind="neutral" :label="formatAction(item.action)" />
                      </TableCell>
                      <TableCell>{{ item.performed_by }}</TableCell>
                      <TableCell class="tabular-nums">{{
                        formatDate(item.performed_at)
                      }}</TableCell>
                      <TableCell>
                        <code
                          class="block max-w-[420px] truncate text-xs"
                          :title="JSON.stringify(item.details)"
                          >{{ JSON.stringify(item.details) }}</code
                        >
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </DataState>
            </TabsContent>

            <!-- Manage -->
            <TabsContent value="manage" class="p-6">
              <div class="mb-4 flex justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  :disabled="identifiersLoading"
                  @click="loadIdentifiers"
                >
                  <RefreshCw class="size-4" aria-hidden="true" />
                  Refresh
                </Button>
              </div>
              <DataState
                :loading="identifiersLoading && !identifiers.length"
                :error="identifiersError"
                :error-title="`Could not load ${identifierPlural}`"
                :empty="!identifiers.length"
                :empty-message="`No ${identifierPlural} yet.`"
                @retry="loadIdentifiers"
              >
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{{ identifierLabel }}</TableHead>
                      <TableHead class="text-right">Genes</TableHead>
                      <TableHead>Last updated</TableHead>
                      <TableHead><span class="sr-only">Actions</span></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow v-for="item in identifiers" :key="item.identifier">
                      <TableCell>{{ item.identifier }}</TableCell>
                      <TableCell class="text-right tabular-nums">{{ item.gene_count }}</TableCell>
                      <TableCell class="tabular-nums">{{
                        formatDate(item.last_updated)
                      }}</TableCell>
                      <TableCell>
                        <div class="flex justify-end">
                          <Tooltip>
                            <TooltipTrigger as-child>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                class="text-danger hover:text-danger"
                                :aria-label="`Delete ${item.identifier}`"
                                @click="confirmDelete(item)"
                              >
                                <Trash2 class="size-4" aria-hidden="true" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Delete all of its evidence</TooltipContent>
                          </Tooltip>
                        </div>
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </DataState>
            </TabsContent>
          </Tabs>
        </TabsContent>
      </Tabs>
    </Card>

    <!-- Replace upload deletes the provider's existing data first -->
    <ConfirmAction
      v-model:open="replaceDialog"
      :title="`Replace ${identifierLabel.toLowerCase()} data?`"
      confirm-label="Replace data"
      danger
      @confirm="uploadFile"
    >
      <p>
        All existing {{ sourceDisplayName(selectedSource) }} evidence for
        <strong class="text-foreground">{{
          providerName || `the ${identifierLabel.toLowerCase()} named after ${selectedFile?.name}`
        }}</strong>
        is deleted before <strong class="text-foreground">{{ selectedFile?.name }}</strong> is
        imported.
      </p>
      <p>This cannot be undone. Use Merge to add to the existing data instead.</p>
    </ConfirmAction>

    <ConfirmAction
      v-model:open="deleteDialog"
      :title="`Delete ${deleteTarget?.identifier}?`"
      confirm-label="Delete"
      danger
      @confirm="executeDelete"
    >
      <p>
        Removes <strong class="text-foreground">{{ deleteTarget?.gene_count }} genes</strong> of
        evidence from {{ sourceDisplayName(selectedSource) }}. This cannot be undone.
      </p>
    </ConfirmAction>

    <ConfirmAction
      v-model:open="softDeleteDialog"
      title="Mark upload as deleted?"
      confirm-label="Mark as deleted"
      @confirm="executeSoftDelete"
    >
      <p>
        Marks the upload record
        <strong class="text-foreground">{{ softDeleteTarget?.evidence_name }}</strong> as deleted.
        The evidence data itself is kept.
      </p>
    </ConfirmAction>
  </div>
</template>

<script setup>
/**
 * AdminHybridSources View
 * Upload, history, audit and management for the Diagnostic panels and Literature sources
 */

import { ref, computed, onMounted, watch } from 'vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import ConfirmAction from '@/components/admin/ConfirmAction.vue'
import { Chip, DataState, PAGE_CONTAINER, StatusBadge } from '@/components/shared'
import { sourceDisplayName } from '@/utils/sources'
import { formatDateTime } from '@/utils/formatDate'
import * as ingestionApi from '@/api/admin/ingestion'
import { toast } from 'vue-sonner'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import {
  BookOpen,
  BriefcaseMedical,
  CloudUpload,
  Cog,
  Database,
  FileText,
  History,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Upload,
  X
} from 'lucide-vue-next'

const SOURCES = [
  { key: 'DiagnosticPanels', icon: BriefcaseMedical },
  { key: 'Literature', icon: BookOpen }
]
const UPLOAD_MODES = [
  { value: 'merge', title: 'Merge', hint: 'Add to the existing data' },
  { value: 'replace', title: 'Replace', hint: 'Delete the existing data first' }
]

// State
const selectedSource = ref('DiagnosticPanels')
const activeTab = ref('upload')
const uploadMode = ref('merge')
const providerName = ref('')
const selectedFile = ref(null)
const isDragging = ref(false)
const uploading = ref(false)
const uploadResult = ref(null)
const statsLoading = ref(true)

const diagnosticStats = ref({ unique_genes: 0, evidence_records: 0 })
const literatureStats = ref({ unique_genes: 0, evidence_records: 0 })

// History tab
const uploads = ref([])
const uploadsLoading = ref(false)
const uploadsError = ref(null)

// Audit tab
const auditRecords = ref([])
const auditLoading = ref(false)
const auditError = ref(null)

// Manage tab
const identifiers = ref([])
const identifiersLoading = ref(false)
const identifiersError = ref(null)

// Dialogs
const replaceDialog = ref(false)
const deleteDialog = ref(false)
const deleteTarget = ref(null)
const softDeleteDialog = ref(false)
const softDeleteTarget = ref(null)
// The input sits inside a v-for, so the template ref is an array
const fileInput = ref([])
const openFilePicker = () => fileInput.value?.[0]?.click()

// Computed
const totalRecords = computed(
  () => diagnosticStats.value.evidence_records + literatureStats.value.evidence_records
)
const isPanels = computed(() => selectedSource.value === 'DiagnosticPanels')
const identifierLabel = computed(() => (isPanels.value ? 'Provider' : 'Publication ID'))
const identifierPlural = computed(() => (isPanels.value ? 'providers' : 'publications'))
const uploadLabel = computed(
  () =>
    `${uploadMode.value === 'replace' ? 'Replace with' : 'Upload'} ${sourceDisplayName(
      selectedSource.value
    ).toLowerCase()} file`
)

const formatAction = action => (action ? action.replaceAll('_', ' ') : 'unknown')

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
    toast.error('Failed to load statistics', { duration: Infinity })
  } finally {
    statsLoading.value = false
  }
}

const loadUploads = async () => {
  uploadsLoading.value = true
  uploadsError.value = null
  try {
    const response = await ingestionApi.listUploads(selectedSource.value)
    uploads.value = response.data?.data?.uploads || []
  } catch (error) {
    window.logService.error('Failed to load uploads:', error)
    uploadsError.value = error.message || 'Request failed'
  } finally {
    uploadsLoading.value = false
  }
}

const loadAuditTrail = async () => {
  auditLoading.value = true
  auditError.value = null
  try {
    const response = await ingestionApi.getAuditTrail(selectedSource.value)
    auditRecords.value = response.data?.data?.audit_records || []
  } catch (error) {
    window.logService.error('Failed to load audit trail:', error)
    auditError.value = error.message || 'Request failed'
  } finally {
    auditLoading.value = false
  }
}

const loadIdentifiers = async () => {
  identifiersLoading.value = true
  identifiersError.value = null
  try {
    const response = await ingestionApi.listIdentifiers(selectedSource.value)
    identifiers.value = response.data?.data?.identifiers || []
  } catch (error) {
    window.logService.error('Failed to load identifiers:', error)
    identifiersError.value = error.message || 'Request failed'
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
    toast.error('File too large. Maximum size is 50MB.', { duration: Infinity })
    return
  }

  // Validate file type
  const validExtensions = ['json', 'csv', 'tsv', 'xlsx', 'xls']
  const extension = file.name.split('.').pop().toLowerCase()
  if (!validExtensions.includes(extension)) {
    toast.error(`Invalid file type. Supported: ${validExtensions.join(', ')}`, {
      duration: Infinity
    })
    return
  }

  selectedFile.value = file
  uploadResult.value = null
}

// Replace deletes the provider's existing data, so it is confirmed first
const requestUpload = () => {
  if (uploadMode.value === 'replace') replaceDialog.value = true
  else uploadFile()
}

const uploadFile = async () => {
  if (!selectedFile.value) return

  uploading.value = true

  try {
    const response = await ingestionApi.uploadSourceFile(
      selectedSource.value,
      selectedFile.value,
      providerName.value || null,
      uploadMode.value
    )

    uploadResult.value = response.data?.data || response.data
    selectedFile.value = null
    providerName.value = ''

    // Reload statistics
    await loadStatistics()

    toast.success('Upload successful!', { duration: 5000 })
  } catch (error) {
    window.logService.error('Upload failed:', error)
    uploadResult.value = {
      status: 'failed',
      message: error.response?.data?.detail || 'Upload failed'
    }
    toast.error(`Upload failed: ${error.response?.data?.detail || error.message}`, {
      duration: Infinity
    })
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

  try {
    await ingestionApi.deleteByIdentifier(selectedSource.value, deleteTarget.value.identifier)
    toast.success('Successfully deleted', { duration: 5000 })
    deleteDialog.value = false
    await loadIdentifiers()
    await loadStatistics()
  } catch (error) {
    window.logService.error('Delete failed:', error)
    toast.error(`Delete failed: ${error.response?.data?.detail || error.message}`, {
      duration: Infinity
    })
  }
}

const confirmSoftDelete = item => {
  softDeleteTarget.value = item
  softDeleteDialog.value = true
}

const executeSoftDelete = async () => {
  if (!softDeleteTarget.value) return

  try {
    await ingestionApi.softDeleteUpload(selectedSource.value, softDeleteTarget.value.id)
    toast.success('Upload marked as deleted', { duration: 5000 })
    softDeleteDialog.value = false
    await loadUploads()
  } catch (error) {
    window.logService.error('Soft delete failed:', error)
    toast.error(`Soft delete failed: ${error.response?.data?.detail || error.message}`, {
      duration: Infinity
    })
  }
}

const formatFileSize = bytes => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

const formatDate = iso => formatDateTime(iso) || 'N/A'

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
