<template>
  <div class="container mx-auto px-4 py-6">
    <AdminHeader
      title="Annotations Management"
      subtitle="Control gene annotation pipeline and manage enrichment data sources"
      :icon="Tags"
      icon-color="teal"
      :breadcrumbs="ADMIN_BREADCRUMBS.annotations"
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
        <strong>Annotation System:</strong> This pipeline enriches our curated genes with additional
        data from external sources like gnomAD (constraint scores), GTEx (tissue expression), HGNC
        (official symbols), ClinVar (clinical variants), and others. This data helps researchers
        understand gene function and disease relevance.
      </AlertDescription>
    </Alert>

    <!-- Statistics Overview -->
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <AdminStatsCard
        title="Annotated Genes"
        :value="statistics.total_genes_with_annotations"
        :loading="statsLoading"
        icon="mdi-dna"
        color="primary"
      />
      <AdminStatsCard
        title="Data Sources"
        :value="annotationSources.length"
        :loading="statsLoading"
        icon="mdi-database"
        color="info"
      />
      <AdminStatsCard
        title="Scheduled Jobs"
        :value="activeJobs"
        :loading="statsLoading"
        icon="mdi-clock-time-four"
        color="warning"
      />
      <AdminStatsCard
        title="Full Coverage"
        :value="statistics.genes_with_both_sources"
        :loading="statsLoading"
        icon="mdi-check-all"
        color="success"
      />
    </div>

    <!-- Pipeline Management -->
    <Card class="mb-6">
      <CardHeader>
        <CardTitle class="flex items-center">
          <Workflow class="size-5 mr-2" />
          Annotation Pipeline Control
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p class="text-sm text-muted-foreground mb-4">
          The annotation pipeline enriches genes with data from external sources. Run updates to
          pull the latest information from gnomAD, GTEx, ClinVar, and other databases.
        </p>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div class="mb-4">
              <span class="font-semibold">Pipeline Status:</span>
              <Badge
                :variant="pipelineStatus.pipeline_ready ? 'default' : 'destructive'"
                class="ml-2"
              >
                {{ pipelineStatus.pipeline_ready ? 'All Sources Ready' : 'Issues Detected' }}
              </Badge>
            </div>

            <div
              v-if="pipelineStatus.updates_due && pipelineStatus.updates_due.length > 0"
              class="mb-4"
            >
              <span class="font-semibold">Sources Needing Updates:</span>
              <div class="flex flex-wrap gap-1 mt-1">
                <Badge
                  v-for="source in pipelineStatus.updates_due"
                  :key="source"
                  variant="outline"
                  class="bg-yellow-50 text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300"
                >
                  {{ source }}
                </Badge>
              </div>
            </div>

            <div v-else class="mb-4">
              <CircleCheck class="size-4 text-green-600 dark:text-green-400 mr-1 inline-block" />
              <span class="text-sm text-muted-foreground">All sources are up to date</span>
            </div>
          </div>
          <div class="space-y-4">
            <div class="space-y-2">
              <Label>Update Strategy</Label>
              <Select v-model="pipelineForm.strategy">
                <SelectTrigger>
                  <SelectValue placeholder="Select strategy" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="option in strategyOptions"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.title }}
                  </SelectItem>
                </SelectContent>
              </Select>
              <p class="text-xs text-muted-foreground">
                Incremental = update stale/missing data only | Full = update all genes | Selective =
                update selected sources only | Forced = full update ignoring cache
              </p>
            </div>
            <div class="flex items-center gap-2">
              <Switch :checked="pipelineForm.force" @update:checked="pipelineForm.force = $event" />
              <Label>Force update (ignore cache TTL)</Label>
            </div>
            <p class="text-xs text-muted-foreground">
              Bypass cache timeouts - use for urgent updates
            </p>
          </div>
        </div>

        <!-- Source Selection for SELECTIVE Strategy -->
        <Collapsible :open="pipelineForm.strategy === 'selective'">
          <CollapsibleContent>
            <Card class="mt-4 border-primary">
              <CardContent class="pt-4">
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center">
                    <DatabaseZap class="size-4 text-primary mr-2 inline-block" />
                    <span class="text-sm font-medium">Select Sources to Update</span>
                  </div>
                  <div class="flex gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      @click="pipelineForm.sources = sourceFilterOptions.map(s => s.value)"
                    >
                      Select All
                    </Button>
                    <Button variant="ghost" size="sm" @click="pipelineForm.sources = []">
                      Clear All
                    </Button>
                  </div>
                </div>
                <div class="flex flex-wrap gap-2 p-3 rounded-md border">
                  <Badge
                    v-for="source in sourceFilterOptions"
                    :key="source.value"
                    :variant="pipelineForm.sources.includes(source.value) ? 'default' : 'outline'"
                    class="cursor-pointer"
                    @click="toggleSource(source.value)"
                  >
                    <CircleCheck
                      v-if="pipelineForm.sources.includes(source.value)"
                      class="size-3 mr-1"
                    />
                    {{ source.title }}
                  </Badge>
                </div>
                <div
                  v-if="pipelineForm.sources.length === 0"
                  class="text-yellow-600 dark:text-yellow-400 text-xs mt-2"
                >
                  <AlertTriangle class="size-3 mr-1 inline-block" />
                  Please select at least one source to update
                </div>
              </CardContent>
            </Card>
          </CollapsibleContent>
        </Collapsible>

        <Separator class="my-4" />

        <!-- Main Pipeline Controls -->
        <div class="flex gap-2 flex-wrap mb-3">
          <Button
            v-if="!pipelineStatus?.status || pipelineStatus?.status !== 'running'"
            :disabled="pipelineLoading"
            @click="triggerPipelineUpdate"
          >
            <Rocket class="size-4 mr-2" />
            {{ pipelineLoading ? 'Running...' : 'Run Full Update' }}
          </Button>

          <Button
            v-else-if="pipelineStatus?.status === 'running'"
            variant="outline"
            class="border-yellow-500 text-yellow-600"
            :disabled="pauseLoading"
            @click="pauseUpdate"
          >
            <Pause class="size-4 mr-2" />
            {{ pauseLoading ? 'Pausing...' : 'Pause Pipeline' }}
          </Button>

          <Button
            v-if="pipelineStatus?.status === 'paused'"
            variant="outline"
            class="border-green-500 text-green-600"
            :disabled="resumeLoading"
            @click="resumeUpdate"
          >
            <Play class="size-4 mr-2" />
            {{ resumeLoading ? 'Resuming...' : 'Resume Pipeline' }}
          </Button>

          <Button variant="secondary" :disabled="pipelineLoading" @click="validateAnnotations">
            <BadgeCheck class="size-4 mr-2" />
            Validate Data
          </Button>
          <Button variant="secondary" :disabled="pipelineLoading" @click="refreshMaterializedView">
            <RefreshCw class="size-4 mr-2" />
            Refresh Cache
          </Button>
        </div>

        <!-- Smart Update Actions -->
        <div class="flex gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            class="border-red-300 text-red-600 dark:border-red-700 dark:text-red-400"
            :disabled="failedLoading || pipelineStatus?.status === 'running'"
            @click="updateFailed"
          >
            <CircleAlert class="size-4 mr-2" />
            {{ failedLoading ? 'Retrying...' : 'Retry Failed' }}
          </Button>

          <Button
            variant="outline"
            size="sm"
            :disabled="newLoading || pipelineStatus?.status === 'running'"
            @click="updateNew"
          >
            <SquarePlus class="size-4 mr-2" />
            {{ newLoading ? 'Updating...' : 'Update New Genes' }}
          </Button>
        </div>
      </CardContent>
    </Card>

    <!-- Gene Annotation Lookup -->
    <Card class="mb-6">
      <CardHeader>
        <CardTitle class="flex items-center">
          <FileSearch class="size-5 mr-2" />
          Test Gene Annotation Lookup
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p class="text-sm text-muted-foreground mb-4">
          Look up annotations for any gene in the database to verify annotation coverage and data
          quality.
        </p>

        <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
          <div class="md:col-span-6 space-y-2">
            <Label>Gene Database ID</Label>
            <Input v-model="lookupGeneId" type="number" placeholder="e.g., 1, 123, 456" />
            <p class="text-xs text-muted-foreground">Enter the internal database ID for a gene</p>
          </div>
          <div class="md:col-span-4 space-y-2">
            <Label>Filter by Source (optional)</Label>
            <Select v-model="lookupSource">
              <SelectTrigger>
                <SelectValue placeholder="All sources" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All sources</SelectItem>
                <SelectItem v-for="src in sourceFilterOptions" :key="src.value" :value="src.value">
                  {{ src.title }}
                </SelectItem>
              </SelectContent>
            </Select>
            <p class="text-xs text-muted-foreground">Show annotations from specific source only</p>
          </div>
          <div class="md:col-span-2 flex items-end">
            <Button
              class="w-full"
              :disabled="lookupLoading || !lookupGeneId"
              @click="lookupGeneAnnotations"
            >
              <Search class="size-4 mr-1" />
              Lookup
            </Button>
          </div>
        </div>

        <Alert v-if="lookupResult" class="mt-4">
          <AlertDescription>
            <div class="mb-3">
              <Dna class="size-4 text-green-600 dark:text-green-400 mr-1 inline-block" />
              <strong>Gene:</strong> {{ lookupResult.gene?.symbol }} ({{
                lookupResult.gene?.hgnc_id
              }})
            </div>

            <div class="mb-3">
              <Database class="size-4 text-blue-600 dark:text-blue-400 mr-1 inline-block" />
              <strong>Annotation Coverage:</strong>
              {{ Object.keys(lookupResult.annotations || {}).length }} data sources
            </div>

            <div v-if="Object.keys(lookupResult.annotations || {}).length > 0">
              <strong>Available Annotations:</strong>
              <div class="flex flex-wrap gap-1 mt-2">
                <Badge
                  v-for="source in Object.keys(lookupResult.annotations || {})"
                  :key="source"
                  variant="secondary"
                >
                  <Check class="size-3 mr-1 inline-block" />
                  {{ source.toUpperCase() }} ({{ lookupResult.annotations[source].length }} records)
                </Badge>
              </div>
            </div>

            <div v-else class="mt-2">
              <AlertTriangle
                class="size-4 text-yellow-600 dark:text-yellow-400 mr-1 inline-block"
              />
              <span class="text-sm">No annotations found for this gene</span>
            </div>
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>

    <!-- Annotation Sources -->
    <Card class="mb-6">
      <CardHeader>
        <CardTitle class="flex items-center">
          <RefreshCw class="size-5 mr-2" />
          Annotation Sources ({{ annotationSources.length }})
        </CardTitle>
      </CardHeader>
      <CardContent class="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead class="w-[200px]">Source</TableHead>
              <TableHead class="w-[300px]">Description</TableHead>
              <TableHead class="w-[150px]">Last Update</TableHead>
              <TableHead class="w-[150px]">Next Update</TableHead>
              <TableHead class="w-[120px]">Frequency</TableHead>
              <TableHead class="w-[100px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-if="loading">
              <TableCell colspan="6" class="text-center py-8 text-muted-foreground">
                Loading...
              </TableCell>
            </TableRow>
            <TableRow v-else-if="annotationSources.length === 0">
              <TableCell colspan="6" class="text-center py-8 text-muted-foreground">
                No annotation sources found
              </TableCell>
            </TableRow>
            <TableRow v-for="item in annotationSources" :key="item.source_name">
              <TableCell>
                <div class="flex items-center">
                  <component
                    :is="item.is_active ? CircleCheck : CircleX"
                    class="size-4 mr-2"
                    :class="
                      item.is_active ? 'text-green-600 dark:text-green-400' : 'text-destructive'
                    "
                  />
                  <strong>{{ item.display_name || item.source_name }}</strong>
                </div>
              </TableCell>
              <TableCell>
                <span class="text-xs text-muted-foreground">{{
                  item.description || 'No description'
                }}</span>
              </TableCell>
              <TableCell>
                <span class="text-xs">
                  {{ item.last_update ? formatDate(item.last_update) : 'Never' }}
                </span>
              </TableCell>
              <TableCell>
                <span class="text-xs">
                  {{ item.next_update ? formatDate(item.next_update) : 'Not scheduled' }}
                </span>
              </TableCell>
              <TableCell>
                <Badge variant="outline">
                  {{ item.update_frequency || 'Manual' }}
                </Badge>
              </TableCell>
              <TableCell>
                <div class="flex gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    class="h-8 w-8"
                    :disabled="sourceUpdateLoading[item.source_name]"
                    @click="updateSource(item.source_name)"
                  >
                    <Play class="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    class="h-8 w-8"
                    @click="showSourceDetails(item)"
                  >
                    <Info class="size-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>

    <!-- Real-time Progress Monitor -->
    <DataSourceProgress class="mb-6" />

    <!-- Scheduled Jobs -->
    <Card class="mb-6">
      <CardHeader class="flex flex-row items-center justify-between">
        <CardTitle class="flex items-center">
          <Clock class="size-5 mr-2" />
          Scheduled Jobs
          <Badge
            :variant="schedulerInfo.scheduler_running ? 'default' : 'destructive'"
            class="ml-2"
          >
            {{ schedulerInfo.scheduler_running ? 'Running' : 'Stopped' }}
          </Badge>
        </CardTitle>
        <Button variant="outline" size="sm" :disabled="jobsLoading" @click="loadScheduledJobs">
          <RefreshCw class="size-4 mr-2" :class="{ 'animate-spin': jobsLoading }" />
          Refresh Jobs
        </Button>
      </CardHeader>
      <CardContent class="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead class="w-[200px]">Job ID</TableHead>
              <TableHead class="w-[200px]">Name</TableHead>
              <TableHead class="w-[150px]">Next Run</TableHead>
              <TableHead class="w-[150px]">Trigger</TableHead>
              <TableHead class="w-[100px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-if="jobsLoading">
              <TableCell colspan="5" class="text-center py-8 text-muted-foreground">
                Loading...
              </TableCell>
            </TableRow>
            <TableRow v-else-if="scheduledJobs.length === 0">
              <TableCell colspan="5" class="text-center py-8 text-muted-foreground">
                No scheduled jobs
              </TableCell>
            </TableRow>
            <TableRow v-for="item in scheduledJobs" :key="item.id">
              <TableCell>
                <code class="text-xs">{{ item.id }}</code>
              </TableCell>
              <TableCell>{{ item.name }}</TableCell>
              <TableCell>
                <span class="text-xs">
                  {{ item.next_run ? formatDate(item.next_run) : 'Not scheduled' }}
                </span>
              </TableCell>
              <TableCell>
                <span class="text-xs">{{ item.trigger || 'Unknown' }}</span>
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="icon"
                  class="h-8 w-8"
                  :disabled="jobTriggerLoading[item.id]"
                  @click="triggerJob(item.id)"
                >
                  <Play class="size-4" />
                </Button>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>

    <!-- Source Details Dialog -->
    <Dialog v-model:open="sourceDetailsDialog">
      <DialogContent class="max-w-[700px]">
        <DialogHeader>
          <DialogTitle>
            {{ selectedSource?.display_name || selectedSource?.source_name }} Details
          </DialogTitle>
        </DialogHeader>
        <div v-if="selectedSource" class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="space-y-3">
              <div><strong>Source Name:</strong> {{ selectedSource.source_name }}</div>
              <div><strong>Display Name:</strong> {{ selectedSource.display_name || 'N/A' }}</div>
              <div>
                <strong>Active:</strong>
                <Badge :variant="selectedSource.is_active ? 'default' : 'destructive'" class="ml-1">
                  {{ selectedSource.is_active ? 'Yes' : 'No' }}
                </Badge>
              </div>
              <div>
                <strong>Update Frequency:</strong> {{ selectedSource.update_frequency || 'Manual' }}
              </div>
            </div>
            <div class="space-y-3">
              <div>
                <strong>Last Update:</strong>
                {{ selectedSource.last_update ? formatDate(selectedSource.last_update) : 'Never' }}
              </div>
              <div>
                <strong>Next Update:</strong>
                {{
                  selectedSource.next_update
                    ? formatDate(selectedSource.next_update)
                    : 'Not scheduled'
                }}
              </div>
            </div>
          </div>

          <div>
            <strong>Description:</strong><br />
            <span class="text-sm">{{
              selectedSource.description || 'No description available'
            }}</span>
          </div>

          <div v-if="selectedSource.config">
            <strong>Configuration:</strong>
            <div class="mt-2 rounded-md border p-3">
              <pre class="text-xs overflow-x-auto">{{
                JSON.stringify(selectedSource.config, null, 2)
              }}</pre>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="sourceDetailsDialog = false">Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import DataSourceProgress from '@/components/DataSourceProgress.vue'
import * as annotationsApi from '@/api/admin/annotations'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'
import { toast } from 'vue-sonner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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
import { Collapsible, CollapsibleContent } from '@/components/ui/collapsible'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
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
  BadgeCheck,
  Check,
  CircleAlert,
  CircleCheck,
  CircleX,
  Clock,
  Database,
  DatabaseZap,
  Dna,
  FileSearch,
  Info,
  Pause,
  Play,
  RefreshCw,
  Rocket,
  Search,
  SquarePlus,
  Tags,
  Workflow
} from 'lucide-vue-next'

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
  const sources = [
    'hgnc',
    'gnomad',
    'gtex',
    'hpo',
    'clinvar',
    'string_ppi',
    'descartes',
    'mpo_mgi',
    'ensembl',
    'uniprot'
  ]
  return sources.map(source => ({ title: source.toUpperCase(), value: source }))
})

// Toggle source selection for selective strategy
const toggleSource = sourceValue => {
  const idx = pipelineForm.sources.indexOf(sourceValue)
  if (idx >= 0) {
    pipelineForm.sources.splice(idx, 1)
  } else {
    pipelineForm.sources.push(sourceValue)
  }
}

// Methods
const loadStatistics = async () => {
  statsLoading.value = true
  try {
    const response = await annotationsApi.getAnnotationStatistics()
    Object.assign(statistics, response.data)
  } catch (error) {
    window.logService.error('Failed to load statistics:', error)
    toast.error('Failed to load annotation statistics', { duration: Infinity })
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
    toast.error('Failed to load annotation sources', { duration: Infinity })
  }
}

const loadPipelineStatus = async () => {
  try {
    const response = await annotationsApi.getPipelineStatus()
    Object.assign(pipelineStatus, response.data)
  } catch (error) {
    window.logService.error('Failed to load pipeline status:', error)
    toast.error('Failed to load pipeline status', { duration: Infinity })
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
    toast.error('Failed to load scheduled jobs', { duration: Infinity })
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
    toast.warning('Please select at least one source for selective update', { duration: 5000 })
    return
  }

  pipelineLoading.value = true
  try {
    const response = await annotationsApi.triggerPipelineUpdate(pipelineForm)
    toast.success(`Pipeline update scheduled: ${response.data.task_id}`, { duration: 5000 })
    await loadPipelineStatus()
  } catch (error) {
    window.logService.error('Failed to trigger pipeline update:', error)
    toast.error('Failed to trigger pipeline update', { duration: Infinity })
  } finally {
    pipelineLoading.value = false
  }
}

const validateAnnotations = async () => {
  pipelineLoading.value = true
  try {
    const response = await annotationsApi.validateAnnotations()
    toast.success('Validation completed', { duration: 5000 })
    window.logService.info('Validation results:', response.data)
  } catch (error) {
    window.logService.error('Failed to validate annotations:', error)
    toast.error('Failed to validate annotations', { duration: Infinity })
  } finally {
    pipelineLoading.value = false
  }
}

const refreshMaterializedView = async () => {
  pipelineLoading.value = true
  try {
    const response = await annotationsApi.refreshMaterializedView()
    toast.success(response.data.message, { duration: 5000 })
  } catch (error) {
    window.logService.error('Failed to refresh materialized view:', error)
    toast.error('Failed to refresh materialized view', { duration: Infinity })
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
      toast.error('Gene not found', { duration: Infinity })
    } else {
      toast.error('Failed to lookup gene annotations', { duration: Infinity })
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
    toast.success(`Updating ${response.data.count} genes missing ${sourceName} annotations`, {
      duration: 5000
    })
    await loadStatistics()
  } catch (error) {
    window.logService.error(`Failed to update source ${sourceName}:`, error)
    toast.error(`Failed to update source ${sourceName}`, { duration: Infinity })
  } finally {
    sourceUpdateLoading[sourceName] = false
  }
}

const pauseUpdate = async () => {
  pauseLoading.value = true
  try {
    await annotationsApi.pausePipeline()
    toast.success('Pipeline paused successfully', { duration: 5000 })
    await loadPipelineStatus()
  } catch (error) {
    window.logService.error('Failed to pause pipeline:', error)
    toast.error(`Error pausing pipeline: ${error.message}`, { duration: Infinity })
  } finally {
    pauseLoading.value = false
  }
}

const resumeUpdate = async () => {
  resumeLoading.value = true
  try {
    await annotationsApi.resumePipeline()
    toast.success('Pipeline resumed successfully', { duration: 5000 })
    await loadPipelineStatus()
  } catch (error) {
    window.logService.error('Failed to resume pipeline:', error)
    toast.error(`Error resuming pipeline: ${error.message}`, { duration: Infinity })
  } finally {
    resumeLoading.value = false
  }
}

const updateFailed = async () => {
  failedLoading.value = true
  try {
    const response = await annotationsApi.updateFailedGenes()
    toast.info(`Retrying ${response.data.count} failed genes`, { duration: 5000 })
    await loadPipelineStatus()
  } catch (error) {
    window.logService.error('Failed to update failed genes:', error)
    toast.error(`Error updating failed genes: ${error.message}`, { duration: Infinity })
  } finally {
    failedLoading.value = false
  }
}

const updateNew = async () => {
  newLoading.value = true
  try {
    const response = await annotationsApi.updateNewGenes()
    toast.info(`Processing ${response.data.count} new genes`, { duration: 5000 })
    await loadPipelineStatus()
  } catch (error) {
    window.logService.error('Failed to update new genes:', error)
    toast.error(`Error updating new genes: ${error.message}`, { duration: Infinity })
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
    toast.success(response.data.message, { duration: 5000 })
    await loadScheduledJobs()
  } catch (error) {
    window.logService.error(`Failed to trigger job ${jobId}:`, error)
    toast.error(`Failed to trigger job ${jobId}`, { duration: Infinity })
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
