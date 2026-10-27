<template>
  <div :class="PAGE_CONTAINER">
    <AdminHeader
      title="Gene Staging"
      subtitle="Review genes that couldn't be automatically normalized to HGNC symbols"
    >
      <template #actions>
        <Button :disabled="loading" @click="loadData">
          <RefreshCw class="size-4 mr-2" :class="{ 'animate-spin': loading }" />
          Refresh
        </Button>
      </template>
    </AdminHeader>

    <!-- Process Explanation -->
    <Alert class="mb-6">
      <Info class="size-4" />
      <AlertDescription>
        <p>
          <strong class="font-medium text-foreground">How staging works:</strong> when a source
          provides a gene name that cannot be matched to an official HGNC symbol, it lands here.
          <strong class="font-medium text-foreground">Approve</strong> it with the correct HGNC
          symbol and ID, or <strong class="font-medium text-foreground">reject</strong> it if it is
          not a gene.
        </p>
      </AlertDescription>
    </Alert>

    <!-- Stats Overview -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      <AdminStatsCard
        title="Needs Your Review"
        :value="stagingStats.total_pending"
        :loading="statsLoading"
        :icon="UserSearch"
      />
      <AdminStatsCard
        title="Successfully Approved"
        :value="stagingStats.total_approved"
        :loading="statsLoading"
        :icon="CircleCheck"
      />
      <AdminStatsCard
        title="Rejected (Not Genes)"
        :value="stagingStats.total_rejected"
        :loading="statsLoading"
        :icon="CircleX"
      />
      <AdminStatsCard
        title="Auto-Normalization Rate"
        :value="`${(normalizationStats.success_rate * 100).toFixed(1)}%`"
        :loading="statsLoading"
        :icon="Bot"
      />
    </div>

    <!-- Pending reviews: up to API_LIMIT highest-priority items, filtered and paged here -->
    <Card>
      <CardHeader class="gap-4">
        <CardTitle>Pending reviews</CardTitle>
        <p
          v-if="!loading && !loadError"
          class="text-sm text-muted-foreground"
          data-testid="staging-scope"
        >
          {{ scopeText }}
        </p>
        <div class="grid grid-cols-1 gap-3 md:grid-cols-[1fr_12rem_auto] md:items-end">
          <div class="relative">
            <Search
              class="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              v-model="filters.search"
              class="pl-9"
              placeholder="Search gene text"
              aria-label="Search gene text"
            />
          </div>
          <Select v-model="filters.sourceFilter">
            <SelectTrigger aria-label="Data source">
              <SelectValue placeholder="All sources" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All sources</SelectItem>
              <SelectItem v-for="source in sourceOptions" :key="source.value" :value="source.value">
                {{ source.title }}
              </SelectItem>
            </SelectContent>
          </Select>
          <div class="flex h-9 items-center gap-2">
            <Switch id="expert-only" v-model="filters.expertReviewOnly" />
            <Label for="expert-only">Expert review only</Label>
          </div>
        </div>
      </CardHeader>
      <CardContent class="p-0">
        <DataState
          :loading="loading && !pendingReviews.length"
          :error="loadError"
          error-title="Could not load pending reviews"
          :empty="!filteredReviews.length"
          :empty-message="
            pendingReviews.length ? 'No pending items match these filters.' : 'Nothing to review.'
          "
          class="mx-4 mb-4"
          @retry="loadPendingReviews"
        >
          <template #loading>
            <div class="space-y-3 p-4" aria-hidden="true">
              <div
                v-for="i in 6"
                :key="i"
                class="h-8 rounded-md bg-muted motion-safe:animate-pulse"
              />
            </div>
          </template>
          <DataTable :table="table" />
          <DataTablePagination :table="table" :page-size-options="[25, 50, 100]" />
        </DataState>
      </CardContent>
    </Card>

    <!-- Approve Dialog -->
    <Dialog v-model:open="approveDialog">
      <DialogContent class="max-w-[700px]">
        <DialogHeader>
          <DialogTitle class="flex items-center">
            <CircleCheck class="size-5 text-success mr-2" aria-hidden="true" />
            Approve Gene: {{ selectedItem?.original_text }}
          </DialogTitle>
        </DialogHeader>
        <div class="space-y-4">
          <Alert>
            <AlertDescription>
              <p>
                <strong class="font-medium text-foreground"
                  >You are confirming this is a gene.</strong
                >
                Provide the official HGNC symbol and ID; the system creates a gene record or links
                to an existing one.
              </p>
            </AlertDescription>
          </Alert>

          <div>
            <strong>Original text from {{ sourceDisplayName(selectedItem?.source_name) }}:</strong>
            <code class="text-lg ml-2">{{ selectedItem?.original_text }}</code>
          </div>

          <div>
            <strong>Why it failed:</strong>
            <span class="text-sm text-muted-foreground ml-2">
              {{ selectedItem?.normalization_log?.failure_reason || 'Unknown error' }}
            </span>
          </div>

          <div class="space-y-2">
            <Label for="approve-symbol">Correct HGNC Gene Symbol *</Label>
            <Input
              id="approve-symbol"
              v-model="approveForm.approved_symbol"
              placeholder="e.g., PKD1, BRCA1, WT1"
            />
            <p class="text-xs text-muted-foreground">
              Enter the official HGNC gene symbol (usually all caps)
            </p>
          </div>

          <div class="space-y-2">
            <Label for="approve-hgnc">HGNC ID *</Label>
            <Input id="approve-hgnc" v-model="approveForm.hgnc_id" placeholder="e.g., HGNC:9008" />
            <p class="text-xs text-muted-foreground">
              Required: the pipeline uses this pair as-is. Look it up on
              <a
                href="https://www.genenames.org/tools/search/"
                target="_blank"
                rel="noopener"
                class="underline"
                >genenames.org</a
              >.
            </p>
          </div>

          <div class="space-y-2">
            <Label>Review Notes (optional)</Label>
            <textarea
              v-model="approveForm.notes"
              class="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              rows="2"
              placeholder="Any additional notes about this approval..."
            />
            <p class="text-xs text-muted-foreground">Optional notes for the audit trail</p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="approveDialog = false">
            <Ban class="size-4 mr-1" />
            Cancel
          </Button>
          <Button
            :disabled="
              actionLoading ||
              !approveForm.approved_symbol?.trim() ||
              !/^HGNC:\d+$/.test(approveForm.hgnc_id.trim())
            "
            @click="confirmApprove"
          >
            <CircleCheck class="size-4 mr-1" />
            {{ actionLoading ? 'Approving...' : 'Approve as Valid Gene' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Reject Dialog -->
    <AlertDialog v-model:open="rejectDialog">
      <AlertDialogContent class="max-w-[600px]">
        <AlertDialogHeader>
          <AlertDialogTitle class="flex items-center">
            <CircleX class="size-5 text-danger mr-2" aria-hidden="true" />
            Reject: {{ selectedItem?.original_text }}
          </AlertDialogTitle>
          <AlertDialogDescription>
            You're marking this as NOT a valid gene. This could be a typo, abbreviation, protein
            name, or other non-gene text.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div class="space-y-4">
          <div>
            <strong>Text from {{ sourceDisplayName(selectedItem?.source_name) }}:</strong>
            <code class="text-lg ml-2">{{ selectedItem?.original_text }}</code>
          </div>

          <div>
            <strong>Why it failed normalization:</strong>
            <span class="text-sm text-muted-foreground ml-2">
              {{ selectedItem?.normalization_log?.failure_reason || 'Unknown error' }}
            </span>
          </div>

          <div class="space-y-2">
            <Label>Why are you rejecting this? *</Label>
            <textarea
              v-model="rejectForm.notes"
              class="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              rows="3"
              placeholder="e.g., 'Not a gene - appears to be a protein complex name'"
            />
            <p class="text-xs text-muted-foreground">
              Please explain why this is not a valid gene symbol
            </p>
          </div>

          <div>
            <strong class="text-sm">Common reasons to reject:</strong>
            <ul class="text-xs text-muted-foreground mt-1 list-disc list-inside">
              <li>Protein or complex names (e.g., "MS6HM complex")</li>
              <li>Disease or condition names</li>
              <li>Typos or garbled text from data sources</li>
              <li>Non-standard abbreviations</li>
              <li>Chemical compound names</li>
            </ul>
          </div>
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            :class="buttonVariants({ variant: 'destructive' })"
            :disabled="actionLoading || !rejectForm.notes?.trim()"
            @click="confirmReject"
          >
            <CircleX class="size-4 mr-1" />
            {{ actionLoading ? 'Rejecting...' : 'Reject as Invalid' }}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <!-- Details Dialog -->
    <Dialog v-model:open="detailsDialog">
      <DialogContent class="max-w-[800px]">
        <DialogHeader>
          <DialogTitle>Gene Staging Details</DialogTitle>
        </DialogHeader>
        <div v-if="selectedItem" class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="space-y-3">
              <div>
                <strong>Original Text:</strong><br />
                <code class="text-sm">{{ selectedItem.original_text }}</code>
              </div>
              <div><strong>Source:</strong> {{ sourceDisplayName(selectedItem.source_name) }}</div>
              <div>
                <strong>Review priority:</strong>
                <span class="tabular-nums">{{ selectedItem.priority_score ?? '—' }}</span>
              </div>
              <div>
                <strong>Expert Review Required:</strong>
                {{ selectedItem.requires_expert_review ? 'Yes' : 'No' }}
              </div>
            </div>
            <div class="space-y-3">
              <div><strong>Created:</strong> {{ formatDate(selectedItem.created_at) }}</div>
              <div><strong>Updated:</strong> {{ formatDate(selectedItem.updated_at) }}</div>
              <div>
                <strong>Status:</strong>
                <StatusBadge :status="selectedItem.status" class="ml-1" />
              </div>
            </div>
          </div>

          <Separator />

          <div>
            <strong>Original Data:</strong>
            <div class="mt-2 rounded-md border p-3">
              <pre class="text-xs overflow-x-auto">{{
                JSON.stringify(selectedItem?.original_data, null, 2)
              }}</pre>
            </div>
          </div>

          <div>
            <strong>Normalization Log:</strong>
            <div class="mt-2 rounded-md border p-3">
              <pre class="text-xs overflow-x-auto">{{
                JSON.stringify(selectedItem?.normalization_log, null, 2)
              }}</pre>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="detailsDialog = false">Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup>
import { h, ref, reactive, onMounted, computed, watch } from 'vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'

import { useTable } from '@tanstack/vue-table'
import { Chip, DataState, PAGE_CONTAINER, StatusBadge } from '@/components/shared'
import { DataTable, DataTablePagination, dataTableFeatures } from '@/components/ui/data-table'
import { sourceDisplayName } from '@/utils/sources'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as stagingApi from '@/api/admin/staging'
import { toast } from 'vue-sonner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button, buttonVariants } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
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
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import {
  Ban,
  Bot,
  BriefcaseBusiness,
  CircleCheck,
  CircleX,
  ExternalLink,
  Info,
  RefreshCw,
  Search,
  UserSearch
} from 'lucide-vue-next'

// Reactive data
const loading = ref(false)
const loadError = ref(null)
// The API returns at most 200 items, highest priority first, and has no offset (backend gap)
const API_LIMIT = 200
const statsLoading = ref(false)
const actionLoading = ref(false)

// Stats data
const stagingStats = reactive({
  total_pending: 0,
  total_approved: 0,
  total_rejected: 0,
  by_source: {}
})

const normalizationStats = reactive({
  total_attempts: 0,
  successful_attempts: 0,
  success_rate: 0,
  by_source: {}
})

// Test normalization

// Filters
const filters = reactive({
  sourceFilter: 'all',
  search: '',
  expertReviewOnly: false
})

// Data
const pendingReviews = ref([])

// Dialogs
const approveDialog = ref(false)
const rejectDialog = ref(false)
const detailsDialog = ref(false)
const selectedItem = ref(null)

// Forms
const approveForm = reactive({
  approved_symbol: '',
  hgnc_id: '',
  notes: ''
})

const rejectForm = reactive({
  notes: ''
})

// Computed
const sourceOptions = computed(() => {
  const sources = [...new Set(pendingReviews.value.map(item => item.source_name))].sort()
  return sources.map(source => ({ title: sourceDisplayName(source), value: source }))
})

const filteredReviews = computed(() => {
  const q = filters.search.trim().toLowerCase()
  return pendingReviews.value.filter(
    item =>
      (filters.sourceFilter === 'all' || item.source_name === filters.sourceFilter) &&
      (!filters.expertReviewOnly || item.requires_expert_review) &&
      (!q || item.original_text?.toLowerCase().includes(q))
  )
})

const scopeText = computed(() => {
  const loaded = pendingReviews.value.length
  const total = stagingStats.total_pending
  const shown = filteredReviews.value.length
  const base =
    total > loaded
      ? `The ${loaded.toLocaleString()} highest-priority of ${total.toLocaleString()} pending items are loaded; reviewing them brings the next ones in.`
      : `${loaded.toLocaleString()} pending items.`
  return shown === loaded ? base : `${shown.toLocaleString()} match the filters. ${base}`
})

const hgncSearchUrl = text =>
  `https://www.genenames.org/tools/search/#!/?query=${encodeURIComponent(text)}`

const iconAction = (label, icon, onClick) =>
  h(Tooltip, null, {
    default: () => [
      h(TooltipTrigger, { asChild: true }, () =>
        h(Button, { variant: 'ghost', size: 'icon-sm', 'aria-label': label, onClick }, () =>
          h(icon, { class: 'size-4', 'aria-hidden': 'true' })
        )
      ),
      h(TooltipContent, null, () => label)
    ]
  })

const columns = [
  {
    accessorKey: 'original_text',
    header: 'Gene text',
    cell: ({ row }) => {
      const text = row.original.original_text
      return h('div', { class: 'flex items-center gap-1' }, [
        h('code', { class: 'font-mono text-sm' }, text),
        h(Tooltip, null, {
          default: () => [
            h(TooltipTrigger, { asChild: true }, () =>
              h(
                'a',
                {
                  href: hgncSearchUrl(text),
                  target: '_blank',
                  rel: 'noopener',
                  'aria-label': `Search HGNC for ${text}`,
                  class:
                    'inline-flex size-6 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none'
                },
                h(ExternalLink, { class: 'size-3.5', 'aria-hidden': 'true' })
              )
            ),
            h(TooltipContent, null, () => `Search HGNC for ${text}`)
          ]
        })
      ])
    }
  },
  {
    accessorKey: 'source_name',
    header: 'Source',
    cell: ({ row }) => h('span', { class: 'text-sm' }, sourceDisplayName(row.original.source_name))
  },
  {
    accessorKey: 'priority_score',
    header: () => h('div', { class: 'text-right' }, 'Priority'),
    cell: ({ row }) =>
      h(Tooltip, null, {
        default: () => [
          h(TooltipTrigger, { asChild: true }, () =>
            h(
              'div',
              { class: 'text-right tabular-nums', tabindex: 0 },
              row.original.priority_score ?? '—'
            )
          ),
          h(TooltipContent, null, () => 'Review priority: higher scores are listed first')
        ]
      }),
    size: 90
  },
  {
    accessorKey: 'requires_expert_review',
    header: 'Expert review',
    cell: ({ row }) =>
      row.original.requires_expert_review
        ? h(Chip, {
            kind: 'neutral',
            label: 'Needed',
            icon: BriefcaseBusiness,
            tooltip: 'Ambiguous text: needs a domain expert before approval'
          })
        : h('span', { class: 'text-sm text-muted-foreground' }, 'No'),
    size: 120
  },
  {
    accessorKey: 'created_at',
    header: 'Submitted',
    cell: ({ row }) =>
      h(
        'span',
        { class: 'text-sm tabular-nums whitespace-nowrap' },
        formatDate(row.original.created_at)
      )
  },
  {
    id: 'actions',
    header: () => h('span', { class: 'sr-only' }, 'Actions'),
    cell: ({ row }) => {
      const item = row.original
      return h('div', { class: 'flex items-center justify-end gap-1.5' }, [
        h(
          Button,
          {
            variant: 'outline',
            size: 'sm',
            'aria-label': `Approve ${item.original_text}`,
            onClick: () => approveItem(item)
          },
          () => [h(CircleCheck, { class: 'text-success', 'aria-hidden': 'true' }), 'Approve']
        ),
        h(
          Button,
          {
            variant: 'outline',
            size: 'sm',
            'aria-label': `Reject ${item.original_text}`,
            onClick: () => rejectItem(item)
          },
          () => [h(CircleX, { class: 'text-danger', 'aria-hidden': 'true' }), 'Reject']
        ),
        iconAction(`Details for ${item.original_text}`, Info, () => showItemDetails(item))
      ])
    },
    enableSorting: false,
    size: 260
  }
]

const table = useTable({
  features: dataTableFeatures,
  get data() {
    return filteredReviews.value
  },
  columns,
  initialState: { pagination: { pageIndex: 0, pageSize: 25 } }
})

// Methods

const loadStats = async () => {
  statsLoading.value = true
  try {
    const [stagingResponse, normalizationResponse] = await Promise.all([
      stagingApi.getStagingStats(),
      stagingApi.getNormalizationStats()
    ])

    Object.assign(stagingStats, stagingResponse.data)
    Object.assign(normalizationStats, normalizationResponse.data)
  } catch (error) {
    window.logService.error('Failed to load stats:', error)
    toast.error('Failed to load statistics', { duration: Infinity })
  } finally {
    statsLoading.value = false
  }
}

const loadPendingReviews = async () => {
  loading.value = true
  loadError.value = null
  try {
    const response = await stagingApi.getPendingStaging({ limit: API_LIMIT })
    pendingReviews.value = response.data
  } catch (error) {
    window.logService.error('Failed to load pending reviews:', error)
    loadError.value = error.message || 'Request failed'
  } finally {
    loading.value = false
  }
}

const loadData = async () => {
  await Promise.all([loadStats(), loadPendingReviews()])
}

const approveItem = item => {
  selectedItem.value = item
  approveForm.approved_symbol = item.original_text // Pre-fill with original text
  approveForm.hgnc_id = ''
  approveForm.notes = ''
  approveDialog.value = true
}

const rejectItem = item => {
  selectedItem.value = item
  rejectForm.notes = ''
  rejectDialog.value = true
}

const showItemDetails = item => {
  selectedItem.value = item
  detailsDialog.value = true
}

const confirmApprove = async () => {
  if (!selectedItem.value || !approveForm.approved_symbol || !approveForm.hgnc_id) return

  actionLoading.value = true
  try {
    await stagingApi.approveStaging(selectedItem.value.id, {
      approved_symbol: approveForm.approved_symbol.trim(),
      hgnc_id: approveForm.hgnc_id.trim(),
      notes: approveForm.notes || null
    })

    toast.success('Gene staging approved successfully', { duration: 5000 })
    approveDialog.value = false
    await loadData()
  } catch (error) {
    window.logService.error('Failed to approve staging:', error)
    // Say why: a symbol/HGNC mismatch or an already decided record (#375)
    const apiError = error?.response?.data?.error
    const detail = apiError?.detail ?? apiError?.message
    toast.error(detail ? `Not approved: ${detail}` : 'Failed to approve gene staging', {
      duration: Infinity
    })
  } finally {
    actionLoading.value = false
  }
}

const confirmReject = async () => {
  if (!selectedItem.value || !rejectForm.notes) return

  actionLoading.value = true
  try {
    await stagingApi.rejectStaging(selectedItem.value.id, {
      notes: rejectForm.notes
    })

    toast.success('Gene staging rejected', { duration: 5000 })
    rejectDialog.value = false
    await loadData()
  } catch (error) {
    window.logService.error('Failed to reject staging:', error)
    toast.error('Failed to reject gene staging', { duration: Infinity })
  } finally {
    actionLoading.value = false
  }
}

// Utility methods
const formatDate = dateString => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString()
}

// A filter change starts again at the first page
watch(
  () => [filters.sourceFilter, filters.search, filters.expertReviewOnly],
  () => table.setPageIndex(0)
)

// Load data on mount
onMounted(() => {
  loadData()
})
</script>
