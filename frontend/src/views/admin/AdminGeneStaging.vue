<template>
  <v-container>
    <AdminHeader
      title="Gene Staging"
      subtitle="Review genes that couldn't be automatically normalized to HGNC symbols"
      icon="mdi-dna"
      icon-color="red"
      :breadcrumbs="ADMIN_BREADCRUMBS.staging"
    >
      <template #actions>
        <v-btn
          color="primary"
          variant="elevated"
          prepend-icon="mdi-refresh"
          :loading="loading"
          @click="loadData"
        >
          Refresh
        </v-btn>
      </template>
    </AdminHeader>

    <!-- Process Explanation -->
    <v-alert type="info" variant="tonal" class="mb-6" prominent>
      <template #prepend>
        <v-icon>mdi-information</v-icon>
      </template>
      <div class="text-body-1">
        <strong>Gene Staging Process:</strong> When data sources provide gene names that can't be
        automatically matched to official HGNC symbols, they're sent here for manual review. Your
        job is to either <strong>approve</strong> them with the correct HGNC symbol, or
        <strong>reject</strong> them if they're not real genes.
      </div>
    </v-alert>

    <!-- Stats Overview -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Needs Your Review"
          :value="stagingStats.total_pending"
          :loading="statsLoading"
          icon="mdi-account-search"
          color="warning"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Successfully Approved"
          :value="stagingStats.total_approved"
          :loading="statsLoading"
          icon="mdi-check-circle"
          color="success"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Rejected (Not Genes)"
          :value="stagingStats.total_rejected"
          :loading="statsLoading"
          icon="mdi-close-circle"
          color="error"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Auto-Normalization Rate"
          :value="`${(normalizationStats.success_rate * 100).toFixed(1)}%`"
          :loading="statsLoading"
          icon="mdi-robot"
          color="info"
        />
      </v-col>
    </v-row>

    <!-- Test Normalization Tool -->
    <v-card class="mb-6">
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-test-tube</v-icon>
        Test Gene Normalization
        <v-tooltip activator="parent" location="top">
          Test if a gene symbol can be automatically normalized before reviewing similar cases
        </v-tooltip>
      </v-card-title>
      <v-card-text>
        <p class="text-body-2 text-medium-emphasis mb-4">
          Use this tool to test how the automatic normalization system would handle a gene symbol.
          This helps when reviewing similar cases below.
        </p>
        <v-row>
          <v-col cols="12" md="8">
            <v-text-field
              v-model="testGeneText"
              label="Gene symbol to test"
              placeholder="e.g., BRCA1, PKD1, WT1, MS6HM"
              density="compact"
              variant="outlined"
              hide-details
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-btn
              color="primary"
              block
              :loading="testLoading"
              :disabled="!testGeneText.trim()"
              @click="testNormalization"
            >
              <v-icon start>mdi-magnify</v-icon>
              Test Now
            </v-btn>
          </v-col>
        </v-row>
        <v-alert
          v-if="testResult"
          :type="testResult.success ? 'success' : 'warning'"
          class="mt-4"
          variant="tonal"
        >
          <div v-if="testResult.success">
            <strong>✓ This gene can be automatically normalized!</strong><br />
            <div class="mt-2">
              <code>{{ JSON.stringify(testResult.result, null, 2) }}</code>
            </div>
          </div>
          <div v-else>
            <strong>⚠ This gene failed automatic normalization</strong><br />
            <span class="text-body-2">This is why it would appear in the staging queue below.</span
            ><br />
            <div class="mt-1 text-caption">Error: {{ testResult.error }}</div>
          </div>
        </v-alert>
      </v-card-text>
    </v-card>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row>
          <v-col cols="12" md="4">
            <v-select
              v-model="filters.sourceFilter"
              label="Data Source"
              :items="sourceOptions"
              density="compact"
              variant="outlined"
              clearable
              hide-details
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-select
              v-model="filters.limit"
              label="Results per page"
              :items="[10, 25, 50, 100]"
              density="compact"
              variant="outlined"
              hide-details
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-switch
              v-model="filters.expertReviewOnly"
              label="Expert review only"
              density="compact"
              hide-details
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Pending Reviews Table -->
    <v-card>
      <v-card-title class="d-flex align-center justify-space-between">
        <div class="d-flex align-center">
          <v-icon class="mr-2">mdi-format-list-bulleted</v-icon>
          Pending Reviews ({{ pendingReviews.length }})
        </div>
        <v-chip v-if="selectedItems.length > 0" color="primary" variant="elevated">
          {{ selectedItems.length }} selected
        </v-chip>
      </v-card-title>

      <v-data-table
        v-model="selectedItems"
        :headers="tableHeaders"
        :items="pendingReviews"
        :loading="loading"
        show-select
        item-value="id"
        density="compact"
        class="elevation-0"
      >
        <template #item.original_text="{ item }">
          <code class="text-caption">{{ item.original_text }}</code>
        </template>

        <template #item.source_name="{ item }">
          <v-chip size="small" variant="outlined">
            {{ item.source_name }}
          </v-chip>
        </template>

        <template #item.priority_score="{ item }">
          <div class="d-flex align-center">
            <v-chip
              :color="getPriorityColor(item.priority_score)"
              size="small"
              :text="item.priority_score.toString()"
            />
            <v-tooltip activator="parent" location="top">
              Priority {{ item.priority_score }}/200. Higher scores = more important to review
              first.
              {{ getPriorityDescription(item.priority_score) }}
            </v-tooltip>
          </div>
        </template>

        <template #item.requires_expert_review="{ item }">
          <v-icon
            :icon="item.requires_expert_review ? 'mdi-account-tie' : 'mdi-check'"
            :color="item.requires_expert_review ? 'orange' : 'green'"
            size="small"
          />
        </template>

        <template #item.created_at="{ item }">
          <span class="text-caption">
            {{ formatDate(item.created_at) }}
          </span>
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex ga-1">
            <v-tooltip text="Approve: This IS a valid gene - provide the correct HGNC symbol">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  icon="mdi-check-circle"
                  size="small"
                  color="success"
                  variant="tonal"
                  @click="approveItem(item)"
                />
              </template>
            </v-tooltip>
            <v-tooltip text="Reject: This is NOT a valid gene symbol">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  icon="mdi-close-circle"
                  size="small"
                  color="error"
                  variant="tonal"
                  @click="rejectItem(item)"
                />
              </template>
            </v-tooltip>
            <v-tooltip text="View details: See why normalization failed">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  icon="mdi-information"
                  size="small"
                  color="info"
                  variant="text"
                  @click="showItemDetails(item)"
                />
              </template>
            </v-tooltip>
          </div>
        </template>
      </v-data-table>

      <!-- Bulk Actions -->
      <v-card-actions v-if="selectedItems.length > 0">
        <v-btn
          color="success"
          variant="tonal"
          prepend-icon="mdi-check-all"
          :loading="bulkActionLoading"
          @click="bulkApprove"
        >
          Bulk Approve ({{ selectedItems.length }})
        </v-btn>
        <v-btn
          color="error"
          variant="tonal"
          prepend-icon="mdi-close-octagon"
          :loading="bulkActionLoading"
          @click="bulkReject"
        >
          Bulk Reject ({{ selectedItems.length }})
        </v-btn>
        <v-spacer />
        <v-btn variant="text" @click="selectedItems = []"> Clear Selection </v-btn>
      </v-card-actions>
    </v-card>

    <!-- Approve Dialog -->
    <v-dialog v-model="approveDialog" max-width="700">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="success" class="mr-2">mdi-check-circle</v-icon>
          Approve Gene: {{ selectedItem?.original_text }}
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            <strong>You're confirming this IS a valid gene.</strong> Please provide the correct,
            official HGNC gene symbol. The system will create a new gene record or link to an
            existing one.
          </v-alert>

          <div class="mb-4">
            <strong>Original text from {{ selectedItem?.source_name }}:</strong>
            <code class="text-h6 ml-2">{{ selectedItem?.original_text }}</code>
          </div>

          <div class="mb-4">
            <strong>Why it failed:</strong>
            <span class="text-body-2 text-medium-emphasis ml-2">
              {{ selectedItem?.normalization_log?.failure_reason || 'Unknown error' }}
            </span>
          </div>

          <v-text-field
            v-model="approveForm.approved_symbol"
            label="Correct HGNC Gene Symbol *"
            variant="outlined"
            density="compact"
            placeholder="e.g., PKD1, BRCA1, WT1"
            hint="Enter the official HGNC gene symbol (usually all caps)"
            persistent-hint
            required
          />

          <v-text-field
            v-model="approveForm.hgnc_id"
            label="HGNC ID (if known)"
            variant="outlined"
            density="compact"
            placeholder="e.g., HGNC:1234"
            hint="Optional - system will look this up if not provided"
            persistent-hint
          />

          <v-textarea
            v-model="approveForm.notes"
            label="Review Notes (optional)"
            variant="outlined"
            density="compact"
            rows="2"
            placeholder="Any additional notes about this approval..."
            hint="Optional notes for the audit trail"
            persistent-hint
          />

          <v-text-field
            v-model="approveForm.reviewer"
            label="Your Name/ID *"
            variant="outlined"
            density="compact"
            required
            hint="This will be recorded for the audit trail"
            persistent-hint
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="approveDialog = false">
            <v-icon start>mdi-cancel</v-icon>
            Cancel
          </v-btn>
          <v-btn
            color="success"
            variant="elevated"
            :loading="actionLoading"
            :disabled="!approveForm.approved_symbol?.trim() || !approveForm.reviewer?.trim()"
            @click="confirmApprove"
          >
            <v-icon start>mdi-check-circle</v-icon>
            Approve as Valid Gene
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Reject Dialog -->
    <v-dialog v-model="rejectDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-close-circle</v-icon>
          Reject: {{ selectedItem?.original_text }}
        </v-card-title>
        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            <strong>You're marking this as NOT a valid gene.</strong> This could be a typo,
            abbreviation, protein name, or other non-gene text that was mistakenly identified as a
            gene symbol.
          </v-alert>

          <div class="mb-4">
            <strong>Text from {{ selectedItem?.source_name }}:</strong>
            <code class="text-h6 ml-2">{{ selectedItem?.original_text }}</code>
          </div>

          <div class="mb-4">
            <strong>Why it failed normalization:</strong>
            <span class="text-body-2 text-medium-emphasis ml-2">
              {{ selectedItem?.normalization_log?.failure_reason || 'Unknown error' }}
            </span>
          </div>

          <v-textarea
            v-model="rejectForm.notes"
            label="Why are you rejecting this? *"
            variant="outlined"
            density="compact"
            rows="3"
            placeholder="e.g., 'Not a gene - appears to be a protein complex name' or 'Typo in source data' or 'Abbreviation for a condition, not a gene'"
            hint="Please explain why this is not a valid gene symbol"
            persistent-hint
            required
          />

          <v-text-field
            v-model="rejectForm.reviewer"
            label="Your Name/ID *"
            variant="outlined"
            density="compact"
            required
            hint="This will be recorded for the audit trail"
            persistent-hint
          />

          <div class="mt-3">
            <strong class="text-body-2">Common reasons to reject:</strong>
            <ul class="text-caption text-medium-emphasis mt-1">
              <li>Protein or complex names (e.g., "MS6HM complex")</li>
              <li>Disease or condition names</li>
              <li>Typos or garbled text from data sources</li>
              <li>Non-standard abbreviations</li>
              <li>Chemical compound names</li>
            </ul>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="rejectDialog = false">
            <v-icon start>mdi-cancel</v-icon>
            Cancel
          </v-btn>
          <v-btn
            color="error"
            variant="elevated"
            :loading="actionLoading"
            :disabled="!rejectForm.notes?.trim() || !rejectForm.reviewer?.trim()"
            @click="confirmReject"
          >
            <v-icon start>mdi-close-circle</v-icon>
            Reject as Invalid
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Details Dialog -->
    <v-dialog v-model="detailsDialog" max-width="800">
      <v-card>
        <v-card-title>Gene Staging Details</v-card-title>
        <v-card-text>
          <v-row v-if="selectedItem">
            <v-col cols="12" md="6">
              <div class="mb-3">
                <strong>Original Text:</strong><br />
                <code class="text-body-2">{{ selectedItem.original_text }}</code>
              </div>
              <div class="mb-3"><strong>Source:</strong> {{ selectedItem.source_name }}</div>
              <div class="mb-3">
                <strong>Priority Score:</strong>
                {{ (selectedItem.priority_score * 100).toFixed(1) }}%
              </div>
              <div class="mb-3">
                <strong>Expert Review Required:</strong>
                {{ selectedItem.requires_expert_review ? 'Yes' : 'No' }}
              </div>
            </v-col>
            <v-col cols="12" md="6">
              <div class="mb-3">
                <strong>Created:</strong> {{ formatDate(selectedItem.created_at) }}
              </div>
              <div class="mb-3">
                <strong>Updated:</strong> {{ formatDate(selectedItem.updated_at) }}
              </div>
              <div class="mb-3">
                <strong>Status:</strong>
                <v-chip size="small" :color="getStatusColor(selectedItem.status)">
                  {{ selectedItem.status }}
                </v-chip>
              </div>
            </v-col>
          </v-row>

          <v-divider class="my-4" />

          <div class="mb-3">
            <strong>Original Data:</strong>
            <v-card variant="outlined" class="mt-2">
              <v-card-text>
                <pre class="text-caption">{{
                  JSON.stringify(selectedItem?.original_data, null, 2)
                }}</pre>
              </v-card-text>
            </v-card>
          </div>

          <div class="mb-3">
            <strong>Normalization Log:</strong>
            <v-card variant="outlined" class="mt-2">
              <v-card-text>
                <pre class="text-caption">{{
                  JSON.stringify(selectedItem?.normalization_log, null, 2)
                }}</pre>
              </v-card-text>
            </v-card>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="detailsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="5000">
      {{ snackbar.message }}
      <template #actions>
        <v-btn icon="mdi-close" @click="snackbar.show = false" />
      </template>
    </v-snackbar>
  </v-container>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as stagingApi from '@/api/admin/staging'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'

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

// Snackbar
const snackbar = reactive({
  show: false,
  message: '',
  color: 'info'
})

// Computed
const sourceOptions = computed(() => {
  const sources = [...new Set(pendingReviews.value.map(item => item.source_name))]
  return sources.map(source => ({ title: source, value: source }))
})

const tableHeaders = [
  { title: 'Gene Symbol', key: 'original_text', width: '180px' },
  { title: 'Data Source', key: 'source_name', width: '120px' },
  { title: 'Review Priority', key: 'priority_score', width: '140px' },
  { title: 'Expert Needed', key: 'requires_expert_review', width: '120px' },
  { title: 'Submitted', key: 'created_at', width: '120px' },
  { title: 'Actions', key: 'actions', sortable: false, width: '140px' }
]

// Methods
const showSnackbar = (message, color = 'info') => {
  snackbar.message = message
  snackbar.color = color
  snackbar.show = true
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
    showSnackbar('Failed to load statistics', 'error')
  } finally {
    statsLoading.value = false
  }
}

const loadPendingReviews = async () => {
  loading.value = true
  try {
    const params = {
      limit: filters.limit,
      source_filter: filters.sourceFilter,
      requires_expert_review: filters.expertReviewOnly || undefined
    }

    const response = await stagingApi.getPendingStaging(params)
    pendingReviews.value = response.data
  } catch (error) {
    window.logService.error('Failed to load pending reviews:', error)
    showSnackbar('Failed to load pending reviews', 'error')
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

    showSnackbar('Gene staging approved successfully', 'success')
    approveDialog.value = false
    await loadData()
  } catch (error) {
    window.logService.error('Failed to approve staging:', error)
    showSnackbar('Failed to approve gene staging', 'error')
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

    showSnackbar('Gene staging rejected', 'success')
    rejectDialog.value = false
    await loadData()
  } catch (error) {
    window.logService.error('Failed to reject staging:', error)
    showSnackbar('Failed to reject gene staging', 'error')
  } finally {
    actionLoading.value = false
  }
}

const bulkApprove = async () => {
  if (selectedItems.value.length === 0) return

  // For bulk operations, we'd need to implement a different approach
  // For now, show a message that this feature needs implementation
  showSnackbar('Bulk approve not yet implemented - please approve items individually', 'warning')
}

const bulkReject = async () => {
  if (selectedItems.value.length === 0) return

  // For bulk operations, we'd need to implement a different approach
  showSnackbar('Bulk reject not yet implemented - please reject items individually', 'warning')
}

// Utility methods
const formatDate = dateString => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString()
}

const getPriorityColor = score => {
  if (score >= 80) return 'error' // High priority (clinical sources)
  if (score >= 50) return 'warning' // Medium priority
  if (score >= 30) return 'info' // Low-medium priority
  return 'success' // Low priority (literature mining)
}

const getPriorityDescription = score => {
  if (score >= 80) return 'High priority - from clinical/expert sources'
  if (score >= 50) return 'Medium priority - likely important gene'
  if (score >= 30) return 'Low-medium priority - some matching hints'
  return 'Low priority - from automated literature mining'
}

const getStatusColor = status => {
  switch (status?.toLowerCase()) {
    case 'pending':
      return 'warning'
    case 'approved':
      return 'success'
    case 'rejected':
      return 'error'
    default:
      return 'grey'
  }
}

// Watchers for filters
import { watch } from 'vue'
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
