<template>
  <div class="container mx-auto px-4 py-6">
    <AdminHeader
      title="Hybrid Source Management"
      subtitle="Upload and manage DiagnosticPanels and Literature evidence"
      :icon="DatabaseZap"
      icon-color="cyan"
      :breadcrumbs="ADMIN_BREADCRUMBS.hybridSources"
    />

    <!-- Source Statistics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <AdminStatsCard
        title="DiagnosticPanels Genes"
        :value="diagnosticStats.unique_genes"
        :loading="statsLoading"
        icon="mdi-medical-bag"
        color="cyan"
      />
      <AdminStatsCard
        title="Literature Genes"
        :value="literatureStats.unique_genes"
        :loading="statsLoading"
        icon="mdi-book-open-page-variant"
        color="purple"
      />
      <AdminStatsCard
        title="Total Evidence Records"
        :value="totalRecords"
        :loading="statsLoading"
        icon="mdi-database"
        color="primary"
      />
    </div>

    <!-- Main Tabbed Interface -->
    <Card>
      <!-- Source Selector Tabs -->
      <Tabs v-model="selectedSource" class="w-full">
        <div class="border-b px-4 pt-4">
          <TabsList>
            <TabsTrigger value="DiagnosticPanels">
              <BriefcaseMedical class="size-4 mr-1" />
              Diagnostic Panels
            </TabsTrigger>
            <TabsTrigger value="Literature">
              <BookOpen class="size-4 mr-1" />
              Literature
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="DiagnosticPanels" class="m-0 p-0">
          <SourceContent />
        </TabsContent>
        <TabsContent value="Literature" class="m-0 p-0">
          <SourceContent />
        </TabsContent>
      </Tabs>
    </Card>

    <!-- Delete Confirmation Dialog -->
    <AlertDialog v-model:open="deleteDialog">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle class="flex items-center text-destructive">
            <AlertTriangle class="size-5 mr-1" />
            Confirm Deletion
          </AlertDialogTitle>
          <AlertDialogDescription>
            <p>
              Are you sure you want to delete
              <strong>{{ deleteTarget?.identifier }}</strong
              >?
            </p>
            <p class="text-yellow-600 dark:text-yellow-400 mt-2">
              This will remove <strong>{{ deleteTarget?.gene_count }} genes</strong> from
              {{ selectedSource }}.
            </p>
            <p class="text-destructive font-bold mt-2">This action cannot be undone!</p>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            :disabled="deleting"
            @click="executeDelete"
          >
            {{ deleting ? 'Deleting...' : 'Delete' }}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <!-- Soft Delete Confirmation Dialog -->
    <AlertDialog v-model:open="softDeleteDialog">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle class="flex items-center text-yellow-600">
            <AlertTriangle class="size-5 mr-1" />
            Soft Delete Upload
          </AlertDialogTitle>
          <AlertDialogDescription>
            <p>
              Mark upload <strong>{{ softDeleteTarget?.evidence_name }}</strong> as deleted?
            </p>
            <p class="text-muted-foreground mt-2">
              This will not delete the actual data, only mark the upload record as deleted.
            </p>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            class="bg-yellow-600 text-white hover:bg-yellow-700"
            :disabled="deleting"
            @click="executeSoftDelete"
          >
            {{ deleting ? 'Processing...' : 'Mark as Deleted' }}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </div>
</template>

<script setup>
/**
 * AdminHybridSources View
 * Complete CRUD interface for DiagnosticPanels and Literature sources
 */

import { ref, computed, onMounted, watch, defineComponent, h } from 'vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as ingestionApi from '@/api/admin/ingestion'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'
import { toast } from 'vue-sonner'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
  AlertTriangle,
  BookOpen,
  BriefcaseMedical,
  CloudUpload,
  Cog,
  DatabaseZap,
  FileText,
  Hash,
  History,
  Merge,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  Upload,
  X
} from 'lucide-vue-next'

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

// File input ref
const fileInput = ref(null)

// Table headers
const uploadHeaders = [
  { title: 'Name', key: 'evidence_name' },
  { title: 'File', key: 'original_filename' },
  { title: 'Status', key: 'upload_status' },
  { title: 'Uploaded By', key: 'uploaded_by' },
  { title: 'Uploaded', key: 'uploaded_at' },
  { title: 'Genes', key: 'gene_count' },
  { title: 'Normalized', key: 'genes_normalized' },
  { title: 'Failed', key: 'genes_failed' },
  { title: 'Actions', key: 'actions' }
]

const auditHeaders = [
  { title: 'Action', key: 'action' },
  { title: 'Performed By', key: 'performed_by' },
  { title: 'When', key: 'performed_at' },
  { title: 'Details', key: 'details' }
]

const identifierHeaders = computed(() => [
  {
    title: selectedSource.value === 'DiagnosticPanels' ? 'Provider' : 'Publication ID',
    key: 'identifier'
  },
  { title: 'Genes', key: 'gene_count' },
  { title: 'Last Updated', key: 'last_updated' },
  { title: 'Actions', key: 'actions' }
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
    toast.error('Failed to load statistics', { duration: Infinity })
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
    toast.error('Failed to load upload history', { duration: Infinity })
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
    toast.error('Failed to load audit trail', { duration: Infinity })
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
    toast.error('Failed to load identifiers', { duration: Infinity })
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

  deleting.value = true
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
    toast.success('Upload marked as deleted', { duration: 5000 })
    softDeleteDialog.value = false
    await loadUploads()
  } catch (error) {
    window.logService.error('Soft delete failed:', error)
    toast.error(`Soft delete failed: ${error.response?.data?.detail || error.message}`, {
      duration: Infinity
    })
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
    completed: 'default',
    processing: 'secondary',
    failed: 'destructive',
    deleted: 'outline'
  }
  return colors[status] || 'outline'
}

const getActionColor = action => {
  const colors = {
    upload: 'default',
    delete: 'destructive',
    soft_delete_upload: 'outline',
    merge: 'secondary',
    replace: 'outline'
  }
  return colors[action] || 'outline'
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

// SourceContent inline component - renders inside each source tab
const SourceContent = defineComponent({
  name: 'SourceContent',
  setup() {
    return () =>
      h('div', [
        // Inner view tabs
        h(
          Tabs,
          {
            modelValue: activeTab.value,
            'onUpdate:modelValue': v => {
              activeTab.value = v
            }
          },
          {
            default: () => [
              h('div', { class: 'border-b px-4' }, [
                h(
                  TabsList,
                  { class: 'bg-transparent' },
                  {
                    default: () => [
                      h(
                        TabsTrigger,
                        { value: 'upload' },
                        { default: () => [h(Upload, { class: 'size-4 mr-1' }), 'Upload'] }
                      ),
                      h(
                        TabsTrigger,
                        { value: 'history' },
                        { default: () => [h(History, { class: 'size-4 mr-1' }), 'History'] }
                      ),
                      h(
                        TabsTrigger,
                        { value: 'audit' },
                        { default: () => [h(ShieldCheck, { class: 'size-4 mr-1' }), 'Audit Trail'] }
                      ),
                      h(
                        TabsTrigger,
                        { value: 'manage' },
                        { default: () => [h(Cog, { class: 'size-4 mr-1' }), 'Manage'] }
                      )
                    ]
                  }
                )
              ]),

              // Upload tab
              h(
                TabsContent,
                { value: 'upload', class: 'p-6' },
                {
                  default: () => [
                    // Upload mode selection
                    h('div', { class: 'mb-4' }, [
                      h('span', { class: 'text-sm font-semibold block mb-2' }, 'Upload Mode:'),
                      h(
                        RadioGroup,
                        {
                          modelValue: uploadMode.value,
                          'onUpdate:modelValue': v => {
                            uploadMode.value = v
                          },
                          class: 'flex gap-4'
                        },
                        {
                          default: () => [
                            h('div', { class: 'flex items-center space-x-2' }, [
                              h(RadioGroupItem, { value: 'merge', id: 'merge' }),
                              h(
                                Label,
                                { for: 'merge' },
                                { default: () => 'Merge (add to existing data)' }
                              )
                            ]),
                            h('div', { class: 'flex items-center space-x-2' }, [
                              h(RadioGroupItem, { value: 'replace', id: 'replace' }),
                              h(
                                Label,
                                { for: 'replace' },
                                { default: () => 'Replace (overwrite existing data)' }
                              )
                            ])
                          ]
                        }
                      )
                    ]),

                    // Replace warning
                    uploadMode.value === 'replace'
                      ? h(
                          Alert,
                          { variant: 'destructive', class: 'mb-4' },
                          {
                            default: () => [
                              h(AlertDescription, null, {
                                default: () =>
                                  h('span', null, [
                                    h('strong', null, 'Warning:'),
                                    ' Replace mode will delete all existing data for this provider/publication before uploading new data.'
                                  ])
                              })
                            ]
                          }
                        )
                      : null,

                    // Provider name
                    h('div', { class: 'space-y-2 mb-4' }, [
                      h(Label, null, {
                        default: () =>
                          selectedSource.value === 'DiagnosticPanels'
                            ? 'Provider Name (optional)'
                            : 'Publication ID (optional)'
                      }),
                      h(Input, {
                        modelValue: providerName.value,
                        'onUpdate:modelValue': v => {
                          providerName.value = v
                        },
                        placeholder:
                          selectedSource.value === 'DiagnosticPanels'
                            ? 'Leave empty to use filename as provider'
                            : 'Leave empty to use filename as publication ID'
                      })
                    ]),

                    // Drag & Drop Zone
                    h(
                      'div',
                      {
                        class: [
                          'border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer',
                          isDragging.value
                            ? 'border-primary bg-primary/5'
                            : 'border-border hover:border-primary/50'
                        ],
                        onDragover: e => {
                          e.preventDefault()
                          isDragging.value = true
                        },
                        onDragleave: e => {
                          e.preventDefault()
                          isDragging.value = false
                        },
                        onDrop: e => {
                          e.preventDefault()
                          handleFileDrop(e)
                        }
                      },
                      [
                        h(CloudUpload, {
                          class: [
                            'size-16 mx-auto mb-4',
                            isDragging.value ? 'text-primary' : 'text-muted-foreground'
                          ]
                        }),
                        h(
                          'h3',
                          { class: 'text-lg font-medium mt-4' },
                          isDragging.value ? 'Drop file here' : 'Drag & drop file here'
                        ),
                        h('p', { class: 'text-sm text-muted-foreground mt-2' }, 'or'),
                        h(
                          Button,
                          {
                            variant: 'outline',
                            class: 'mt-2',
                            onClick: () => fileInput.value?.click()
                          },
                          { default: () => 'Browse Files' }
                        ),
                        h('input', {
                          ref: el => {
                            fileInput.value = el
                          },
                          type: 'file',
                          class: 'hidden',
                          accept: '.json,.csv,.tsv,.xlsx,.xls',
                          onChange: handleFileSelect
                        }),
                        h(
                          'p',
                          { class: 'text-xs text-muted-foreground mt-4' },
                          'Supported: JSON, CSV, TSV, Excel (max 50MB)'
                        )
                      ]
                    ),

                    // Selected file info
                    selectedFile.value
                      ? h(
                          Alert,
                          { class: 'mt-4' },
                          {
                            default: () => [
                              h(AlertDescription, null, {
                                default: () =>
                                  h('div', { class: 'flex items-center' }, [
                                    h(FileText, { class: 'size-4 mr-1' }),
                                    h(
                                      'span',
                                      null,
                                      `${selectedFile.value.name} (${formatFileSize(selectedFile.value.size)})`
                                    ),
                                    h('div', { class: 'flex-1' }),
                                    h(
                                      Button,
                                      {
                                        variant: 'ghost',
                                        size: 'icon',
                                        class: 'h-6 w-6',
                                        onClick: () => {
                                          selectedFile.value = null
                                        }
                                      },
                                      { default: () => h(X, { class: 'size-4' }) }
                                    )
                                  ])
                              })
                            ]
                          }
                        )
                      : null,

                    // Upload button
                    h(
                      Button,
                      {
                        disabled: !selectedFile.value || uploading.value,
                        variant: uploadMode.value === 'replace' ? 'destructive' : 'default',
                        class: 'w-full mt-4',
                        size: 'lg',
                        onClick: uploadFile
                      },
                      {
                        default: () => [
                          h(Upload, { class: 'size-4 mr-2' }),
                          uploading.value
                            ? 'Uploading...'
                            : `${uploadMode.value === 'replace' ? 'Replace' : 'Upload'} ${selectedSource.value} File`
                        ]
                      }
                    ),

                    // Upload progress
                    uploading.value
                      ? h('div', { class: 'mt-4 space-y-1' }, [
                          h(Progress, { modelValue: uploadProgress.value }),
                          h(
                            'p',
                            { class: 'text-xs text-center text-muted-foreground' },
                            `${uploadProgress.value}%`
                          )
                        ])
                      : null,

                    // Upload results
                    uploadResult.value
                      ? h(
                          Alert,
                          {
                            variant:
                              uploadResult.value.status === 'success' ? 'default' : 'destructive',
                            class: 'mt-4'
                          },
                          {
                            default: () => [
                              h(AlertDescription, null, {
                                default: () => [
                                  h('div', { class: 'font-semibold mb-2' }, 'Upload Results'),
                                  h('div', { class: 'space-y-1 text-sm' }, [
                                    h('div', { class: 'flex items-center gap-2' }, [
                                      h(Hash, { class: 'size-4' }),
                                      h(
                                        'span',
                                        null,
                                        `Genes Processed: ${uploadResult.value.genes_processed || 0}`
                                      )
                                    ]),
                                    h('div', { class: 'flex items-center gap-2' }, [
                                      h(Plus, { class: 'size-4' }),
                                      h(
                                        'span',
                                        null,
                                        `Created: ${uploadResult.value.storage_stats?.created || 0}`
                                      )
                                    ]),
                                    h('div', { class: 'flex items-center gap-2' }, [
                                      h(Merge, { class: 'size-4' }),
                                      h(
                                        'span',
                                        null,
                                        `Merged: ${uploadResult.value.storage_stats?.merged || 0}`
                                      )
                                    ])
                                  ]),
                                  uploadResult.value.message
                                    ? h('p', { class: 'mt-2' }, uploadResult.value.message)
                                    : null
                                ]
                              })
                            ]
                          }
                        )
                      : null
                  ]
                }
              ),

              // History tab
              h(
                TabsContent,
                { value: 'history', class: 'p-6' },
                {
                  default: () => [
                    h('div', { class: 'flex justify-end mb-4' }, [
                      h(
                        Button,
                        { variant: 'outline', onClick: loadUploads },
                        {
                          default: () => [h(RefreshCw, { class: 'size-4 mr-2' }), 'Refresh']
                        }
                      )
                    ]),
                    h(Table, null, {
                      default: () => [
                        h(TableHeader, null, {
                          default: () =>
                            h(TableRow, null, {
                              default: () =>
                                uploadHeaders.map(hdr =>
                                  h(TableHead, { key: hdr.key }, { default: () => hdr.title })
                                )
                            })
                        }),
                        h(TableBody, null, {
                          default: () =>
                            uploadsLoading.value
                              ? h(TableRow, null, {
                                  default: () =>
                                    h(
                                      TableCell,
                                      {
                                        colspan: 9,
                                        class: 'text-center py-8 text-muted-foreground'
                                      },
                                      {
                                        default: () => 'Loading...'
                                      }
                                    )
                                })
                              : uploads.value.length === 0
                                ? h(TableRow, null, {
                                    default: () =>
                                      h(
                                        TableCell,
                                        {
                                          colspan: 9,
                                          class: 'text-center py-8 text-muted-foreground'
                                        },
                                        {
                                          default: () => 'No upload history found'
                                        }
                                      )
                                  })
                                : uploads.value.map(item =>
                                    h(
                                      TableRow,
                                      { key: item.id },
                                      {
                                        default: () => [
                                          h(TableCell, null, { default: () => item.evidence_name }),
                                          h(TableCell, null, {
                                            default: () => item.original_filename
                                          }),
                                          h(TableCell, null, {
                                            default: () =>
                                              h(
                                                Badge,
                                                { variant: getStatusColor(item.upload_status) },
                                                {
                                                  default: () => item.upload_status
                                                }
                                              )
                                          }),
                                          h(TableCell, null, { default: () => item.uploaded_by }),
                                          h(TableCell, null, {
                                            default: () => formatDate(item.uploaded_at)
                                          }),
                                          h(TableCell, null, { default: () => item.gene_count }),
                                          h(TableCell, null, {
                                            default: () => item.genes_normalized
                                          }),
                                          h(TableCell, null, { default: () => item.genes_failed }),
                                          h(TableCell, null, {
                                            default: () =>
                                              item.upload_status !== 'deleted'
                                                ? h(
                                                    Button,
                                                    {
                                                      variant: 'ghost',
                                                      size: 'icon',
                                                      class: 'h-8 w-8 text-destructive',
                                                      onClick: () => confirmSoftDelete(item)
                                                    },
                                                    {
                                                      default: () => h(Trash2, { class: 'size-4' })
                                                    }
                                                  )
                                                : null
                                          })
                                        ]
                                      }
                                    )
                                  )
                        })
                      ]
                    })
                  ]
                }
              ),

              // Audit tab
              h(
                TabsContent,
                { value: 'audit', class: 'p-6' },
                {
                  default: () => [
                    h('div', { class: 'flex justify-end mb-4' }, [
                      h(
                        Button,
                        { variant: 'outline', onClick: loadAuditTrail },
                        {
                          default: () => [h(RefreshCw, { class: 'size-4 mr-2' }), 'Refresh']
                        }
                      )
                    ]),
                    h(Table, null, {
                      default: () => [
                        h(TableHeader, null, {
                          default: () =>
                            h(TableRow, null, {
                              default: () =>
                                auditHeaders.map(hdr =>
                                  h(TableHead, { key: hdr.key }, { default: () => hdr.title })
                                )
                            })
                        }),
                        h(TableBody, null, {
                          default: () =>
                            auditLoading.value
                              ? h(TableRow, null, {
                                  default: () =>
                                    h(
                                      TableCell,
                                      {
                                        colspan: 4,
                                        class: 'text-center py-8 text-muted-foreground'
                                      },
                                      {
                                        default: () => 'Loading...'
                                      }
                                    )
                                })
                              : auditRecords.value.length === 0
                                ? h(TableRow, null, {
                                    default: () =>
                                      h(
                                        TableCell,
                                        {
                                          colspan: 4,
                                          class: 'text-center py-8 text-muted-foreground'
                                        },
                                        {
                                          default: () => 'No audit records found'
                                        }
                                      )
                                  })
                                : auditRecords.value.map(item =>
                                    h(
                                      TableRow,
                                      { key: item.id },
                                      {
                                        default: () => [
                                          h(TableCell, null, {
                                            default: () =>
                                              h(
                                                Badge,
                                                { variant: getActionColor(item.action) },
                                                {
                                                  default: () => item.action
                                                }
                                              )
                                          }),
                                          h(TableCell, null, { default: () => item.performed_by }),
                                          h(TableCell, null, {
                                            default: () => formatDate(item.performed_at)
                                          }),
                                          h(TableCell, null, {
                                            default: () =>
                                              h(
                                                'span',
                                                { class: 'text-xs' },
                                                JSON.stringify(item.details)
                                              )
                                          })
                                        ]
                                      }
                                    )
                                  )
                        })
                      ]
                    })
                  ]
                }
              ),

              // Manage tab
              h(
                TabsContent,
                { value: 'manage', class: 'p-6' },
                {
                  default: () => [
                    h('div', { class: 'flex justify-end mb-4' }, [
                      h(
                        Button,
                        { variant: 'outline', onClick: loadIdentifiers },
                        {
                          default: () => [h(RefreshCw, { class: 'size-4 mr-2' }), 'Refresh']
                        }
                      )
                    ]),
                    h(Table, null, {
                      default: () => [
                        h(TableHeader, null, {
                          default: () =>
                            h(TableRow, null, {
                              default: () =>
                                identifierHeaders.value.map(hdr =>
                                  h(TableHead, { key: hdr.key }, { default: () => hdr.title })
                                )
                            })
                        }),
                        h(TableBody, null, {
                          default: () =>
                            identifiersLoading.value
                              ? h(TableRow, null, {
                                  default: () =>
                                    h(
                                      TableCell,
                                      {
                                        colspan: 4,
                                        class: 'text-center py-8 text-muted-foreground'
                                      },
                                      {
                                        default: () => 'Loading...'
                                      }
                                    )
                                })
                              : identifiers.value.length === 0
                                ? h(TableRow, null, {
                                    default: () =>
                                      h(
                                        TableCell,
                                        {
                                          colspan: 4,
                                          class: 'text-center py-8 text-muted-foreground'
                                        },
                                        {
                                          default: () =>
                                            `No ${selectedSource.value === 'DiagnosticPanels' ? 'providers' : 'publications'} found`
                                        }
                                      )
                                  })
                                : identifiers.value.map(item =>
                                    h(
                                      TableRow,
                                      { key: item.identifier },
                                      {
                                        default: () => [
                                          h(TableCell, null, { default: () => item.identifier }),
                                          h(TableCell, null, { default: () => item.gene_count }),
                                          h(TableCell, null, {
                                            default: () => formatDate(item.last_updated)
                                          }),
                                          h(TableCell, null, {
                                            default: () =>
                                              h(
                                                Button,
                                                {
                                                  variant: 'ghost',
                                                  size: 'icon',
                                                  class: 'h-8 w-8 text-destructive',
                                                  onClick: () => confirmDelete(item)
                                                },
                                                { default: () => h(Trash2, { class: 'size-4' }) }
                                              )
                                          })
                                        ]
                                      }
                                    )
                                  )
                        })
                      ]
                    })
                  ]
                }
              )
            ]
          }
        )
      ])
  }
})
</script>
