# Frontend Implementation Plan

## Overview

Modern Vue 3 + Vite frontend implementing a sophisticated gene curation interface with real-time data visualization, professional workflow management, and advanced search capabilities. Built specifically for scientific curation workflows.

## Architecture

### Technology Stack
- **Framework**: Vue 3 with Composition API + TypeScript
- **Build Tool**: Vite with Hot Module Replacement
- **UI Framework**: Vuetify 3 for Material Design components
- **State Management**: Pinia for reactive state management
- **HTTP Client**: Axios with interceptors for API communication
- **Charts**: Chart.js/Vue-Chart.js for data visualization
- **Tables**: Vuetify Data Tables with server-side pagination
- **Forms**: VeeValidate with Yup schemas for validation
- **Testing**: Vitest + Vue Testing Library

### Project Structure
```
frontend/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── api/
│   │   ├── client.ts                    # Axios configuration
│   │   ├── types.ts                     # API response types
│   │   └── endpoints/
│   │       ├── genes.ts                 # Gene endpoints
│   │       ├── curations.ts             # Curation endpoints
│   │       ├── search.ts                # Search endpoints
│   │       └── workflow.ts              # Workflow endpoints
│   ├── components/
│   │   ├── common/
│   │   │   ├── AppHeader.vue
│   │   │   ├── AppSidebar.vue
│   │   │   ├── LoadingSpinner.vue
│   │   │   └── ConfirmDialog.vue
│   │   ├── curation/
│   │   │   ├── CurationCard.vue         # Gene curation summary card
│   │   │   ├── EvidenceTable.vue        # Evidence sources table
│   │   │   ├── AssertionEditor.vue      # Gene-disease assertion editor
│   │   │   ├── WorkflowTracker.vue      # Curation workflow progress
│   │   │   └── ScoreVisualization.vue   # Evidence score charts
│   │   ├── search/
│   │   │   ├── AdvancedSearch.vue       # Multi-criteria search form
│   │   │   ├── SearchFilters.vue        # Filter sidebar
│   │   │   ├── SearchResults.vue        # Results table with pagination
│   │   │   └── SavedSearches.vue        # Saved search management
│   │   ├── forms/
│   │   │   ├── GeneForm.vue             # Gene information form
│   │   │   ├── EvidenceForm.vue         # Evidence entry form
│   │   │   ├── WorkflowForm.vue         # Workflow action form
│   │   │   └── ExportForm.vue           # Data export configuration
│   │   └── visualization/
│   │       ├── EvidenceScoreChart.vue   # Evidence scoring visualization
│   │       ├── SourceDistribution.vue   # Evidence source pie chart
│   │       ├── WorkflowTimeline.vue     # Curation timeline
│   │       └── NetworkGraph.vue         # Gene interaction network
│   ├── stores/
│   │   ├── auth.ts                      # Authentication state
│   │   ├── genes.ts                     # Gene data state
│   │   ├── curations.ts                 # Curation state
│   │   ├── search.ts                    # Search state and history
│   │   └── ui.ts                        # UI state (themes, notifications)
│   ├── views/
│   │   ├── Dashboard.vue                # Main dashboard with statistics
│   │   ├── GeneList.vue                 # Gene browser with search
│   │   ├── GeneDetail.vue               # Detailed gene view
│   │   ├── CurationEditor.vue           # Curation editing interface
│   │   ├── WorkflowManager.vue          # Workflow management view
│   │   ├── Search.vue                   # Advanced search interface
│   │   ├── Reports.vue                  # Analytics and reporting
│   │   └── Settings.vue                 # User preferences
│   ├── router/
│   │   ├── index.ts                     # Vue Router configuration
│   │   └── guards.ts                    # Route guards for authentication
│   ├── composables/
│   │   ├── useApi.ts                    # API interaction composable
│   │   ├── useAuth.ts                   # Authentication composable
│   │   ├── usePagination.ts             # Pagination logic
│   │   ├── useSearch.ts                 # Search functionality
│   │   └── useNotifications.ts          # Toast notifications
│   ├── utils/
│   │   ├── formatters.ts                # Data formatting utilities
│   │   ├── validators.ts                # Form validation schemas
│   │   ├── constants.ts                 # Application constants
│   │   └── export.ts                    # Data export utilities
│   ├── types/
│   │   ├── api.ts                       # API type definitions
│   │   ├── curation.ts                  # Curation data types
│   │   └── ui.ts                        # UI component types
│   ├── assets/
│   │   ├── styles/
│   │   │   ├── main.scss                # Global styles
│   │   │   ├── variables.scss           # SCSS variables
│   │   │   └── vuetify.scss             # Vuetify customizations
│   │   └── images/
│   ├── plugins/
│   │   ├── vuetify.ts                   # Vuetify configuration
│   │   └── axios.ts                     # Axios interceptors
│   ├── App.vue                          # Root component
│   └── main.ts                          # Application entry point
├── vite.config.ts                       # Vite configuration
├── package.json
├── tsconfig.json
└── Dockerfile
```

## Key Implementation Details

### 1. API Integration Layer

**Centralized API Client**:
```typescript
// src/api/client.ts
import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { useAuthStore } from '@/stores/auth'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor for auth token
    this.client.interceptors.request.use((config) => {
      const authStore = useAuthStore()
      if (authStore.token) {
        config.headers.Authorization = `Bearer ${authStore.token}`
      }
      return config
    })

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error) => {
        if (error.response?.status === 401) {
          const authStore = useAuthStore()
          authStore.logout()
        }
        return Promise.reject(error)
      }
    )
  }

  async get<T>(url: string, params?: any): Promise<T> {
    const response = await this.client.get<T>(url, { params })
    return response.data
  }

  async post<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.post<T>(url, data)
    return response.data
  }

  async put<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.put<T>(url, data)
    return response.data
  }

  async delete<T>(url: string): Promise<T> {
    const response = await this.client.delete<T>(url)
    return response.data
  }
}

export const apiClient = new ApiClient()
```

**Curation API Endpoints**:
```typescript
// src/api/endpoints/curations.ts
import { apiClient } from '../client'
import type { 
  CurationResponse, 
  CurationCreate, 
  CurationSearchParams,
  PaginatedResponse 
} from '../types'

export const curationApi = {
  // Get all curations with pagination and filtering
  async search(params: CurationSearchParams): Promise<PaginatedResponse<CurationResponse>> {
    return apiClient.get('/curations/search', params)
  },

  // Get specific curation by ID
  async getById(id: string): Promise<CurationResponse> {
    return apiClient.get(`/curations/${id}`)
  },

  // Create new curation
  async create(data: CurationCreate): Promise<CurationResponse> {
    return apiClient.post('/curations/', data)
  },

  // Update existing curation
  async update(id: string, data: Partial<CurationCreate>): Promise<CurationResponse> {
    return apiClient.put(`/curations/${id}`, data)
  },

  // Advance curation through workflow
  async advanceWorkflow(id: string, action: string, comment: string) {
    return apiClient.post(`/curations/${id}/workflow/advance`, { action, comment })
  },

  // Export curation data
  async export(params: { format: 'json' | 'csv' | 'gencc' }): Promise<Blob> {
    return apiClient.get('/curations/export', params)
  }
}
```

### 2. State Management with Pinia

**Curation Store**:
```typescript
// src/stores/curations.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { curationApi } from '@/api/endpoints/curations'
import type { CurationResponse, CurationSearchParams } from '@/api/types'

export const useCurationStore = defineStore('curations', () => {
  // State
  const curations = ref<CurationResponse[]>([])
  const currentCuration = ref<CurationResponse | null>(null)
  const loading = ref(false)
  const searchParams = ref<CurationSearchParams>({
    skip: 0,
    limit: 20,
    min_score: undefined,
    classification: undefined,
    workflow_status: undefined
  })
  const totalCount = ref(0)

  // Getters
  const highConfidenceCurations = computed(() =>
    curations.value.filter(c => 
      ['Definitive', 'Strong'].includes(c.core_metrics.highest_confidence_classification)
    )
  )

  const curationsByStatus = computed(() => {
    const statusCounts: Record<string, number> = {}
    curations.value.forEach(c => {
      const status = c.curation_workflow.status
      statusCounts[status] = (statusCounts[status] || 0) + 1
    })
    return statusCounts
  })

  // Actions
  async function searchCurations(params: Partial<CurationSearchParams> = {}) {
    loading.value = true
    try {
      const mergedParams = { ...searchParams.value, ...params }
      const response = await curationApi.search(mergedParams)
      
      curations.value = response.curations
      totalCount.value = response.total
      searchParams.value = { ...mergedParams, skip: response.skip, limit: response.limit }
    } catch (error) {
      console.error('Failed to search curations:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function getCuration(id: string) {
    loading.value = true
    try {
      currentCuration.value = await curationApi.getById(id)
    } catch (error) {
      console.error('Failed to get curation:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function createCuration(data: CurationCreate) {
    loading.value = true
    try {
      const newCuration = await curationApi.create(data)
      curations.value.unshift(newCuration)
      return newCuration
    } catch (error) {
      console.error('Failed to create curation:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function advanceWorkflow(id: string, action: string, comment: string) {
    try {
      await curationApi.advanceWorkflow(id, action, comment)
      // Refresh current curation if it's the one being updated
      if (currentCuration.value?.id === id) {
        await getCuration(id)
      }
      // Refresh list if it contains this curation
      const index = curations.value.findIndex(c => c.id === id)
      if (index !== -1) {
        await searchCurations()
      }
    } catch (error) {
      console.error('Failed to advance workflow:', error)
      throw error
    }
  }

  return {
    // State
    curations,
    currentCuration,
    loading,
    searchParams,
    totalCount,
    
    // Getters
    highConfidenceCurations,
    curationsByStatus,
    
    // Actions
    searchCurations,
    getCuration,
    createCuration,
    advanceWorkflow
  }
})
```

### 3. Advanced Search Interface

**Search Component**:
```vue
<!-- src/components/search/AdvancedSearch.vue -->
<template>
  <v-card>
    <v-card-title>Advanced Gene Search</v-card-title>
    <v-card-text>
      <v-form @submit.prevent="performSearch">
        <v-row>
          <!-- Basic Search -->
          <v-col cols="12" md="4">
            <v-text-field
              v-model="searchForm.gene_symbol"
              label="Gene Symbol"
              placeholder="e.g. PKD1, NPHS1"
              clearable
            />
          </v-col>
          
          <!-- Evidence Score Range -->
          <v-col cols="12" md="4">
            <v-range-slider
              v-model="searchForm.score_range"
              label="Evidence Score Range"
              :min="0"
              :max="100"
              :step="1"
              thumb-label
            />
          </v-col>
          
          <!-- Classification Filter -->
          <v-col cols="12" md="4">
            <v-select
              v-model="searchForm.classification"
              :items="classificationOptions"
              label="Classification"
              multiple
              chips
              clearable
            />
          </v-col>
          
          <!-- Workflow Status -->
          <v-col cols="12" md="4">
            <v-select
              v-model="searchForm.workflow_status"
              :items="workflowStatusOptions"
              label="Workflow Status"
              multiple
              chips
              clearable
            />
          </v-col>
          
          <!-- Evidence Source -->
          <v-col cols="12" md="4">
            <v-autocomplete
              v-model="searchForm.evidence_sources"
              :items="evidenceSourceOptions"
              label="Evidence Sources"
              multiple
              chips
              clearable
            />
          </v-col>
          
          <!-- Curator Filter -->
          <v-col cols="12" md="4">
            <v-autocomplete
              v-model="searchForm.curator"
              :items="curatorOptions"
              label="Curator"
              clearable
            />
          </v-col>
        </v-row>
        
        <!-- Search Actions -->
        <v-row>
          <v-col>
            <v-btn
              type="submit"
              color="primary"
              :loading="loading"
              prepend-icon="mdi-magnify"
            >
              Search
            </v-btn>
            <v-btn
              variant="outlined"
              @click="resetSearch"
              class="ml-2"
            >
              Reset
            </v-btn>
            <v-btn
              variant="outlined"
              @click="saveSearch"
              class="ml-2"
              prepend-icon="mdi-content-save"
            >
              Save Search
            </v-btn>
          </v-col>
        </v-row>
      </v-form>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useCurationStore } from '@/stores/curations'
import { useNotifications } from '@/composables/useNotifications'

const curationStore = useCurationStore()
const { showSuccess, showError } = useNotifications()

const loading = ref(false)

const searchForm = reactive({
  gene_symbol: '',
  score_range: [0, 100],
  classification: [],
  workflow_status: [],
  evidence_sources: [],
  curator: ''
})

const classificationOptions = [
  'Definitive',
  'Strong', 
  'Moderate',
  'Limited',
  'Disputed',
  'Refuted',
  'No Known Disease Relationship'
]

const workflowStatusOptions = [
  'Automated',
  'In_Primary_Review',
  'In_Secondary_Review',
  'Expert_Review', 
  'Approved',
  'Published'
]

const evidenceSourceOptions = [
  'ClinGen',
  'PanelApp UK',
  'PanelApp Australia',
  'Blueprint Genetics',
  'Literature Review',
  'OMIM',
  'HPO'
]

const curatorOptions = ref<string[]>([]) // Populated from API

async function performSearch() {
  loading.value = true
  try {
    const params = {
      gene_symbol: searchForm.gene_symbol || undefined,
      min_score: searchForm.score_range[0] > 0 ? searchForm.score_range[0] : undefined,
      max_score: searchForm.score_range[1] < 100 ? searchForm.score_range[1] : undefined,
      classification: searchForm.classification.length > 0 ? searchForm.classification : undefined,
      workflow_status: searchForm.workflow_status.length > 0 ? searchForm.workflow_status : undefined,
      evidence_sources: searchForm.evidence_sources.length > 0 ? searchForm.evidence_sources : undefined,
      curator: searchForm.curator || undefined,
      skip: 0,
      limit: 50
    }
    
    await curationStore.searchCurations(params)
    showSuccess('Search completed successfully')
  } catch (error) {
    showError('Search failed. Please try again.')
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  Object.assign(searchForm, {
    gene_symbol: '',
    score_range: [0, 100],
    classification: [],
    workflow_status: [],
    evidence_sources: [],
    curator: ''
  })
}

function saveSearch() {
  // Implementation for saving search parameters
  showSuccess('Search saved successfully')
}
</script>
```

### 4. Data Visualization Components

**Evidence Score Visualization**:
```vue
<!-- src/components/visualization/EvidenceScoreChart.vue -->
<template>
  <v-card>
    <v-card-title>Evidence Score Breakdown</v-card-title>
    <v-card-text>
      <canvas ref="chartCanvas"></canvas>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
} from 'chart.js'
import { Bar } from 'vue-chartjs'
import type { CurationResponse } from '@/api/types'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

interface Props {
  curation: CurationResponse
}

const props = defineProps<Props>()
const chartCanvas = ref<HTMLCanvasElement>()

const chartData = computed(() => {
  const assertions = props.curation.assertions || []
  const sourceCategories: Record<string, number> = {}
  
  assertions.forEach(assertion => {
    assertion.evidence?.forEach(evidence => {
      const category = evidence.source_category
      const weight = evidence.weight_in_scoring || 0.5
      sourceCategories[category] = (sourceCategories[category] || 0) + weight
    })
  })
  
  return {
    labels: Object.keys(sourceCategories),
    datasets: [
      {
        label: 'Evidence Weight',
        data: Object.values(sourceCategories),
        backgroundColor: [
          '#4CAF50',  // Expert Panel - Green
          '#2196F3',  // Literature - Blue
          '#FF9800',  // Diagnostic Panel - Orange
          '#9C27B0',  // Constraint Evidence - Purple
          '#607D8B'   // Database - Grey
        ],
        borderColor: '#fff',
        borderWidth: 2
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  plugins: {
    title: {
      display: true,
      text: 'Evidence Sources by Category'
    },
    legend: {
      display: false
    },
    tooltip: {
      callbacks: {
        label: (context: any) => {
          const category = context.label
          const weight = context.raw
          return `${category}: ${weight.toFixed(2)} points`
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      title: {
        display: true,
        text: 'Evidence Weight'
      }
    },
    x: {
      title: {
        display: true,
        text: 'Source Category'
      }
    }
  }
}

onMounted(() => {
  if (chartCanvas.value) {
    new ChartJS(chartCanvas.value, {
      type: 'bar',
      data: chartData.value,
      options: chartOptions
    })
  }
})
</script>
```

### 5. Workflow Management Interface

**Workflow Tracker Component**:
```vue
<!-- src/components/curation/WorkflowTracker.vue -->
<template>
  <v-card>
    <v-card-title>Curation Workflow</v-card-title>
    <v-card-text>
      <!-- Status Timeline -->
      <v-timeline align="start" class="mb-4">
        <v-timeline-item
          v-for="(step, index) in workflowSteps"
          :key="step.status"
          :color="getStepColor(step.status)"
          :icon="getStepIcon(step.status)"
          size="small"
        >
          <template #opposite>
            <span class="text-caption">{{ step.date }}</span>
          </template>
          
          <v-card variant="outlined" :color="getStepColor(step.status)">
            <v-card-title class="text-h6">{{ step.status }}</v-card-title>
            <v-card-text>
              <div class="text-body-2 mb-2">{{ step.description }}</div>
              <div v-if="step.curator" class="text-caption">
                <strong>Curator:</strong> {{ step.curator }}
              </div>
              <div v-if="step.comment" class="text-caption mt-1">
                <strong>Note:</strong> {{ step.comment }}
              </div>
            </v-card-text>
          </v-card>
        </v-timeline-item>
      </v-timeline>
      
      <!-- Current Actions -->
      <v-card v-if="availableActions.length > 0" variant="outlined">
        <v-card-title>Available Actions</v-card-title>
        <v-card-text>
          <v-row>
            <v-col
              v-for="action in availableActions"
              :key="action.name"
              cols="12"
              sm="6"
              md="4"
            >
              <v-btn
                :color="action.color"
                variant="outlined"
                @click="showActionDialog(action)"
                block
              >
                {{ action.label }}
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-card-text>
    
    <!-- Action Dialog -->
    <v-dialog v-model="actionDialog" max-width="500">
      <v-card>
        <v-card-title>{{ selectedAction?.label }}</v-card-title>
        <v-card-text>
          <v-textarea
            v-model="actionComment"
            label="Comment (required)"
            :rules="[v => !!v || 'Comment is required']"
            rows="3"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="actionDialog = false">Cancel</v-btn>
          <v-btn
            :color="selectedAction?.color"
            :loading="actionLoading"
            @click="executeAction"
          >
            {{ selectedAction?.label }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCurationStore } from '@/stores/curations'
import { useNotifications } from '@/composables/useNotifications'
import type { CurationResponse } from '@/api/types'

interface Props {
  curation: CurationResponse
}

const props = defineProps<Props>()
const curationStore = useCurationStore()
const { showSuccess, showError } = useNotifications()

const actionDialog = ref(false)
const actionComment = ref('')
const actionLoading = ref(false)
const selectedAction = ref<any>(null)

const workflowSteps = computed(() => {
  const reviewLog = props.curation.curation_workflow?.review_log || []
  return reviewLog.map(entry => ({
    status: entry.new_status || entry.action,
    date: new Date(entry.timestamp).toLocaleDateString(),
    curator: entry.user_name || entry.user_email,
    comment: entry.comment,
    description: getStatusDescription(entry.new_status || entry.action)
  }))
})

const availableActions = computed(() => {
  const currentStatus = props.curation.curation_workflow?.status
  const actions = []
  
  switch (currentStatus) {
    case 'Automated':
      actions.push(
        { name: 'review', label: 'Start Primary Review', color: 'primary' },
        { name: 'approve', label: 'Auto-Approve', color: 'success' }
      )
      break
    case 'In_Primary_Review':
      actions.push(
        { name: 'secondary_review', label: 'Forward to Secondary Review', color: 'primary' },
        { name: 'approve', label: 'Approve', color: 'success' },
        { name: 'reject', label: 'Reject', color: 'error' }
      )
      break
    case 'In_Secondary_Review':
      actions.push(
        { name: 'approve', label: 'Approve', color: 'success' },
        { name: 'reject', label: 'Reject', color: 'error' },
        { name: 'return_primary', label: 'Return to Primary Review', color: 'warning' }
      )
      break
    case 'Approved':
      actions.push(
        { name: 'publish', label: 'Publish', color: 'success' },
        { name: 'return_review', label: 'Return for Review', color: 'warning' }
      )
      break
  }
  
  return actions
})

function getStepColor(status: string): string {
  const colors: Record<string, string> = {
    'Automated': 'grey',
    'In_Primary_Review': 'primary',
    'In_Secondary_Review': 'info',
    'Expert_Review': 'warning',
    'Approved': 'success',
    'Published': 'success',
    'Rejected': 'error'
  }
  return colors[status] || 'grey'
}

function getStepIcon(status: string): string {
  const icons: Record<string, string> = {
    'Automated': 'mdi-robot',
    'In_Primary_Review': 'mdi-account-search',
    'In_Secondary_Review': 'mdi-account-multiple-check',
    'Expert_Review': 'mdi-account-star',
    'Approved': 'mdi-check-circle',
    'Published': 'mdi-publish',
    'Rejected': 'mdi-close-circle'
  }
  return icons[status] || 'mdi-circle'
}

function getStatusDescription(status: string): string {
  const descriptions: Record<string, string> = {
    'Automated': 'Automatically generated curation',
    'In_Primary_Review': 'Under primary curator review',
    'In_Secondary_Review': 'Under secondary curator review',
    'Expert_Review': 'Under expert panel review',
    'Approved': 'Approved for publication',
    'Published': 'Published and available',
    'Rejected': 'Rejected - requires revision'
  }
  return descriptions[status] || 'Status update'
}

function showActionDialog(action: any) {
  selectedAction.value = action
  actionComment.value = ''
  actionDialog.value = true
}

async function executeAction() {
  if (!actionComment.value.trim()) return
  
  actionLoading.value = true
  try {
    await curationStore.advanceWorkflow(
      props.curation.id,
      selectedAction.value.name,
      actionComment.value
    )
    showSuccess(`Workflow action "${selectedAction.value.label}" completed successfully`)
    actionDialog.value = false
  } catch (error) {
    showError('Failed to execute workflow action')
  } finally {
    actionLoading.value = false
  }
}
</script>
```

## Development Setup

### Vite Configuration
```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'

export default defineConfig({
  plugins: [
    vue(),
    vuetify({ autoImport: true })
  ],
  resolve: {
    alias: {
      '@': new URL('./src', import.meta.url).pathname
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
```

This frontend implementation provides a sophisticated, user-friendly interface for scientific gene curation with advanced search capabilities, real-time workflow management, and comprehensive data visualization features.