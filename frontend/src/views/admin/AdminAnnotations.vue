<template>
  <v-container fluid class="pa-4">
    <AdminHeader
      title="Annotations Management"
      subtitle="Control gene annotation pipeline and manage enrichment data sources"
      back-route="/admin"
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
        <strong>Annotation System:</strong> This pipeline enriches our curated genes with additional
        data from external sources like gnomAD (constraint scores), GTEx (tissue expression), HGNC
        (official symbols), ClinVar (clinical variants), and others. This data helps researchers
        understand gene function and disease relevance.
      </div>
    </v-alert>

    <!-- Statistics Overview -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Annotated Genes"
          :value="statistics.total_genes_with_annotations"
          :loading="statsLoading"
          icon="mdi-dna"
          color="primary"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Data Sources"
          :value="annotationSources.length"
          :loading="statsLoading"
          icon="mdi-database"
          color="info"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Scheduled Jobs"
          :value="activeJobs"
          :loading="statsLoading"
          icon="mdi-clock-time-four"
          color="warning"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Full Coverage"
          :value="statistics.genes_with_both_sources"
          :loading="statsLoading"
          icon="mdi-check-all"
          color="success"
        />
      </v-col>
    </v-row>

    <!-- Pipeline Management -->
    <v-card class="mb-6">
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-pipeline</v-icon>
        Annotation Pipeline Control
      </v-card-title>
      <v-card-text>
        <div class="text-body-2 text-medium-emphasis mb-4">
          The annotation pipeline enriches genes with data from external sources. Run updates to
          pull the latest information from gnomAD, GTEx, ClinVar, and other databases.
        </div>

        <v-row>
          <v-col cols="12" md="6">
            <div class="mb-4">
              <strong>Pipeline Status:</strong>
              <v-chip
                :color="pipelineStatus.pipeline_ready ? 'success' : 'error'"
                size="small"
                class="ml-2"
              >
                {{ pipelineStatus.pipeline_ready ? 'All Sources Ready' : 'Issues Detected' }}
              </v-chip>
            </div>

            <div
              v-if="pipelineStatus.updates_due && pipelineStatus.updates_due.length > 0"
              class="mb-4"
            >
              <strong>Sources Needing Updates:</strong>
              <div class="d-flex flex-wrap ga-1 mt-1">
                <v-chip
                  v-for="source in pipelineStatus.updates_due"
                  :key="source"
                  size="small"
                  color="warning"
                  variant="tonal"
                >
                  {{ source }}
                </v-chip>
              </div>
            </div>

            <div v-else class="mb-4">
              <v-icon color="success" size="small" class="mr-1">mdi-check-circle</v-icon>
              <span class="text-body-2 text-medium-emphasis">All sources are up to date</span>
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <v-select
              v-model="pipelineForm.strategy"
              label="Update Strategy"
              :items="strategyOptions"
              density="compact"
              variant="outlined"
              hint="Incremental = update stale/missing data only | Full = update all genes | Selective = update selected sources only | Forced = full update ignoring cache"
              persistent-hint
              class="mb-3"
            />
            <v-switch
              v-model="pipelineForm.force"
              label="Force update (ignore cache TTL)"
              density="compact"
              color="warning"
              hint="Bypass cache timeouts - use for urgent updates"
              persistent-hint
            />
          </v-col>
        </v-row>

        <!-- Source Selection for SELECTIVE Strategy -->
        <v-expand-transition>
          <v-row v-if="pipelineForm.strategy === 'selective'" class="mt-4">
            <v-col cols="12">
              <v-card variant="outlined" color="primary">
                <v-card-text>
                  <div class="d-flex align-center mb-3">
                    <v-icon color="primary" size="small" class="mr-2">mdi-database-check</v-icon>
                    <span class="text-subtitle-2 font-weight-medium">Select Sources to Update</span>
                    <v-spacer />
                    <v-btn
                      variant="text"
                      size="x-small"
                      @click="pipelineForm.sources = sourceFilterOptions.map(s => s.value)"
                    >
                      Select All
                    </v-btn>
                    <v-btn variant="text" size="x-small" @click="pipelineForm.sources = []">
                      Clear All
                    </v-btn>
                  </div>
                  <v-chip-group
                    v-model="pipelineForm.sources"
                    column
                    multiple
                    filter
                    variant="outlined"
                    selected-class="text-primary"
                  >
                    <v-chip
                      v-for="source in sourceFilterOptions"
                      :key="source.value"
                      :value="source.value"
                      size="small"
                      label
                    >
                      <v-icon
                        v-if="pipelineForm.sources.includes(source.value)"
                        start
                        size="x-small"
                      >
                        mdi-check-circle
                      </v-icon>
                      {{ source.title }}
                    </v-chip>
                  </v-chip-group>
                  <div
                    v-if="pipelineForm.sources.length === 0"
                    class="text-warning text-caption mt-2"
                  >
                    <v-icon size="x-small" class="mr-1">mdi-alert</v-icon>
                    Please select at least one source to update
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-expand-transition>

        <v-divider class="my-4" />

        <!-- Main Pipeline Controls -->
        <div class="d-flex ga-2 flex-wrap mb-3">
          <v-btn
            v-if="!pipelineStatus?.status || pipelineStatus?.status !== 'running'"
            color="primary"
            variant="elevated"
            prepend-icon="mdi-rocket-launch"
            :loading="pipelineLoading"
            @click="triggerPipelineUpdate"
          >
            Run Full Update
          </v-btn>

          <v-btn
            v-else-if="pipelineStatus?.status === 'running'"
            color="warning"
            variant="elevated"
            prepend-icon="mdi-pause"
            :loading="pauseLoading"
            @click="pauseUpdate"
          >
            Pause Pipeline
          </v-btn>

          <v-btn
            v-if="pipelineStatus?.status === 'paused'"
            color="success"
            variant="elevated"
            prepend-icon="mdi-play-pause"
            :loading="resumeLoading"
            @click="resumeUpdate"
          >
            Resume Pipeline
          </v-btn>

          <v-btn
            color="info"
            variant="tonal"
            prepend-icon="mdi-check-decagram"
            :loading="pipelineLoading"
            @click="validateAnnotations"
          >
            Validate Data
          </v-btn>
          <v-btn
            color="success"
            variant="tonal"
            prepend-icon="mdi-cached"
            :loading="pipelineLoading"
            @click="refreshMaterializedView"
          >
            Refresh Cache
          </v-btn>
        </div>

        <!-- Smart Update Actions -->
        <div class="d-flex ga-2 flex-wrap">
          <v-btn
            color="error"
            variant="tonal"
            prepend-icon="mdi-alert-circle"
            :loading="failedLoading"
            :disabled="pipelineStatus?.status === 'running'"
            size="small"
            @click="updateFailed"
          >
            Retry Failed
          </v-btn>

          <v-btn
            color="info"
            variant="tonal"
            prepend-icon="mdi-new-box"
            :loading="newLoading"
            :disabled="pipelineStatus?.status === 'running'"
            size="small"
            @click="updateNew"
          >
            Update New Genes
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <!-- Gene Annotation Lookup -->
    <v-card class="mb-6">
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-file-search</v-icon>
        Test Gene Annotation Lookup
      </v-card-title>
      <v-card-text>
        <p class="text-body-2 text-medium-emphasis mb-4">
          Look up annotations for any gene in the database to verify annotation coverage and data
          quality.
        </p>

        <v-row>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="lookupGeneId"
              label="Gene Database ID"
              type="number"
              density="compact"
              variant="outlined"
              placeholder="e.g., 1, 123, 456"
              hint="Enter the internal database ID for a gene"
              persistent-hint
            />
          </v-col>
          <v-col cols="12" md="4">
            <v-select
              v-model="lookupSource"
              label="Filter by Source (optional)"
              :items="sourceFilterOptions"
              density="compact"
              variant="outlined"
              clearable
              hint="Show annotations from specific source only"
              persistent-hint
            />
          </v-col>
          <v-col cols="12" md="2">
            <v-btn
              color="primary"
              block
              :loading="lookupLoading"
              :disabled="!lookupGeneId"
              @click="lookupGeneAnnotations"
            >
              <v-icon start>mdi-magnify</v-icon>
              Lookup
            </v-btn>
          </v-col>
        </v-row>

        <v-alert v-if="lookupResult" class="mt-4" variant="tonal" color="info">
          <div class="mb-3">
            <v-icon color="success" size="small" class="mr-1">mdi-dna</v-icon>
            <strong>Gene:</strong> {{ lookupResult.gene?.symbol }} ({{
              lookupResult.gene?.hgnc_id
            }})
          </div>

          <div class="mb-3">
            <v-icon color="info" size="small" class="mr-1">mdi-database</v-icon>
            <strong>Annotation Coverage:</strong>
            {{ Object.keys(lookupResult.annotations || {}).length }} data sources
          </div>

          <div v-if="Object.keys(lookupResult.annotations || {}).length > 0">
            <strong>Available Annotations:</strong>
            <div class="d-flex flex-wrap ga-1 mt-2">
              <v-chip
                v-for="source in Object.keys(lookupResult.annotations || {})"
                :key="source"
                size="small"
                color="primary"
                variant="tonal"
              >
                <v-icon start size="x-small">mdi-check</v-icon>
                {{ source.toUpperCase() }} ({{ lookupResult.annotations[source].length }} records)
              </v-chip>
            </div>
          </div>

          <div v-else class="mt-2">
            <v-icon color="warning" size="small" class="mr-1">mdi-alert</v-icon>
            <span class="text-body-2">No annotations found for this gene</span>
          </div>
        </v-alert>
      </v-card-text>
    </v-card>

    <!-- Annotation Sources -->
    <v-card class="mb-6">
      <v-card-title class="d-flex align-center justify-space-between">
        <div class="d-flex align-center">
          <v-icon class="mr-2">mdi-database-sync</v-icon>
          Annotation Sources ({{ annotationSources.length }})
        </div>
      </v-card-title>

      <v-data-table
        :headers="sourcesHeaders"
        :items="annotationSources"
        :loading="loading"
        density="compact"
        class="elevation-0"
      >
        <template #item.source_name="{ item }">
          <div class="d-flex align-center">
            <v-icon
              :color="item.is_active ? 'success' : 'error'"
              :icon="item.is_active ? 'mdi-check-circle' : 'mdi-close-circle'"
              size="small"
              class="mr-2"
            />
            <strong>{{ item.display_name || item.source_name }}</strong>
          </div>
        </template>

        <template #item.description="{ item }">
          <span class="text-caption">{{ item.description || 'No description' }}</span>
        </template>

        <template #item.last_update="{ item }">
          <span class="text-caption">
            {{ item.last_update ? formatDate(item.last_update) : 'Never' }}
          </span>
        </template>

        <template #item.next_update="{ item }">
          <span class="text-caption">
            {{ item.next_update ? formatDate(item.next_update) : 'Not scheduled' }}
          </span>
        </template>

        <template #item.update_frequency="{ item }">
          <v-chip size="small" variant="outlined">
            {{ item.update_frequency || 'Manual' }}
          </v-chip>
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex ga-1">
            <v-btn
              icon="mdi-play"
              size="small"
              color="primary"
              variant="text"
              :loading="sourceUpdateLoading[item.source_name]"
              @click="updateSource(item.source_name)"
            />
            <v-btn
              icon="mdi-information"
              size="small"
              color="info"
              variant="text"
              @click="showSourceDetails(item)"
            />
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Scheduled Jobs -->
    <v-card class="mb-6">
      <v-card-title class="d-flex align-center justify-space-between">
        <div class="d-flex align-center">
          <v-icon class="mr-2">mdi-clock-outline</v-icon>
          Scheduled Jobs
          <v-chip
            :color="schedulerInfo.scheduler_running ? 'success' : 'error'"
            size="small"
            class="ml-2"
          >
            {{ schedulerInfo.scheduler_running ? 'Running' : 'Stopped' }}
          </v-chip>
        </div>
        <v-btn
          size="small"
          prepend-icon="mdi-refresh"
          :loading="jobsLoading"
          @click="loadScheduledJobs"
        >
          Refresh Jobs
        </v-btn>
      </v-card-title>

      <v-data-table
        :headers="jobsHeaders"
        :items="scheduledJobs"
        :loading="jobsLoading"
        density="compact"
        class="elevation-0"
      >
        <template #item.id="{ item }">
          <code class="text-caption">{{ item.id }}</code>
        </template>

        <template #item.next_run="{ item }">
          <span class="text-caption">
            {{ item.next_run ? formatDate(item.next_run) : 'Not scheduled' }}
          </span>
        </template>

        <template #item.trigger="{ item }">
          <span class="text-caption">{{ item.trigger || 'Unknown' }}</span>
        </template>

        <template #item.actions="{ item }">
          <v-btn
            icon="mdi-play"
            size="small"
            color="primary"
            variant="text"
            :loading="jobTriggerLoading[item.id]"
            @click="triggerJob(item.id)"
          />
        </template>
      </v-data-table>
    </v-card>

    <!-- Source Details Dialog -->
    <v-dialog v-model="sourceDetailsDialog" max-width="700">
      <v-card v-if="selectedSource">
        <v-card-title
          >{{ selectedSource.display_name || selectedSource.source_name }} Details</v-card-title
        >
        <v-card-text>
          <v-row>
            <v-col cols="12" md="6">
              <div class="mb-3"><strong>Source Name:</strong> {{ selectedSource.source_name }}</div>
              <div class="mb-3">
                <strong>Display Name:</strong> {{ selectedSource.display_name || 'N/A' }}
              </div>
              <div class="mb-3">
                <strong>Active:</strong>
                <v-chip size="small" :color="selectedSource.is_active ? 'success' : 'error'">
                  {{ selectedSource.is_active ? 'Yes' : 'No' }}
                </v-chip>
              </div>
              <div class="mb-3">
                <strong>Update Frequency:</strong> {{ selectedSource.update_frequency || 'Manual' }}
              </div>
            </v-col>
            <v-col cols="12" md="6">
              <div class="mb-3">
                <strong>Last Update:</strong>
                {{ selectedSource.last_update ? formatDate(selectedSource.last_update) : 'Never' }}
              </div>
              <div class="mb-3">
                <strong>Next Update:</strong>
                {{
                  selectedSource.next_update
                    ? formatDate(selectedSource.next_update)
                    : 'Not scheduled'
                }}
              </div>
            </v-col>
          </v-row>

          <div class="mb-3">
            <strong>Description:</strong><br />
            <span class="text-body-2">{{
              selectedSource.description || 'No description available'
            }}</span>
          </div>

          <div v-if="selectedSource.config" class="mb-3">
            <strong>Configuration:</strong>
            <v-card variant="outlined" class="mt-2">
              <v-card-text>
                <pre class="text-caption">{{ JSON.stringify(selectedSource.config, null, 2) }}</pre>
              </v-card-text>
            </v-card>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="sourceDetailsDialog = false">Close</v-btn>
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
import * as annotationsApi from '@/api/admin/annotations'

// Reactive data
const loading = ref(false)
const statsLoading = ref(false)
const pipelineLoading = ref(false)
const lookupLoading = ref(false)
const jobsLoading = ref(false)
const sourceUpdateLoading = reactive({})
const jobTriggerLoading = reactive({})
const pauseLoading = ref(false)
const resumeLoading = ref(false)
const failedLoading = ref(false)
const newLoading = ref(false)

// Data
const statistics = reactive({
  total_genes_with_annotations: 0,
  genes_with_both_sources: 0,
  sources: []
})

const annotationSources = ref([])
const pipelineStatus = reactive({
  sources: [],
  pipeline_ready: false,
  updates_due: []
})

const schedulerInfo = reactive({
  scheduler_running: false,
  jobs: [],
  total_jobs: 0
})

const scheduledJobs = ref([])

// Forms and inputs
const pipelineForm = reactive({
  strategy: 'incremental',
  sources: [],
  geneIds: [],
  force: false
})

const lookupGeneId = ref('')
const lookupSource = ref(null)
const lookupResult = ref(null)

// Dialogs
const sourceDetailsDialog = ref(false)
const selectedSource = ref(null)

// Snackbar
const snackbar = reactive({
  show: false,
  message: '',
  color: 'info'
})

// Computed
const activeJobs = computed(() => {
  return scheduledJobs.value.length
})

const strategyOptions = [
  { title: 'Incremental', value: 'incremental' },
  { title: 'Full', value: 'full' },
  { title: 'Forced', value: 'forced' },
  { title: 'Selective', value: 'selective' }
]

const sourceFilterOptions = computed(() => {
  const sources = ['hgnc', 'gnomad', 'gtex', 'hpo', 'clinvar', 'string_ppi', 'descartes', 'mpo_mgi']
  return sources.map(source => ({ title: source.toUpperCase(), value: source }))
})

// Table headers
const sourcesHeaders = [
  { title: 'Source', key: 'source_name', width: '200px' },
  { title: 'Description', key: 'description', width: '300px' },
  { title: 'Last Update', key: 'last_update', width: '150px' },
  { title: 'Next Update', key: 'next_update', width: '150px' },
  { title: 'Frequency', key: 'update_frequency', width: '120px' },
  { title: 'Actions', key: 'actions', sortable: false, width: '100px' }
]

const jobsHeaders = [
  { title: 'Job ID', key: 'id', width: '200px' },
  { title: 'Name', key: 'name', width: '200px' },
  { title: 'Next Run', key: 'next_run', width: '150px' },
  { title: 'Trigger', key: 'trigger', width: '150px' },
  { title: 'Actions', key: 'actions', sortable: false, width: '100px' }
]

// Methods
const showSnackbar = (message, color = 'info') => {
  snackbar.message = message
  snackbar.color = color
  snackbar.show = true
}

const loadStatistics = async () => {
  statsLoading.value = true
  try {
    const response = await annotationsApi.getAnnotationStatistics()
    Object.assign(statistics, response.data)
  } catch (error) {
    window.logService.error('Failed to load statistics:', error)
    showSnackbar('Failed to load annotation statistics', 'error')
  } finally {
    statsLoading.value = false
  }
}

const loadAnnotationSources = async () => {
  try {
    const response = await annotationsApi.getAnnotationSources()
    annotationSources.value = response.data
  } catch (error) {
    window.logService.error('Failed to load annotation sources:', error)
    showSnackbar('Failed to load annotation sources', 'error')
  }
}

const loadPipelineStatus = async () => {
  try {
    const response = await annotationsApi.getPipelineStatus()
    Object.assign(pipelineStatus, response.data)
  } catch (error) {
    window.logService.error('Failed to load pipeline status:', error)
    showSnackbar('Failed to load pipeline status', 'error')
  }
}

const loadScheduledJobs = async () => {
  jobsLoading.value = true
  try {
    const response = await annotationsApi.getScheduledJobs()
    Object.assign(schedulerInfo, response.data)
    scheduledJobs.value = response.data.jobs || []
  } catch (error) {
    window.logService.error('Failed to load scheduled jobs:', error)
    showSnackbar('Failed to load scheduled jobs', 'error')
  } finally {
    jobsLoading.value = false
  }
}

const loadData = async () => {
  loading.value = true
  try {
    await Promise.all([
      loadStatistics(),
      loadAnnotationSources(),
      loadPipelineStatus(),
      loadScheduledJobs()
    ])
  } finally {
    loading.value = false
  }
}

const triggerPipelineUpdate = async () => {
  // Validate SELECTIVE strategy has sources selected
  if (pipelineForm.strategy === 'selective' && pipelineForm.sources.length === 0) {
    showSnackbar('Please select at least one source for selective update', 'warning')
    return
  }

  pipelineLoading.value = true
  try {
    const response = await annotationsApi.triggerPipelineUpdate(pipelineForm)
    showSnackbar(`Pipeline update scheduled: ${response.data.task_id}`, 'success')
    await loadPipelineStatus()
  } catch (error) {
    window.logService.error('Failed to trigger pipeline update:', error)
    showSnackbar('Failed to trigger pipeline update', 'error')
  } finally {
    pipelineLoading.value = false
  }
}

const validateAnnotations = async () => {
  pipelineLoading.value = true
  try {
    const response = await annotationsApi.validateAnnotations()
    showSnackbar('Validation completed', 'success')
    window.logService.info('Validation results:', response.data)
  } catch (error) {
    window.logService.error('Failed to validate annotations:', error)
    showSnackbar('Failed to validate annotations', 'error')
  } finally {
    pipelineLoading.value = false
  }
}

const refreshMaterializedView = async () => {
  pipelineLoading.value = true
  try {
    const response = await annotationsApi.refreshMaterializedView()
    showSnackbar(response.data.message, 'success')
  } catch (error) {
    window.logService.error('Failed to refresh materialized view:', error)
    showSnackbar('Failed to refresh materialized view', 'error')
  } finally {
    pipelineLoading.value = false
  }
}

const lookupGeneAnnotations = async () => {
  if (!lookupGeneId.value) return

  lookupLoading.value = true
  lookupResult.value = null

  try {
    const response = await annotationsApi.getGeneAnnotations(
      parseInt(lookupGeneId.value),
      lookupSource.value
    )
    lookupResult.value = response.data
  } catch (error) {
    window.logService.error('Failed to lookup gene annotations:', error)
    if (error.response?.status === 404) {
      showSnackbar('Gene not found', 'error')
    } else {
      showSnackbar('Failed to lookup gene annotations', 'error')
    }
  } finally {
    lookupLoading.value = false
  }
}

const updateSource = async sourceName => {
  sourceUpdateLoading[sourceName] = true
  try {
    // Use the new update-missing endpoint for source-specific updates
    const response = await annotationsApi.updateMissingForSource(sourceName)
    showSnackbar(
      `Updating ${response.data.count} genes missing ${sourceName} annotations`,
      'success'
    )
    await loadStatistics()
  } catch (error) {
    window.logService.error(`Failed to update source ${sourceName}:`, error)
    showSnackbar(`Failed to update source ${sourceName}`, 'error')
  } finally {
    sourceUpdateLoading[sourceName] = false
  }
}

const pauseUpdate = async () => {
  pauseLoading.value = true
  try {
    await annotationsApi.pausePipeline()
    showSnackbar('Pipeline paused successfully', 'success')
    await loadPipelineStatus()
  } catch (error) {
    window.logService.error('Failed to pause pipeline:', error)
    showSnackbar(`Error pausing pipeline: ${error.message}`, 'error')
  } finally {
    pauseLoading.value = false
  }
}

const resumeUpdate = async () => {
  resumeLoading.value = true
  try {
    await annotationsApi.resumePipeline()
    showSnackbar('Pipeline resumed successfully', 'success')
    await loadPipelineStatus()
  } catch (error) {
    window.logService.error('Failed to resume pipeline:', error)
    showSnackbar(`Error resuming pipeline: ${error.message}`, 'error')
  } finally {
    resumeLoading.value = false
  }
}

const updateFailed = async () => {
  failedLoading.value = true
  try {
    const response = await annotationsApi.updateFailedGenes()
    showSnackbar(`Retrying ${response.data.count} failed genes`, 'info')
    await loadPipelineStatus()
  } catch (error) {
    window.logService.error('Failed to update failed genes:', error)
    showSnackbar(`Error updating failed genes: ${error.message}`, 'error')
  } finally {
    failedLoading.value = false
  }
}

const updateNew = async () => {
  newLoading.value = true
  try {
    const response = await annotationsApi.updateNewGenes()
    showSnackbar(`Processing ${response.data.count} new genes`, 'info')
    await loadPipelineStatus()
  } catch (error) {
    window.logService.error('Failed to update new genes:', error)
    showSnackbar(`Error updating new genes: ${error.message}`, 'error')
  } finally {
    newLoading.value = false
  }
}

const showSourceDetails = source => {
  selectedSource.value = source
  sourceDetailsDialog.value = true
}

const triggerJob = async jobId => {
  jobTriggerLoading[jobId] = true
  try {
    const response = await annotationsApi.triggerScheduledJob(jobId)
    showSnackbar(response.data.message, 'success')
    await loadScheduledJobs()
  } catch (error) {
    window.logService.error(`Failed to trigger job ${jobId}:`, error)
    showSnackbar(`Failed to trigger job ${jobId}`, 'error')
  } finally {
    jobTriggerLoading[jobId] = false
  }
}

// Utility methods
const formatDate = dateString => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString()
}

// Load data on mount
onMounted(() => {
  loadData()
})
</script>
