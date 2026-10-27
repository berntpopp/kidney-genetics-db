<template>
  <div :class="PAGE_CONTAINER">
    <AdminHeader
      title="Annotation Sources"
      subtitle="Control gene annotation pipeline and manage enrichment data sources"
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
          <strong class="font-medium text-foreground">Annotations</strong> enrich curated genes with
          data from external sources such as gnomAD (constraint), GTEx (tissue expression), HGNC
          (official symbols) and ClinVar (clinical variants).
        </p>
      </AlertDescription>
    </Alert>

    <!-- Statistics Overview -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      <AdminStatsCard
        title="Annotated Genes"
        :value="statistics.total_genes_with_annotations"
        :loading="statsLoading"
        :icon="Dna"
      />
      <AdminStatsCard
        title="Data Sources"
        :value="annotationSources.length"
        :loading="statsLoading"
        :icon="Database"
      />
      <AdminStatsCard
        title="Scheduled Jobs"
        :value="activeJobs"
        :loading="statsLoading"
        :icon="Clock4"
      />
      <AdminStatsCard
        title="Full Coverage"
        :value="statistics.genes_with_both_sources"
        :loading="statsLoading"
        :icon="CheckCheck"
      />
    </div>

    <!-- Pipeline Management -->
    <Card class="mb-6">
      <CardHeader>
        <CardTitle class="flex items-center"> Annotation Pipeline Control </CardTitle>
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
              <StatusBadge
                :status="pipelineStatusBadge.status"
                :label="pipelineStatusBadge.label"
                class="ml-2"
              />
            </div>

            <div
              v-if="pipelineStatus.updates_due && pipelineStatus.updates_due.length > 0"
              class="mb-4"
            >
              <span class="font-semibold">Sources Needing Updates:</span>
              <div class="flex flex-wrap gap-1 mt-1">
                <StatusBadge
                  v-for="source in pipelineStatus.updates_due"
                  :key="source"
                  status="stale"
                  :label="source"
                  tooltip="Update due"
                />
              </div>
            </div>

            <div v-else class="mb-4">
              <CircleCheck class="size-4 text-success mr-1 inline-block" aria-hidden="true" />
              <span class="text-sm text-muted-foreground">All sources are up to date</span>
            </div>
          </div>
          <div class="space-y-4">
            <div class="space-y-2">
              <Label>Update Strategy</Label>
              <Select v-model="pipelineForm.strategy">
                <SelectTrigger aria-label="Update Strategy">
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
              <Switch id="force-update" v-model="pipelineForm.force" />
              <Label for="force-update">Force update (ignore cache TTL)</Label>
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
                  <Chip
                    v-for="source in sourceFilterOptions"
                    :key="source.value"
                    kind="neutral"
                    :label="source.title"
                    :icon="pipelineForm.sources.includes(source.value) ? CircleCheck : undefined"
                    :aria-pressed="pipelineForm.sources.includes(source.value)"
                    :class="
                      pipelineForm.sources.includes(source.value)
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'bg-transparent text-muted-foreground'
                    "
                    @click="toggleSource(source.value)"
                  />
                </div>
                <div v-if="pipelineForm.sources.length === 0" class="text-warning text-xs mt-2">
                  <AlertTriangle class="size-3 mr-1 inline-block" aria-hidden="true" />
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
            @click="confirmPipelineUpdate"
          >
            <Rocket class="size-4 mr-2" />
            {{ pipelineLoading ? 'Running...' : 'Run Full Update' }}
          </Button>

          <Button
            v-else-if="pipelineStatus?.status === 'running'"
            variant="outline"
            :disabled="pauseLoading"
            @click="pauseUpdate"
          >
            <Pause class="size-4 mr-2" />
            {{ pauseLoading ? 'Pausing...' : 'Pause Pipeline' }}
          </Button>

          <Button
            v-if="pipelineStatus?.status === 'paused'"
            variant="outline"
            :disabled="resumeLoading"
            @click="resumeUpdate"
          >
            <Play class="size-4 mr-2" />
            {{ resumeLoading ? 'Resuming...' : 'Resume Pipeline' }}
          </Button>

          <Button variant="outline" :disabled="pipelineLoading" @click="validateAnnotations">
            <BadgeCheck class="size-4 mr-2" />
            Validate Data
          </Button>
          <Button variant="outline" :disabled="pipelineLoading" @click="askConfirm('refreshViews')">
            <RefreshCw class="size-4 mr-2" />
            Refresh Cache
          </Button>
        </div>

        <!-- Smart Update Actions -->
        <div class="flex gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            :disabled="failedLoading || pipelineStatus?.status === 'running'"
            @click="askConfirm('retryFailed')"
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
        <CardTitle class="flex items-center"> Test Gene Annotation Lookup </CardTitle>
      </CardHeader>
      <CardContent>
        <p class="text-sm text-muted-foreground mb-4">
          Look up annotations for any gene in the database to verify annotation coverage and data
          quality.
        </p>

        <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
          <div class="md:col-span-6 space-y-2">
            <Label for="lookup-gene">Gene symbol</Label>
            <Input
              id="lookup-gene"
              v-model="lookupGeneId"
              placeholder="e.g. PKD1"
              autocomplete="off"
              @keyup.enter="lookupGeneAnnotations"
            />
            <p class="text-xs text-muted-foreground">
              An HGNC gene symbol (or the internal gene ID)
            </p>
          </div>
          <div class="md:col-span-4 space-y-2">
            <Label>Filter by Source (optional)</Label>
            <Select v-model="lookupSource">
              <SelectTrigger aria-label="Filter by Source">
                <SelectValue placeholder="All sources" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All sources</SelectItem>
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
              <strong>Gene:</strong> {{ lookupResult.gene?.symbol }} ({{
                lookupResult.gene?.hgnc_id
              }})
            </div>

            <div class="mb-3">
              <strong>Annotation Coverage:</strong>
              {{ Object.keys(lookupResult.annotations || {}).length }} data sources
            </div>

            <div v-if="Object.keys(lookupResult.annotations || {}).length > 0">
              <strong>Available Annotations:</strong>
              <div class="flex flex-wrap gap-1 mt-2">
                <Chip
                  v-for="source in Object.keys(lookupResult.annotations || {})"
                  :key="source"
                  kind="neutral"
                  :label="`${source.toUpperCase()} (${lookupResult.annotations[source].length} records)`"
                />
              </div>
            </div>

            <div v-else class="mt-2">
              <AlertTriangle class="size-4 text-warning mr-1 inline-block" aria-hidden="true" />
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
          Annotation Sources ({{ annotationSources.length }})
        </CardTitle>
      </CardHeader>
      <CardContent class="p-0">
        <DataState
          :loading="loading && !annotationSources.length"
          :error="sourcesError"
          error-title="Could not load annotation sources"
          :empty="!annotationSources.length"
          empty-message="No annotation sources are configured."
          class="m-4"
          @retry="loadAnnotationSources"
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
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-[200px]">Source</TableHead>
                <TableHead class="w-[300px]">Description</TableHead>
                <TableHead class="w-[150px]">Last Update</TableHead>
                <TableHead class="w-[150px]">Next Update</TableHead>
                <TableHead class="w-[120px]">Frequency</TableHead>
                <TableHead class="w-[100px]"><span class="sr-only">Actions</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="item in annotationSources" :key="item.source_name">
                <TableCell>
                  <div class="flex items-center gap-2">
                    <strong>{{ item.display_name || item.source_name }}</strong>
                    <StatusBadge v-if="!item.is_active" status="inactive" />
                  </div>
                </TableCell>
                <TableCell>
                  <span class="text-xs text-muted-foreground">{{
                    item.description || 'No description'
                  }}</span>
                </TableCell>
                <TableCell>
                  <span class="text-xs tabular-nums">
                    {{ item.last_update ? formatDate(item.last_update) : 'Never' }}
                  </span>
                </TableCell>
                <TableCell>
                  <span class="text-xs tabular-nums">
                    {{ item.next_update ? formatDate(item.next_update) : 'Not scheduled' }}
                  </span>
                </TableCell>
                <TableCell>
                  <Chip
                    kind="neutral"
                    :label="item.update_frequency || 'Manual'"
                    tooltip="How often this source is refreshed"
                  />
                </TableCell>
                <TableCell>
                  <div class="flex justify-end gap-1">
                    <Tooltip>
                      <TooltipTrigger as-child>
                        <Button
                          :aria-label="`Annotate genes missing ${item.display_name || item.source_name}`"
                          variant="ghost"
                          size="icon-sm"
                          :disabled="sourceUpdateLoading[item.source_name]"
                          @click="updateSource(item.source_name)"
                        >
                          <Play class="size-4" aria-hidden="true" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Annotate genes missing this source</TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger as-child>
                        <Button
                          :aria-label="`Details for ${item.display_name || item.source_name}`"
                          variant="ghost"
                          size="icon-sm"
                          @click="showSourceDetails(item)"
                        >
                          <Info class="size-4" aria-hidden="true" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Source details</TooltipContent>
                    </Tooltip>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </DataState>
      </CardContent>
    </Card>

    <!-- Real-time Progress Monitor -->
    <DataSourceProgress class="mb-6" />

    <!-- Scheduled Jobs -->
    <Card class="mb-6">
      <CardHeader class="flex flex-row flex-wrap items-center justify-between gap-2">
        <CardTitle class="flex flex-wrap items-center gap-y-1">
          Scheduled Jobs
          <StatusBadge
            :status="schedulerInfo.scheduler_running ? 'running' : 'idle'"
            :label="schedulerInfo.scheduler_running ? 'Scheduler running' : 'Scheduler stopped'"
            class="ml-2"
          />
        </CardTitle>
        <Button variant="outline" size="sm" :disabled="jobsLoading" @click="loadScheduledJobs">
          <RefreshCw class="size-4 mr-2" :class="{ 'animate-spin': jobsLoading }" />
          Refresh Jobs
        </Button>
      </CardHeader>
      <CardContent class="p-0">
        <DataState
          :loading="jobsLoading && !scheduledJobs.length"
          :error="jobsError"
          error-title="Could not load scheduled jobs"
          :empty="!scheduledJobs.length"
          empty-message="No jobs are scheduled."
          class="m-4"
          @retry="loadScheduledJobs"
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-[200px]">Job ID</TableHead>
                <TableHead class="w-[200px]">Name</TableHead>
                <TableHead class="w-[150px]">Next Run</TableHead>
                <TableHead class="w-[150px]">Trigger</TableHead>
                <TableHead class="w-[100px]"><span class="sr-only">Actions</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="item in scheduledJobs" :key="item.id">
                <TableCell>
                  <code class="text-xs">{{ item.id }}</code>
                </TableCell>
                <TableCell>{{ item.name }}</TableCell>
                <TableCell>
                  <span class="text-xs tabular-nums">
                    {{ item.next_run ? formatDate(item.next_run) : 'Not scheduled' }}
                  </span>
                </TableCell>
                <TableCell>
                  <span class="text-xs">{{ item.trigger || 'Unknown' }}</span>
                </TableCell>
                <TableCell>
                  <div class="flex justify-end">
                    <Tooltip>
                      <TooltipTrigger as-child>
                        <Button
                          :aria-label="`Run ${item.name} now`"
                          variant="ghost"
                          size="icon-sm"
                          :disabled="jobTriggerLoading[item.id]"
                          @click="triggerJob(item.id)"
                        >
                          <Play class="size-4" aria-hidden="true" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Run now</TooltipContent>
                    </Tooltip>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </DataState>
      </CardContent>
    </Card>

    <ConfirmAction
      v-model:open="confirmOpen"
      :title="CONFIRMS[confirmKind].title"
      :description="CONFIRMS[confirmKind].description"
      :confirm-label="CONFIRMS[confirmKind].confirm"
      @confirm="CONFIRMS[confirmKind].run()"
    />

    <AlertDialog v-model:open="showUpdateDialog">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Start annotation pipeline update?</AlertDialogTitle>
          <AlertDialogDescription>
            Strategy:
            <strong>{{
              strategyOptions.find(o => o.value === pipelineForm.strategy)?.title
            }}</strong
            >. Sources:
            <strong>{{
              pipelineForm.sources.length
                ? pipelineForm.sources.join(', ').toUpperCase()
                : 'all annotation sources'
            }}</strong
            >.<span v-if="pipelineForm.force"> Cache TTL is ignored (force).</span>
            The update runs in the background.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction @click="triggerPipelineUpdate">Start Update</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

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
                <StatusBadge
                  :status="selectedSource.is_active ? 'active' : 'inactive'"
                  class="ml-1"
                />
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
import { Chip, DataState, PAGE_CONTAINER, StatusBadge } from '@/components/shared'
import ConfirmAction from '@/components/admin/ConfirmAction.vue'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { geneApi } from '@/api/genes'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import DataSourceProgress from '@/components/DataSourceProgress.vue'
import * as annotationsApi from '@/api/admin/annotations'
import { toast } from 'vue-sonner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
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
  CheckCheck,
  CircleAlert,
  CircleCheck,
  Clock4,
  Database,
  Dna,
  Info,
  Pause,
  Play,
  RefreshCw,
  Rocket,
  Search,
  SquarePlus
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
const sourcesError = ref(null)
const jobsError = ref(null)

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

// One status from both fields, so "ready" never sits next to a list of due sources
const pipelineStatusBadge = computed(() => {
  if (!pipelineStatus.pipeline_ready) return { status: 'error', label: 'Issues Detected' }
  const due = pipelineStatus.updates_due?.length ?? 0
  if (due > 0) return { status: 'warning', label: `${due} ${due === 1 ? 'Source' : 'Sources'} Due` }
  return { status: 'ok', label: 'All Sources Up to Date' }
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
const showUpdateDialog = ref(false)
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
    'uniprot',
    'mondo'
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

// Heavy or bulk operations ask first (one ConfirmAction for each kind)
const confirmOpen = ref(false)
const confirmKind = ref('refreshViews')
const CONFIRMS = {
  refreshViews: {
    title: 'Refresh annotation views?',
    description:
      'Rebuilds the materialized annotation views from the database. Queries may be slower until it finishes.',
    confirm: 'Refresh views',
    run: () => refreshMaterializedView()
  },
  retryFailed: {
    title: 'Retry failed annotations?',
    description:
      'Starts a background update for every gene whose last annotation attempt failed, across all sources.',
    confirm: 'Retry failed',
    run: () => updateFailed()
  }
}
const askConfirm = kind => {
  confirmKind.value = kind
  confirmOpen.value = true
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
  sourcesError.value = null
  try {
    const response = await annotationsApi.getAnnotationSources()
    annotationSources.value = response.data
  } catch (error) {
    window.logService.error('Failed to load annotation sources:', error)
    sourcesError.value = error.message || 'Request failed'
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
  jobsError.value = null
  try {
    const response = await annotationsApi.getScheduledJobs()
    Object.assign(schedulerInfo, response.data)
    scheduledJobs.value = response.data.jobs || []
  } catch (error) {
    window.logService.error('Failed to load scheduled jobs:', error)
    jobsError.value = error.message || 'Request failed'
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

const confirmPipelineUpdate = () => {
  // Validate SELECTIVE strategy has sources selected
  if (pipelineForm.strategy === 'selective' && pipelineForm.sources.length === 0) {
    toast.warning('Please select at least one source for selective update', { duration: 5000 })
    return
  }
  showUpdateDialog.value = true
}

const triggerPipelineUpdate = async () => {
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
    const input = String(lookupGeneId.value).trim()
    // Digits are an internal gene ID; anything else is resolved as a gene symbol
    const geneId = /^\d+$/.test(input) ? Number(input) : (await geneApi.getGene(input)).id
    const response = await annotationsApi.getGeneAnnotations(
      Number(geneId),
      lookupSource.value === 'all' ? null : lookupSource.value
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
