<template>
  <div class="container mx-auto px-4 py-6">
    <AdminHeader
      title="Gene Staging"
      subtitle="Review genes that couldn't be automatically normalized to HGNC symbols"
      :icon="Dna"
      icon-color="red"
      :breadcrumbs="ADMIN_BREADCRUMBS.staging"
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
        <strong>Gene Staging Process:</strong> When data sources provide gene names that can't be
        automatically matched to official HGNC symbols, they're sent here for manual review. Your
        job is to either <strong>approve</strong> them with the correct HGNC symbol, or
        <strong>reject</strong> them if they're not real genes.
      </AlertDescription>
    </Alert>

    <!-- Stats Overview -->
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <AdminStatsCard
        title="Needs Your Review"
        :value="stagingStats.total_pending"
        :loading="statsLoading"
        icon="mdi-account-search"
        color="warning"
      />
      <AdminStatsCard
        title="Successfully Approved"
        :value="stagingStats.total_approved"
        :loading="statsLoading"
        icon="mdi-check-circle"
        color="success"
      />
      <AdminStatsCard
        title="Rejected (Not Genes)"
        :value="stagingStats.total_rejected"
        :loading="statsLoading"
        icon="mdi-close-circle"
        color="error"
      />
      <AdminStatsCard
        title="Auto-Normalization Rate"
        :value="`${(normalizationStats.success_rate * 100).toFixed(1)}%`"
        :loading="statsLoading"
        icon="mdi-robot"
        color="info"
      />
    </div>

    <!-- Test Normalization Tool -->
    <Card class="mb-6">
      <CardHeader>
        <CardTitle class="flex items-center">
          <TestTube class="size-5 mr-2" />
          Test Gene Normalization
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p class="text-sm text-muted-foreground mb-4">
          Use this tool to test how the automatic normalization system would handle a gene symbol.
          This helps when reviewing similar cases below.
        </p>
        <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
          <div class="md:col-span-8 space-y-2">
            <Label>Gene symbol to test</Label>
            <Input v-model="testGeneText" placeholder="e.g., BRCA1, PKD1, WT1, MS6HM" />
          </div>
          <div class="md:col-span-4 flex items-end">
            <Button
              class="w-full"
              :disabled="testLoading || !testGeneText.trim()"
              @click="testNormalization"
            >
              <Search class="size-4 mr-1" />
              Test Now
            </Button>
          </div>
        </div>
        <Alert
          v-if="testResult"
          :variant="testResult.success ? 'default' : 'destructive'"
          class="mt-4"
        >
          <AlertDescription>
            <div v-if="testResult.success">
              <strong>This gene can be automatically normalized!</strong><br />
              <div class="mt-2">
                <code>{{ JSON.stringify(testResult.result, null, 2) }}</code>
              </div>
            </div>
            <div v-else>
              <strong>This gene failed automatic normalization</strong><br />
              <span class="text-sm">This is why it would appear in the staging queue below.</span
              ><br />
              <div class="mt-1 text-xs">Error: {{ testResult.error }}</div>
            </div>
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>

    <!-- Filters -->
    <Card class="mb-4">
      <CardContent class="pt-6">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="space-y-2">
            <Label>Data Source</Label>
            <Select v-model="filters.sourceFilter">
              <SelectTrigger>
                <SelectValue placeholder="All sources" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All sources</SelectItem>
                <SelectItem
                  v-for="source in sourceOptions"
                  :key="source.value"
                  :value="source.value"
                >
                  {{ source.title }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-2">
            <Label>Results per page</Label>
            <Select v-model="filtersLimitStr" @update:model-value="updateFilterLimit">
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="n in [10, 25, 50, 100]" :key="n" :value="String(n)">
                  {{ n }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="flex items-end">
            <div class="flex items-center gap-2">
              <Switch
                :checked="filters.expertReviewOnly"
                @update:checked="filters.expertReviewOnly = $event"
              />
              <Label>Expert review only</Label>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Pending Reviews Table -->
    <Card>
      <CardHeader class="flex flex-row items-center justify-between">
        <CardTitle class="flex items-center">
          <List class="size-5 mr-2" />
          Pending Reviews ({{ pendingReviews.length }})
        </CardTitle>
        <Badge v-if="selectedItems.length > 0"> {{ selectedItems.length }} selected </Badge>
      </CardHeader>
      <CardContent class="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead class="w-[40px]">
                <Checkbox :checked="allSelected" @update:checked="toggleAllSelection" />
              </TableHead>
              <TableHead class="w-[180px]">Gene Symbol</TableHead>
              <TableHead class="w-[120px]">Data Source</TableHead>
              <TableHead class="w-[140px]">Review Priority</TableHead>
              <TableHead class="w-[120px]">Expert Needed</TableHead>
              <TableHead class="w-[120px]">Submitted</TableHead>
              <TableHead class="w-[140px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-if="loading">
              <TableCell colspan="7" class="text-center py-8 text-muted-foreground">
                Loading...
              </TableCell>
            </TableRow>
            <TableRow v-else-if="pendingReviews.length === 0">
              <TableCell colspan="7" class="text-center py-8 text-muted-foreground">
                No pending reviews
              </TableCell>
            </TableRow>
            <TableRow v-for="item in pendingReviews" :key="item.id">
              <TableCell>
                <Checkbox
                  :checked="selectedItems.includes(item.id)"
                  @update:checked="toggleItemSelection(item.id, $event)"
                />
              </TableCell>
              <TableCell>
                <code class="text-xs">{{ item.original_text }}</code>
              </TableCell>
              <TableCell>
                <Badge variant="outline">{{ item.source_name }}</Badge>
              </TableCell>
              <TableCell>
                <Badge :variant="getPriorityVariant(item.priority_score)">
                  {{ item.priority_score }}
                </Badge>
              </TableCell>
              <TableCell>
                <component
                  :is="item.requires_expert_review ? BriefcaseBusiness : Check"
                  class="size-4"
                  :class="
                    item.requires_expert_review
                      ? 'text-orange-500'
                      : 'text-green-600 dark:text-green-400'
                  "
                />
              </TableCell>
              <TableCell>
                <span class="text-xs">{{ formatDate(item.created_at) }}</span>
              </TableCell>
              <TableCell>
                <div class="flex gap-1">
                  <Tooltip>
                    <TooltipTrigger as-child>
                      <Button
                        variant="ghost"
                        size="icon"
                        class="h-8 w-8 text-green-600"
                        @click="approveItem(item)"
                      >
                        <CircleCheck class="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Approve: This IS a valid gene</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger as-child>
                      <Button
                        variant="ghost"
                        size="icon"
                        class="h-8 w-8 text-destructive"
                        @click="rejectItem(item)"
                      >
                        <CircleX class="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Reject: This is NOT a valid gene</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger as-child>
                      <Button
                        variant="ghost"
                        size="icon"
                        class="h-8 w-8"
                        @click="showItemDetails(item)"
                      >
                        <Info class="size-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>View details</TooltipContent>
                  </Tooltip>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>

      <!-- Bulk Actions -->
      <div v-if="selectedItems.length > 0" class="flex items-center gap-2 p-4 border-t">
        <Button
          variant="outline"
          class="border-green-500 text-green-600"
          :disabled="bulkActionLoading"
          @click="bulkApprove"
        >
          <CheckCheck class="size-4 mr-2" />
          Bulk Approve ({{ selectedItems.length }})
        </Button>
        <Button
          variant="outline"
          class="border-red-500 text-red-600"
          :disabled="bulkActionLoading"
          @click="bulkReject"
        >
          <Ban class="size-4 mr-2" />
          Bulk Reject ({{ selectedItems.length }})
        </Button>
        <div class="flex-1" />
        <Button variant="ghost" @click="selectedItems = []">Clear Selection</Button>
      </div>
    </Card>

    <!-- Approve Dialog -->
    <Dialog v-model:open="approveDialog">
      <DialogContent class="max-w-[700px]">
        <DialogHeader>
          <DialogTitle class="flex items-center">
            <CircleCheck class="size-5 text-green-600 dark:text-green-400 mr-2" />
            Approve Gene: {{ selectedItem?.original_text }}
          </DialogTitle>
        </DialogHeader>
        <div class="space-y-4">
          <Alert>
            <AlertDescription>
              <strong>You're confirming this IS a valid gene.</strong> Please provide the correct,
              official HGNC gene symbol. The system will create a new gene record or link to an
              existing one.
            </AlertDescription>
          </Alert>

          <div>
            <strong>Original text from {{ selectedItem?.source_name }}:</strong>
            <code class="text-lg ml-2">{{ selectedItem?.original_text }}</code>
          </div>

          <div>
            <strong>Why it failed:</strong>
            <span class="text-sm text-muted-foreground ml-2">
              {{ selectedItem?.normalization_log?.failure_reason || 'Unknown error' }}
            </span>
          </div>

          <div class="space-y-2">
            <Label>Correct HGNC Gene Symbol *</Label>
            <Input v-model="approveForm.approved_symbol" placeholder="e.g., PKD1, BRCA1, WT1" />
            <p class="text-xs text-muted-foreground">
              Enter the official HGNC gene symbol (usually all caps)
            </p>
          </div>

          <div class="space-y-2">
            <Label>HGNC ID (if known)</Label>
            <Input v-model="approveForm.hgnc_id" placeholder="e.g., HGNC:1234" />
            <p class="text-xs text-muted-foreground">
              Optional - system will look this up if not provided
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

          <div class="space-y-2">
            <Label>Your Name/ID *</Label>
            <Input v-model="approveForm.reviewer" placeholder="Your name or ID" />
            <p class="text-xs text-muted-foreground">This will be recorded for the audit trail</p>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="approveDialog = false">
            <Ban class="size-4 mr-1" />
            Cancel
          </Button>
          <Button
            :disabled="
              actionLoading || !approveForm.approved_symbol?.trim() || !approveForm.reviewer?.trim()
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
            <CircleX class="size-5 text-destructive mr-2" />
            Reject: {{ selectedItem?.original_text }}
          </AlertDialogTitle>
          <AlertDialogDescription>
            You're marking this as NOT a valid gene. This could be a typo, abbreviation, protein
            name, or other non-gene text.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div class="space-y-4">
          <div>
            <strong>Text from {{ selectedItem?.source_name }}:</strong>
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

          <div class="space-y-2">
            <Label>Your Name/ID *</Label>
            <Input v-model="rejectForm.reviewer" placeholder="Your name or ID" />
            <p class="text-xs text-muted-foreground">This will be recorded for the audit trail</p>
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
            class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            :disabled="actionLoading || !rejectForm.notes?.trim() || !rejectForm.reviewer?.trim()"
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
              <div><strong>Source:</strong> {{ selectedItem.source_name }}</div>
              <div>
                <strong>Priority Score:</strong>
                {{ (selectedItem.priority_score * 100).toFixed(1) }}%
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
                <Badge :variant="getStatusVariant(selectedItem.status)" class="ml-1">
                  {{ selectedItem.status }}
                </Badge>
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
import { ref, reactive, onMounted, computed, watch } from 'vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as stagingApi from '@/api/admin/staging'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'
import { toast } from 'vue-sonner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Checkbox } from '@/components/ui/checkbox'
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import {
  Ban,
  BriefcaseBusiness,
  Check,
  CheckCheck,
  CircleCheck,
  CircleX,
  Dna,
  Info,
  List,
  RefreshCw,
  Search,
  TestTube
} from 'lucide-vue-next'

// Reactive data
const loading = ref(false)
const statsLoading = ref(false)
const testLoading = ref(false)
const actionLoading = ref(false)
const bulkActionLoading = ref(false)

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
const testGeneText = ref('')
const testResult = ref(null)

// Filters
const filters = reactive({
  sourceFilter: null,
  limit: 50,
  expertReviewOnly: false
})
const filtersLimitStr = ref('50')

// Data
const pendingReviews = ref([])
const selectedItems = ref([])

// Dialogs
const approveDialog = ref(false)
const rejectDialog = ref(false)
const detailsDialog = ref(false)
const selectedItem = ref(null)

// Forms
const approveForm = reactive({
  approved_symbol: '',
  hgnc_id: '',
  notes: '',
  reviewer: 'Admin User'
})

const rejectForm = reactive({
  notes: '',
  reviewer: 'Admin User'
})

// Computed
const sourceOptions = computed(() => {
  const sources = [...new Set(pendingReviews.value.map(item => item.source_name))]
  return sources.map(source => ({ title: source, value: source }))
})

const allSelected = computed(() => {
  return (
    pendingReviews.value.length > 0 && selectedItems.value.length === pendingReviews.value.length
  )
})

// Methods
const toggleAllSelection = checked => {
  if (checked) {
    selectedItems.value = pendingReviews.value.map(item => item.id)
  } else {
    selectedItems.value = []
  }
}

const toggleItemSelection = (id, checked) => {
  if (checked) {
    selectedItems.value = [...selectedItems.value, id]
  } else {
    selectedItems.value = selectedItems.value.filter(i => i !== id)
  }
}

const updateFilterLimit = val => {
  filters.limit = parseInt(val)
  filtersLimitStr.value = val
}

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
  try {
    const params = {
      limit: filters.limit,
      source_filter: filters.sourceFilter === 'all' ? '' : filters.sourceFilter,
      requires_expert_review: filters.expertReviewOnly || undefined
    }

    const response = await stagingApi.getPendingStaging(params)
    pendingReviews.value = response.data
  } catch (error) {
    window.logService.error('Failed to load pending reviews:', error)
    toast.error('Failed to load pending reviews', { duration: Infinity })
  } finally {
    loading.value = false
  }
}

const loadData = async () => {
  await Promise.all([loadStats(), loadPendingReviews()])
}

const testNormalization = async () => {
  if (!testGeneText.value.trim()) return

  testLoading.value = true
  testResult.value = null

  try {
    const response = await stagingApi.testNormalization(testGeneText.value.trim())
    testResult.value = response.data
  } catch (error) {
    window.logService.error('Failed to test normalization:', error)
    testResult.value = {
      success: false,
      error: error.response?.data?.detail || error.message
    }
  } finally {
    testLoading.value = false
  }
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
  if (!selectedItem.value || !approveForm.approved_symbol || !approveForm.reviewer) return

  actionLoading.value = true
  try {
    await stagingApi.approveStaging(selectedItem.value.id, {
      approved_symbol: approveForm.approved_symbol,
      hgnc_id: approveForm.hgnc_id || null,
      notes: approveForm.notes || null,
      reviewer: approveForm.reviewer
    })

    toast.success('Gene staging approved successfully', { duration: 5000 })
    approveDialog.value = false
    await loadData()
  } catch (error) {
    window.logService.error('Failed to approve staging:', error)
    toast.error('Failed to approve gene staging', { duration: Infinity })
  } finally {
    actionLoading.value = false
  }
}

const confirmReject = async () => {
  if (!selectedItem.value || !rejectForm.notes || !rejectForm.reviewer) return

  actionLoading.value = true
  try {
    await stagingApi.rejectStaging(selectedItem.value.id, {
      notes: rejectForm.notes,
      reviewer: rejectForm.reviewer
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

const bulkApprove = async () => {
  if (selectedItems.value.length === 0) return
  toast.warning('Bulk approve not yet implemented - please approve items individually', {
    duration: 5000
  })
}

const bulkReject = async () => {
  if (selectedItems.value.length === 0) return
  toast.warning('Bulk reject not yet implemented - please reject items individually', {
    duration: 5000
  })
}

// Utility methods
const formatDate = dateString => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString()
}

const getPriorityVariant = score => {
  if (score >= 80) return 'destructive'
  if (score >= 50) return 'outline'
  if (score >= 30) return 'secondary'
  return 'default'
}

const getStatusVariant = status => {
  switch (status?.toLowerCase()) {
    case 'pending':
      return 'outline'
    case 'approved':
      return 'default'
    case 'rejected':
      return 'destructive'
    default:
      return 'secondary'
  }
}

// Watchers for filters
watch(
  [() => filters.sourceFilter, () => filters.limit, () => filters.expertReviewOnly],
  () => {
    loadPendingReviews()
  },
  { deep: true }
)

// Load data on mount
onMounted(() => {
  loadData()
})
</script>
