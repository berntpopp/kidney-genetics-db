<template>
  <div class="container mx-auto px-4 py-6">
    <!-- Breadcrumb -->
    <Breadcrumb class="mb-2">
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

    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <RefreshCw class="size-6 text-primary" />
      <div>
        <h1 class="text-2xl font-bold">Data Sources</h1>
        <p class="text-sm text-muted-foreground">
          Live status and statistics from integrated data sources
        </p>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-12">
      <div
        class="h-16 w-16 animate-spin rounded-full border-4 border-primary border-t-transparent mb-4"
      />
      <div class="text-lg font-semibold">Loading data sources...</div>
    </div>

    <!-- Data Sources Cards -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <Card
        v-for="source in dataSources"
        :key="source.name"
        class="source-card h-full overflow-hidden"
        @mouseenter="hoveredCard = source.name"
        @mouseleave="hoveredCard = null"
      >
        <!-- Header with gradient -->
        <div
          class="p-4"
          :style="`background: linear-gradient(135deg, ${getSourceGradient(source.name)});`"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <component :is="getSourceIcon(source.name)" class="size-6 text-white" />
              <div>
                <h3 class="text-lg font-bold text-white">{{ source.name }}</h3>
                <div class="text-xs text-white/95">{{ source.type || 'API' }}</div>
              </div>
            </div>
            <Badge
              :variant="source.status === 'active' ? 'default' : 'secondary'"
              :class="getStatusBadgeClass(source.status)"
            >
              {{ getStatusLabel(source.status) }}
            </Badge>
          </div>
        </div>

        <!-- Content -->
        <CardContent class="p-4">
          <p class="text-sm text-muted-foreground mb-4">
            {{ source.description || getSourceDescription(source.name) }}
          </p>

          <!-- Statistics -->
          <div class="flex justify-between items-center mb-3">
            <div class="text-center">
              <div class="text-lg font-bold text-green-600 dark:text-green-400">
                {{ source.stats?.gene_count || 0 }}
              </div>
              <div class="text-xs text-muted-foreground">Genes</div>
            </div>
            <div class="text-center">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <div class="text-lg font-bold text-primary">
                      {{ getMetadataCount(source, 'primary') }}
                    </div>
                    <div class="text-xs text-muted-foreground">
                      {{ getMetadataLabel(source, 'primary') }}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>{{ getMetadataTooltip(source, 'primary') }}</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <div v-if="getMetadataCount(source, 'secondary') > 0" class="text-center">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger>
                    <div class="text-lg font-bold text-blue-600 dark:text-blue-400">
                      {{ getMetadataCount(source, 'secondary') }}
                    </div>
                    <div class="text-xs text-muted-foreground">
                      {{ getMetadataLabel(source, 'secondary') }}
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>{{ getMetadataTooltip(source, 'secondary') }}</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>

          <!-- Last Update -->
          <Separator class="my-3" />
          <div class="flex items-center justify-between">
            <span class="text-xs text-muted-foreground">Last Updated</span>
            <span class="text-xs font-medium">
              {{ formatDate(source.stats?.last_updated) }}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Summary Statistics -->
    <Card class="mt-6">
      <CardHeader class="flex flex-row items-center gap-2">
        <ChartBarBig class="size-5 text-primary" />
        <CardTitle>Database Summary</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger as-child>
                <div class="text-center">
                  <div class="text-3xl font-bold text-primary">
                    {{ summaryStats.total_active }}
                  </div>
                  <div class="text-sm text-muted-foreground">
                    Active Sources
                    <CircleHelp class="size-3 ml-1 inline-block" />
                  </div>
                </div>
              </TooltipTrigger>
              <TooltipContent>{{
                apiResponse?.explanations?.active_sources || 'Number of active data sources'
              }}</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger as-child>
                <div class="text-center">
                  <div class="text-3xl font-bold text-green-600 dark:text-green-400">
                    {{ summaryStats.unique_genes.toLocaleString() }}
                  </div>
                  <div class="text-sm text-muted-foreground">
                    Genes with Evidence
                    <CircleHelp class="size-3 ml-1 inline-block" />
                  </div>
                </div>
              </TooltipTrigger>
              <TooltipContent>{{
                apiResponse?.explanations?.unique_genes || 'Total unique genes with evidence'
              }}</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger as-child>
                <div class="text-center">
                  <div class="text-3xl font-bold text-blue-600 dark:text-blue-400">
                    {{ calculateCoverage() }}%
                  </div>
                  <div class="text-sm text-muted-foreground">
                    Source Coverage
                    <CircleHelp class="size-3 ml-1 inline-block" />
                  </div>
                </div>
              </TooltipTrigger>
              <TooltipContent>{{
                apiResponse?.explanations?.source_coverage || 'Percentage of multi-source coverage'
              }}</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger as-child>
                <div class="text-center">
                  <div class="text-3xl font-bold" style="color: #8b5cf6">
                    {{ formatDate(summaryStats.last_update) }}
                  </div>
                  <div class="text-sm text-muted-foreground">
                    Last Updated
                    <CircleHelp class="size-3 ml-1 inline-block" />
                  </div>
                </div>
              </TooltipTrigger>
              <TooltipContent>{{
                apiResponse?.explanations?.last_updated || 'Most recent data update'
              }}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import {
  RefreshCw,
  ChartBarBig,
  CircleHelp,
  LayoutDashboard,
  User,
  FileText,
  TestTube,
  Dna,
  Stethoscope,
  Database
} from 'lucide-vue-next'
import { ref, computed, onMounted } from 'vue'
import { datasourceApi } from '@/api/datasources'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

const breadcrumbs = PUBLIC_BREADCRUMBS.dataSources

const loading = ref(true)
const hoveredCard = ref<string | null>(null)
const dataSources = ref<Array<Record<string, unknown>>>([])
const apiResponse = ref<Record<string, unknown> | null>(null)

const sourceDescriptions: Record<string, string> = {
  PanelApp: 'Expert-curated gene panels from UK Genomics England and Australian Genomics',
  HPO: 'Human Phenotype Ontology providing standardized phenotype-gene associations',
  PubTator: 'Literature mining from PubMed Central with automated text analysis',
  ClinGen: 'Clinical Genome Resource providing authoritative disease-gene relationships',
  GenCC: 'Harmonized gene-disease relationships from 40+ submitters worldwide',
  DiagnosticPanels: 'Commercial diagnostic panels from leading genetic testing laboratories'
}

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

const getSourceGradient = (sourceName: string) => {
  const gradients: Record<string, string> = {
    PanelApp: '#0EA5E9, #0284C7',
    HPO: '#8B5CF6, #7C3AED',
    PubTator: '#3B82F6, #2563EB',
    ClinGen: '#F59E0B, #D97706',
    GenCC: '#10B981, #059669',
    DiagnosticPanels: '#EF4444, #DC2626'
  }
  return gradients[sourceName] || gradients['PanelApp']
}

const getSourceIcon = (sourceName: string) => {
  const icons: Record<string, typeof Database> = {
    PanelApp: LayoutDashboard,
    HPO: User,
    PubTator: FileText,
    ClinGen: TestTube,
    GenCC: Dna,
    DiagnosticPanels: Stethoscope
  }
  return icons[sourceName] || Database
}

const getSourceDescription = (sourceName: string) => {
  return sourceDescriptions[sourceName] || 'Integrated data source for genetic information'
}

const getStatusBadgeClass = (status: string) => {
  switch (status) {
    case 'active':
      return 'bg-green-600 text-white'
    case 'error':
      return 'bg-red-600 text-white'
    case 'pending':
      return 'bg-yellow-600 text-white'
    default:
      return ''
  }
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'active':
      return 'Active'
    case 'error':
      return 'Error'
    case 'pending':
      return 'Pending'
    default:
      return 'Unknown'
  }
}

const getMetadataCount = (source: Record<string, unknown>, type: string): number => {
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

const getMetadataLabel = (source: Record<string, unknown>, type: string) => {
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

const getMetadataTooltip = (source: Record<string, unknown>, type: string) => {
  const explanations = (apiResponse.value as Record<string, unknown>)?.explanations as
    | Record<string, string>
    | undefined
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
  return date.toLocaleDateString()
}

onMounted(async () => {
  try {
    window.logService.info('Loading data sources...')
    const response = await datasourceApi.getDataSources()
    window.logService.info('Datasource API response:', response)

    apiResponse.value = response
    dataSources.value = response.sources || []
  } catch (error) {
    window.logService.error('Failed to load data sources:', error)
    dataSources.value = []
    apiResponse.value = {
      total_active: 0,
      last_pipeline_run: null,
      sources: []
    }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.source-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.source-card:hover {
  transform: translateY(-2px);
  box-shadow:
    0 10px 15px -3px rgb(0 0 0 / 0.1),
    0 4px 6px -4px rgb(0 0 0 / 0.1);
}

@media (prefers-reduced-motion: reduce) {
  .source-card {
    transition-duration: 0.01ms !important;
  }

  .source-card:hover {
    transform: none;
  }
}
</style>
