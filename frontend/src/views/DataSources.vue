<template>
  <div :class="PAGE_CONTAINER">
    <PageHeader
      title="Data Sources"
      description="Live status and statistics from integrated data sources"
    >
      <template #breadcrumb>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem v-for="(crumb, index) in breadcrumbs" :key="index">
              <BreadcrumbLink v-if="!crumb.disabled && crumb.to" as-child>
                <RouterLink :to="crumb.to">{{ crumb.title }}</RouterLink>
              </BreadcrumbLink>
              <BreadcrumbPage v-else>{{ crumb.title }}</BreadcrumbPage>
              <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1" />
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </template>
    </PageHeader>

    <TooltipProvider>
      <DataState
        :loading="loading"
        :error="loadError"
        :empty="dataSources.length === 0"
        error-title="Could not load data sources"
        empty-message="No data sources available."
        @retry="loadDataSources"
      >
        <!-- Skeletons in the loaded layout so nothing shifts when data arrives -->
        <template #loading>
          <h2 class="mb-3 text-xl font-semibold">Sources</h2>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            <!-- 7 = sources in backend/config/datasources.yaml; the API returns all, inactive included -->
            <Card v-for="n in 7" :key="n" class="h-full gap-0 py-0 motion-safe:animate-pulse">
              <div class="flex items-start justify-between gap-3 p-4 pb-2">
                <div class="h-6 w-28 rounded-md bg-muted" />
              </div>
              <CardContent class="px-4 pb-4">
                <div class="mb-4 h-10 rounded-md bg-muted" />
                <div class="mb-3 h-12 rounded-md bg-muted" />
                <Separator class="my-3" />
                <div class="h-4 rounded-md bg-muted" />
              </CardContent>
            </Card>
          </div>
          <Card class="mt-6">
            <CardHeader class="flex flex-row items-center gap-2">
              <ChartBarBig class="size-5 text-muted-foreground" aria-hidden="true" />
              <CardTitle tag="h2" class="text-xl">Database Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div class="grid grid-cols-2 gap-4 motion-safe:animate-pulse sm:grid-cols-4">
                <div v-for="n in 4" :key="n" class="h-14 rounded-md bg-muted" />
              </div>
            </CardContent>
          </Card>
        </template>

        <h2 class="mb-3 text-xl font-semibold">Sources</h2>
        <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Card
            v-for="source in dataSources"
            :key="source.name"
            class="h-full gap-0 py-0"
            :data-source="source.name"
          >
            <div class="flex items-start justify-between gap-3 p-4 pb-2">
              <div class="min-w-0">
                <h3 class="text-base font-semibold">
                  <SourceLabel :source="source.name" />
                </h3>
                <p v-if="source.type" class="text-xs text-muted-foreground">{{ source.type }}</p>
              </div>
              <StatusBadge :status="source.status" :tooltip="getStatusTooltip(source.status)" />
            </div>

            <CardContent class="flex flex-1 flex-col px-4 pb-4">
              <p class="mb-4 text-sm text-muted-foreground">
                {{ source.description || getSourceConfig(source.name).description }}
              </p>

              <!-- Counts as neutral stats; the label below each value is its unit -->
              <div class="mb-3 grid grid-cols-3 gap-2 text-center">
                <div class="flex flex-col-reverse">
                  <span class="text-xs text-muted-foreground">Genes</span>
                  <span class="text-lg font-semibold tabular-nums text-foreground">
                    {{ (source.stats?.gene_count || 0).toLocaleString() }}
                  </span>
                </div>
                <div v-for="kind in metricKinds(source)" :key="kind">
                  <Tooltip>
                    <TooltipTrigger as-child>
                      <button
                        type="button"
                        class="flex w-full flex-col-reverse rounded-md focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                      >
                        <span class="text-xs text-muted-foreground">
                          {{ getMetadataLabel(source, kind) }}
                        </span>
                        <span class="text-lg font-semibold tabular-nums text-foreground">
                          {{ getMetadataCount(source, kind).toLocaleString() }}
                        </span>
                      </button>
                    </TooltipTrigger>
                    <TooltipContent class="max-w-xs">{{
                      getMetadataTooltip(source, kind)
                    }}</TooltipContent>
                  </Tooltip>
                </div>
              </div>

              <Separator class="mt-auto mb-3" />
              <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">Last updated</span>
                <span class="font-medium tabular-nums">
                  {{ formatDate(source.stats?.last_updated) }}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        <!-- Summary Statistics -->
        <Card class="mt-6">
          <CardHeader class="flex flex-row items-center gap-2">
            <ChartBarBig class="size-5 text-muted-foreground" aria-hidden="true" />
            <CardTitle tag="h2" class="text-xl">Database Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Tooltip v-for="stat in summaryItems" :key="stat.label">
                <TooltipTrigger as-child>
                  <button
                    type="button"
                    class="flex flex-col-reverse items-center rounded-md text-center focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                  >
                    <span class="inline-flex items-center gap-1 text-sm text-muted-foreground">
                      {{ stat.label }}
                      <CircleHelp class="size-3" aria-hidden="true" />
                    </span>
                    <span
                      class="text-xl font-semibold whitespace-nowrap tabular-nums text-foreground sm:text-3xl"
                    >
                      {{ stat.value }}
                    </span>
                  </button>
                </TooltipTrigger>
                <TooltipContent class="max-w-xs">{{ stat.tooltip }}</TooltipContent>
              </Tooltip>
            </div>
          </CardContent>
        </Card>
      </DataState>
    </TooltipProvider>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { ChartBarBig, CircleHelp } from 'lucide-vue-next'
import { ref, computed, onMounted } from 'vue'
import { datasourceApi } from '@/api/datasources'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getBreadcrumbSchema } from '@/composables/useJsonLd'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import {
  DataState,
  PageHeader,
  PAGE_CONTAINER,
  SourceLabel,
  StatusBadge
} from '@/components/shared'
import { getSourceConfig } from '@/utils/sources'

const breadcrumbs = PUBLIC_BREADCRUMBS.dataSources

useJsonLd(getBreadcrumbSchema(breadcrumbs))

useSeoMeta({
  title: 'Data Sources — Integrated Genomic Databases',
  description:
    'Live status and statistics from integrated kidney genetics data sources: PanelApp, ClinGen, GenCC, HPO, PubTator, and diagnostic panels. Renal genetics database sources.',
  canonicalPath: '/data-sources'
})

const loading = ref(true)
const loadError = ref<Error | null>(null)
/** One source as /api/datasources/ returns it */
interface SourceRow {
  name: string
  status: string
  type?: string
  description?: string
  stats?: { gene_count?: number; last_updated?: string; metadata?: Record<string, number> }
}

const dataSources = ref<SourceRow[]>([])
const apiResponse = ref<Record<string, unknown> | null>(null)

const summaryStats = computed(() => {
  if (!apiResponse.value) {
    return { total_active: 0, unique_genes: 0, last_update: null }
  }
  const response = apiResponse.value as Record<string, unknown>
  return {
    total_active: (response.total_active as number) || 0,
    unique_genes: (response.total_unique_genes as number) || 0,
    last_update: (response.last_data_update as string) || null
  }
})

const STATUS_TOOLTIPS: Record<string, string> = {
  active: 'Data from this source is loaded and in use.',
  error: 'The last update of this source failed.',
  pending: 'An update of this source is pending.',
  inactive: 'This source is switched off in the current configuration.'
}

const getStatusTooltip = (status: string) =>
  STATUS_TOOLTIPS[status] ?? 'The server reported no status for this source.'

/** Source-specific metrics shown beside the gene count (secondary only when non-zero) */
const metricKinds = (source: SourceRow) =>
  getMetadataCount(source, 'secondary') > 0 ? ['primary', 'secondary'] : ['primary']

const getMetadataCount = (source: SourceRow, type: string): number => {
  const stats = source.stats as Record<string, unknown> | undefined
  const metadata = stats?.metadata as Record<string, number> | undefined
  if (!metadata) return 0

  if (type === 'primary') {
    switch (source.name) {
      case 'ClinGen':
        return metadata.expert_panels || 0
      case 'GenCC':
        return metadata.submissions || 0
      case 'HPO':
        return metadata.phenotype_terms || 0
      case 'PubTator':
        return metadata.publications || 0
      case 'PanelApp':
        return metadata.panels || 0
      case 'DiagnosticPanels':
        return metadata.providers || 0
      default:
        return 0
    }
  } else if (type === 'secondary') {
    switch (source.name) {
      case 'ClinGen':
        return metadata.classifications || 0
      case 'GenCC':
        return metadata.submitters || 0
      case 'PanelApp':
        return metadata.regions || 0
      case 'DiagnosticPanels':
        return metadata.panels || 0
      default:
        return 0
    }
  }
  return 0
}

const getMetadataLabel = (source: SourceRow, type: string) => {
  if (type === 'primary') {
    switch (source.name) {
      case 'ClinGen':
        return 'Expert Panels'
      case 'GenCC':
        return 'Submissions'
      case 'HPO':
        return 'Phenotypes'
      case 'PubTator':
        return 'Publications'
      case 'PanelApp':
        return 'Panels'
      case 'DiagnosticPanels':
        return 'Providers'
      default:
        return 'Records'
    }
  } else if (type === 'secondary') {
    switch (source.name) {
      case 'ClinGen':
        return 'Classifications'
      case 'GenCC':
        return 'Submitters'
      case 'PanelApp':
        return 'Regions'
      case 'DiagnosticPanels':
        return 'Panels'
      default:
        return ''
    }
  }
  return ''
}

const getMetadataTooltip = (source: SourceRow, type: string) => {
  const explanations = (apiResponse.value as Record<string, unknown>)?.explanations as
    Record<string, string> | undefined
  const tooltipMap: Record<string, string | undefined> = {
    'Expert Panels': explanations?.expert_panels,
    Classifications: explanations?.classifications,
    Submissions: explanations?.submissions,
    Submitters: explanations?.submitters,
    Phenotypes: explanations?.phenotypes,
    Publications: explanations?.publications,
    Panels: explanations?.panels,
    Regions: explanations?.regions,
    Providers: explanations?.providers
  }

  const label = getMetadataLabel(source, type)
  return tooltipMap[label] || `Number of ${label.toLowerCase()} in this data source`
}

const summaryItems = computed(() => {
  const explanations = (apiResponse.value?.explanations ?? {}) as Record<string, string>
  return [
    {
      label: 'Active Sources',
      value: summaryStats.value.total_active.toLocaleString(),
      tooltip: explanations.active_sources || 'Number of active data sources'
    },
    {
      label: 'Genes with Evidence',
      value: summaryStats.value.unique_genes.toLocaleString(),
      tooltip: explanations.unique_genes || 'Total unique genes with evidence'
    },
    {
      label: 'Source Coverage',
      value: `${calculateCoverage()}%`,
      tooltip: explanations.source_coverage || 'Percentage of multi-source coverage'
    },
    {
      label: 'Last Updated',
      value: formatDate(summaryStats.value.last_update),
      tooltip: explanations.last_updated || 'Most recent data update'
    }
  ]
})

const calculateCoverage = () => {
  const uniqueGenes = summaryStats.value.unique_genes || 1
  const response = apiResponse.value as Record<string, unknown> | null
  const totalEvidence = (response?.total_evidence_records as number) || 0
  const avgSourcesPerGene = totalEvidence / uniqueGenes
  return Math.min(Math.round((avgSourcesPerGene / 6) * 100), 100)
}

const formatDate = (dateStr: string | null | undefined) => {
  if (!dateStr) return 'Never'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return 'Never'

  const today = new Date()
  const diffDays = Math.floor((today.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  // en-CA formats as YYYY-MM-DD in local time, matching the relative labels
  return date.toLocaleDateString('en-CA')
}

const loadDataSources = async () => {
  loading.value = true
  loadError.value = null
  try {
    window.logService.info('Loading data sources...')
    const response = await datasourceApi.getDataSources()
    window.logService.info('Datasource API response:', response)

    apiResponse.value = response
    dataSources.value = (response.sources as SourceRow[]) || []
  } catch (error) {
    window.logService.error('Failed to load data sources:', error)
    dataSources.value = []
    apiResponse.value = null
    loadError.value = new Error("Couldn't load data sources from the server.")
  } finally {
    loading.value = false
  }
}

onMounted(loadDataSources)
</script>
