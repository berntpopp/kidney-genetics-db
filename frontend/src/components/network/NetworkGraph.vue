<template>
  <Card class="network-graph-card w-full">
    <CardHeader class="flex flex-row items-center justify-between space-y-0 p-4">
      <div>
        <CardTitle tag="h2" class="text-lg font-semibold"
          >Protein-Protein Interaction Network</CardTitle
        >
        <p class="text-sm text-muted-foreground mt-1">
          {{ networkStats }}
        </p>
      </div>
      <div class="flex gap-2">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                aria-label="Export graph as PNG"
                variant="ghost"
                size="icon"
                class="size-8"
                :disabled="!cyInstance"
                @click="exportGraph"
              >
                <Download class="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom"><p>Export graph as PNG</p></TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                aria-label="Fit graph to view"
                variant="ghost"
                size="icon"
                class="size-8"
                :disabled="!cyInstance"
                @click="fitGraph"
              >
                <Maximize2 class="size-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom"><p>Fit to screen</p></TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                aria-label="Refresh network"
                variant="ghost"
                size="icon"
                class="size-8"
                :disabled="loading"
                @click="$emit('refresh')"
              >
                <RefreshCw class="size-4" :class="{ 'animate-spin': loading }" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom"><p>Refresh network</p></TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </CardHeader>

    <Separator />

    <!-- Network Controls -->
    <CardContent class="p-3">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div class="space-y-1">
          <label class="text-xs font-medium text-muted-foreground">Layout</label>
          <Select v-model="layoutType" @update:model-value="applyLayout">
            <SelectTrigger aria-label="Layout" class="h-9">
              <SelectValue placeholder="Layout" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="opt in layoutOptions" :key="opt.value" :value="opt.value">
                {{ opt.title }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="space-y-1">
          <label class="text-xs font-medium text-muted-foreground">Node Color</label>
          <Select :model-value="colorMode" @update:model-value="$emit('update:colorMode', $event)">
            <SelectTrigger aria-label="Node Color" class="h-9">
              <Palette class="size-4 mr-2 text-muted-foreground" />
              <SelectValue placeholder="Node Color" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="mode in networkAnalysisConfig.nodeColoring.modes"
                :key="mode.value"
                :value="mode.value"
              >
                {{ mode.label }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <!-- Search Controls Row -->
      <div
        v-if="cyInstance && !loading && !error"
        class="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3"
      >
        <div class="relative">
          <Search class="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
          <Input
            v-model="localSearchPattern"
            placeholder="e.g., COL*, PKD1, *A1"
            aria-label="Search genes in the network"
            class="pl-8 h-9"
            :class="{ 'pr-24': matchCount > 0 }"
            @input="handleSearchInput"
            @keyup.enter="handleSearch(localSearchPattern)"
          />
          <button
            v-if="localSearchPattern"
            type="button"
            aria-label="Clear search"
            class="absolute top-1.5 right-1.5 inline-flex size-6 items-center justify-center rounded-sm text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            @click="clearSearchHighlight"
          >
            <X class="size-4" />
          </button>
          <Badge
            v-if="matchCount > 0"
            variant="secondary"
            class="absolute right-8 top-1.5 text-xs tabular-nums"
          >
            {{ matchCount }} {{ matchCount === 1 ? 'match' : 'matches' }}
          </Badge>
        </div>

        <div class="flex gap-2 items-center">
          <Button
            variant="outline"
            size="sm"
            :disabled="matchCount === 0"
            @click="highlightSearchMatches"
          >
            <CheckSquare class="size-4 mr-1" />
            Highlight All
          </Button>
          <Button
            variant="outline"
            size="sm"
            :disabled="matchCount === 0"
            @click="fitSearchMatches"
          >
            <Maximize2 class="size-4 mr-1" />
            Fit View
          </Button>
          <span v-if="localSearchPattern && matchCount === 0" class="text-sm text-muted-foreground">
            No matches found
          </span>
        </div>
      </div>
    </CardContent>

    <Separator />

    <!-- Cytoscape Graph Container -->
    <CardContent class="p-0 network-container-wrapper">
      <div
        ref="cytoscapeContainer"
        class="cytoscape-container"
        :style="{ height: graphHeight, visibility: !loading && !error ? 'visible' : 'hidden' }"
      >
        <!-- Tooltip for node hover -->
        <div
          v-if="tooltipVisible"
          class="node-tooltip"
          :style="{
            left: tooltipX + 'px',
            top: tooltipY + 'px'
          }"
        >
          <div class="tooltip-gene">{{ tooltipData.geneSymbol }}</div>
          <div v-if="tooltipData.clusterName" class="tooltip-cluster">
            {{ tooltipData.clusterName }}
          </div>
          <div v-if="tooltipData.hpoData" class="tooltip-hpo">
            <div class="tooltip-hpo-divider"></div>
            <div class="tooltip-hpo-section-title">Gene Classification</div>
            <div v-if="tooltipData.hpoData.clinical_group" class="tooltip-hpo-item">
              <span class="tooltip-hpo-label">Clinical:</span>
              {{
                networkAnalysisConfig.nodeColoring.labels.clinical_group[
                  tooltipData.hpoData.clinical_group
                ] || tooltipData.hpoData.clinical_group
              }}
            </div>
            <div v-if="tooltipData.hpoData.onset_group" class="tooltip-hpo-item">
              <span class="tooltip-hpo-label">Onset:</span>
              {{
                networkAnalysisConfig.nodeColoring.labels.onset_group[
                  tooltipData.hpoData.onset_group
                ] || tooltipData.hpoData.onset_group
              }}
            </div>
            <div v-if="tooltipData.hpoData.is_syndromic !== null" class="tooltip-hpo-item">
              <span class="tooltip-hpo-label">Type:</span>
              {{ tooltipData.hpoData.is_syndromic ? 'Syndromic' : 'Isolated' }}
            </div>

            <!-- Cluster context percentages -->
            <div v-if="tooltipData.hpoPercentages" class="tooltip-cluster-context">
              <div class="tooltip-hpo-divider"></div>
              <div class="tooltip-hpo-section-title">In Cluster</div>
              <div v-if="tooltipData.hpoPercentages.clinical" class="tooltip-context-item">
                <span class="tooltip-context-percent"
                  >{{ tooltipData.hpoPercentages.clinical }}%</span
                >
                <span class="tooltip-context-label">
                  {{
                    networkAnalysisConfig.nodeColoring.labels.clinical_group[
                      tooltipData.hpoData.clinical_group
                    ] || tooltipData.hpoData.clinical_group
                  }}
                </span>
              </div>
              <div v-if="tooltipData.hpoPercentages.onset" class="tooltip-context-item">
                <span class="tooltip-context-percent">{{ tooltipData.hpoPercentages.onset }}%</span>
                <span class="tooltip-context-label">
                  {{
                    networkAnalysisConfig.nodeColoring.labels.onset_group[
                      tooltipData.hpoData.onset_group
                    ] || tooltipData.hpoData.onset_group
                  }}
                </span>
              </div>
              <div v-if="tooltipData.hpoPercentages.syndromic" class="tooltip-context-item">
                <span class="tooltip-context-percent"
                  >{{ tooltipData.hpoPercentages.syndromic }}%</span
                >
                <span class="tooltip-context-label">
                  {{ tooltipData.hpoData.is_syndromic ? 'Syndromic' : 'Isolated' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading State: the canvas keeps its height, with a progress message -->
      <div
        v-if="loading"
        class="absolute inset-0 flex items-center justify-center bg-muted/40"
        role="status"
      >
        <p class="flex items-center gap-2 text-sm text-muted-foreground">
          <LoaderCircle class="size-5 motion-safe:animate-spin" aria-hidden="true" />
          Building and laying out the network…
        </p>
      </div>

      <!-- Error State -->
      <div v-if="error && !loading" class="absolute inset-0 flex items-center justify-center p-4">
        <DataState
          class="max-w-md"
          :error="error"
          error-title="Could not build the network"
          @retry="$emit('refresh')"
        />
      </div>

      <!-- Empty State -->
      <div
        v-if="!loading && !error && !cyInstance"
        class="absolute inset-0 flex items-center justify-center"
      >
        <div class="text-center text-muted-foreground">
          <NetworkIcon class="size-16 mb-4 mx-auto" />
          <p class="text-base">No network data available</p>
          <p class="text-sm">Build a network to visualize interactions</p>
        </div>
      </div>
    </CardContent>

    <!-- Dynamic Legend (Clusters or HPO Classifications) -->
    <Separator v-if="showLegend" />
    <CardContent v-if="showLegend" class="p-3">
      <!-- HPO Classification Legend (when in HPO mode) -->
      <div v-if="hpoLegendItems.length > 0" class="mb-3">
        <div class="flex items-center mb-2">
          <span class="text-xs text-muted-foreground font-medium">{{ legendTitle }}</span>
        </div>
        <div class="flex flex-wrap gap-2">
          <Badge
            v-for="item in hpoLegendItems"
            :key="item.id"
            variant="outline"
            class="text-foreground"
            :style="legendChipStyle(item.color)"
          >
            {{ item.label }}
          </Badge>
        </div>
      </div>

      <!-- Cluster Legend (always visible when clusters exist) -->
      <div v-if="clusterLegendItems.length > 0">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs text-muted-foreground font-medium">
            {{ colorMode === 'cluster' ? legendTitle : 'Clusters' }}
            <span v-if="colorMode !== 'cluster'" class="ml-1">(inactive)</span>
          </span>
          <!-- Sort options only for cluster mode -->
          <div v-if="colorMode === 'cluster'" class="inline-flex rounded-md border">
            <Button
              :variant="clusterSortMethod === 'size' ? 'secondary' : 'ghost'"
              :aria-pressed="clusterSortMethod === 'size'"
              size="sm"
              class="h-7 rounded-none rounded-l-md text-xs px-2"
              title="Sort by cluster size (largest first)"
              @click="clusterSortMethod = 'size'"
            >
              <ArrowUpDown class="size-3 mr-1" />
              Size
            </Button>
            <Button
              :variant="clusterSortMethod === 'spatial' ? 'secondary' : 'ghost'"
              :aria-pressed="clusterSortMethod === 'spatial'"
              size="sm"
              class="h-7 rounded-none rounded-r-md text-xs px-2"
              title="Sort by spatial proximity in graph"
              @click="clusterSortMethod = 'spatial'"
            >
              <Route class="size-3 mr-1" />
              Spatial
            </Button>
          </div>
        </div>
        <div class="flex flex-wrap gap-2">
          <TooltipProvider :delay-duration="300">
            <Tooltip v-for="item in clusterLegendItems" :key="item.id">
              <TooltipTrigger as-child>
                <Badge
                  variant="outline"
                  role="button"
                  tabindex="0"
                  class="cursor-pointer cluster-chip"
                  :class="item.isActive ? 'text-foreground' : 'text-muted-foreground'"
                  :style="item.isActive ? legendChipStyle(item.color) : {}"
                  @mouseenter="highlightCluster(item.id)"
                  @mouseleave="clearHighlight()"
                  @focus="highlightCluster(item.id)"
                  @blur="clearHighlight()"
                  @click="openClusterDialog(item.id)"
                  @keydown.enter.prevent="openClusterDialog(item.id)"
                  @keydown.space.prevent="openClusterDialog(item.id)"
                >
                  {{ item.label }}
                  <span class="tabular-nums text-muted-foreground">{{ item.size }}</span>
                </Badge>
              </TooltipTrigger>

              <!-- HPO Statistics Tooltip -->
              <TooltipContent
                v-if="clusterStatistics.has(item.id) && hpoClassifications?.data"
                side="top"
                class="max-w-xs p-3 z-50"
              >
                <div class="text-sm font-medium mb-1.5 flex items-center gap-2">
                  {{ item.label }}
                  <Badge variant="secondary" class="text-xs">
                    {{ clusterStatistics.get(item.id).total }} genes
                  </Badge>
                </div>

                <Separator class="my-1.5" />

                <!-- HPO Data Coverage (tooltip is inverted: text stays on background tokens) -->
                <div class="mb-2 flex items-center gap-1 text-xs text-background/80">
                  <Database class="size-3" aria-hidden="true" />
                  HPO data: {{ clusterStatistics.get(item.id).hpoDataCount }} /
                  {{ clusterStatistics.get(item.id).total }}
                  ({{ clusterStatistics.get(item.id).hpoDataPercentage }}%)
                </div>

                <div
                  v-for="group in tooltipGroups(clusterStatistics.get(item.id))"
                  :key="group.title"
                  class="mb-2 last:mb-0"
                >
                  <div class="mb-1 text-xs font-medium">{{ group.title }}</div>
                  <ul class="flex flex-wrap gap-x-3 gap-y-1 text-xs">
                    <li v-for="row in group.rows" :key="row.label" class="flex items-center gap-1">
                      <span
                        class="size-2 shrink-0 rounded-full"
                        :style="{ backgroundColor: row.color }"
                        aria-hidden="true"
                      />
                      {{ row.label }}: <span class="tabular-nums">{{ row.value }}</span>
                    </li>
                  </ul>
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>
    </CardContent>

    <!-- Cluster Details Dialog -->
    <ClusterDetailsDialog
      v-model="clusterDialogOpen"
      :cluster-id="selectedClusterId"
      :cluster-display-name="
        selectedClusterId !== null ? getClusterDisplayName(selectedClusterId) : ''
      "
      :cluster-color="selectedClusterColor"
      :genes="selectedClusterGenes"
      :hpo-classifications="hpoClassifications"
      :hgnc-ids="hgncIds"
      @highlight-gene="highlightGeneInNetwork"
    />
  </Card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  ArrowUpDown,
  CheckSquare,
  Database,
  Download,
  LoaderCircle,
  Maximize2,
  Network as NetworkIcon,
  Palette,
  RefreshCw,
  Route,
  Search,
  X
} from 'lucide-vue-next'
import cytoscape from 'cytoscape'
import coseBilkent from 'cytoscape-cose-bilkent'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { DataState } from '@/components/shared'
import { useAppTheme } from '@/composables/useAppTheme'
import { markOutline } from '../visualizations/chartMarks'
import { canvasColor, clearCanvasColors } from './canvasColor'

import ClusterDetailsDialog from './ClusterDetailsDialog.vue'
import { useNetworkSearch } from '../../composables/useNetworkSearch'
import { networkAnalysisConfig, OTHER_CLUSTER_COLOR } from '../../config/networkAnalysis'
import { computeHpoClusterStats } from './hpoClusterStats'

// Nodes before clustering, and anything without a category, stay neutral
const DEFAULT_NODE_COLOR = 'var(--muted-foreground)'

// Register cose-bilkent layout
cytoscape.use(coseBilkent)

// Props
const props = defineProps({
  networkData: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  },
  height: {
    type: String,
    default: '600px'
  },
  clusterIdMapping: {
    type: Map,
    default: () => new Map()
  },
  clusterColorsMap: {
    type: Map,
    default: () => new Map()
  },
  colorMode: {
    type: String,
    default: 'cluster'
  },
  hpoClassifications: {
    type: Object,
    default: null
  },
  loadingHPOData: {
    type: Boolean,
    default: false
  },
  /** gene_id -> HGNC ID, to name genes by their identifier instead of internal ids */
  hgncIds: {
    type: Map,
    default: () => new Map()
  }
})

const { isDark } = useAppTheme()

// Emits
const emit = defineEmits(['refresh', 'update:colorMode', 'nodeClick', 'selectCluster'])

// Refs
const cytoscapeContainer = ref(null)
const cyInstance = ref(null)
const layoutType = ref('cose-bilkent')
const clusterColors = ref({})
const clusterCentroids = ref({}) // { clusterId: { x, y } }
const clusterSortMethod = ref('size') // 'size' or 'spatial'

// Cluster details dialog state
const clusterDialogOpen = ref(false)
const selectedClusterId = ref(null)
const selectedClusterGenes = ref([])

// Tooltip state
const tooltipVisible = ref(false)
const tooltipX = ref(0)
const tooltipY = ref(0)
const tooltipData = ref({
  geneSymbol: '',
  clusterName: '',
  hpoData: null,
  hpoPercentages: null
})

// Search state (using composable)
const { matchCount, searchNodes, clearSearch } = useNetworkSearch()
const searchMatchedNodes = ref([])
const localSearchPattern = ref('')

// Debounce timer for auto-search
let searchDebounceTimer = null

// Computed
const graphHeight = computed(() => props.height)

const networkStats = computed(() => {
  if (!props.networkData) return 'No network loaded'
  const { nodes, edges, components } = props.networkData
  return `Displayed: ${nodes} genes, ${edges} interactions, ${components} component(s)`
})

// Legend visibility - show if clusters exist OR HPO data exists
const showLegend = computed(() => {
  const hasClusters = Object.keys(clusterColors.value).length > 0
  const hasHPOData = props.hpoClassifications?.data && props.hpoClassifications.data.length > 0

  // Show if we have clusters (always show them) OR HPO data
  return hasClusters || hasHPOData
})

// Cluster legend items (always available when clusters exist)
const clusterLegendItems = computed(() => {
  if (Object.keys(clusterColors.value).length === 0) {
    return []
  }

  return sortedClusterColors.value.map(cluster => ({
    label: getClusterDisplayName(cluster.backendId),
    size: clusterSizes.value.get(cluster.backendId) ?? 0,
    color: cluster.color,
    id: cluster.backendId,
    type: 'cluster',
    isActive: props.colorMode === 'cluster'
  }))
})

// HPO legend items (when in HPO mode)
const hpoLegendItems = computed(() => {
  if (props.colorMode === 'cluster' || !props.hpoClassifications?.data) {
    return []
  }

  const colorScheme = networkAnalysisConfig.nodeColoring.colorSchemes[props.colorMode]
  const labels = networkAnalysisConfig.nodeColoring.labels[props.colorMode]

  if (!colorScheme || !labels) {
    return []
  }

  return Object.entries(colorScheme).map(([key, color]) => ({
    label: labels[key] || key,
    color,
    id: key,
    type: 'hpo',
    isActive: true
  }))
})

// Rows for the cluster tooltip: one swatch + label per HPO group (neutral text)
const tooltipGroups = stats => {
  const schemes = networkAnalysisConfig.nodeColoring.colorSchemes
  const { syndromic } = stats
  const syndromicRows = []
  if (syndromic.assessedCount > 0) {
    syndromicRows.push(
      {
        label: 'Syndromic',
        value: `${syndromic.syndromicPercentage}%`,
        color: schemes.syndromic.true
      },
      {
        label: 'Isolated',
        value: `${syndromic.isolatedPercentage}%`,
        color: schemes.syndromic.false
      }
    )
  }
  if (syndromic.unknownCount > 0) {
    syndromicRows.push({
      label: networkAnalysisConfig.nodeColoring.labels.syndromic.null,
      value: `${syndromic.unknownCount} ${syndromic.unknownCount === 1 ? 'gene' : 'genes'}`,
      color: schemes.syndromic.null
    })
  }
  const pct = rows => rows.map(r => ({ label: r.label, value: `${r.percentage}%`, color: r.color }))
  return [
    { title: 'Clinical Classification', rows: pct(stats.clinical) },
    { title: 'Age of Onset', rows: pct(stats.onset) },
    { title: `Syndromic Assessment (${syndromic.assessedCount} assessed)`, rows: syndromicRows }
  ].filter(g => g.rows.length > 0)
}

// Genes per cluster, for the legend chips
const clusterSizes = computed(() => {
  const sizes = new Map()
  for (const el of props.networkData?.cytoscape_json?.elements ?? []) {
    const id = el.data?.cluster_id
    if (el.data?.gene_id && id !== undefined) sizes.set(id, (sizes.get(id) ?? 0) + 1)
  }
  return sizes
})

// Legend title based on color mode
const legendTitle = computed(() => {
  const mode = networkAnalysisConfig.nodeColoring.modes.find(m => m.value === props.colorMode)
  return mode?.label || 'Legend'
})

const selectedClusterColor = computed(() => {
  if (selectedClusterId.value === null) return OTHER_CLUSTER_COLOR
  return clusterColors.value[selectedClusterId.value] || OTHER_CLUSTER_COLOR
})

// Sort cluster colors by display ID or spatial proximity
const sortedClusterColors = computed(() => {
  if (!props.clusterIdMapping || props.clusterIdMapping.size === 0) {
    // Fallback: convert to array sorted by backendId
    return Object.entries(clusterColors.value)
      .map(([backendId, color]) => ({
        backendId: parseInt(backendId),
        displayId: parseInt(backendId),
        color
      }))
      .sort((a, b) => a.backendId - b.backendId)
  }

  // Create array of cluster objects with display info and centroids
  const clusters = Object.entries(clusterColors.value).map(([backendId, color]) => ({
    backendId: parseInt(backendId),
    displayId: props.clusterIdMapping.get(parseInt(backendId)) ?? parseInt(backendId),
    color,
    centroid: clusterCentroids.value[backendId] || null
  }))

  // Sort based on selected method
  if (clusterSortMethod.value === 'spatial' && Object.keys(clusterCentroids.value).length > 0) {
    // Spatial sorting: by angle from center (clockwise from top)
    // This creates a natural circular flow around the network
    clusters.sort((a, b) => {
      if (!a.centroid || !b.centroid) return 0
      // Calculate angle from center (atan2 returns -π to π, adjust to 0-2π)
      const angleA = Math.atan2(a.centroid.y, a.centroid.x) + Math.PI
      const angleB = Math.atan2(b.centroid.y, b.centroid.x) + Math.PI
      return angleA - angleB
    })
  } else {
    // Default: Sort by displayId (size-based ranking: 0 = largest cluster)
    clusters.sort((a, b) => a.displayId - b.displayId)
  }

  // Return array (NOT object) to preserve sort order
  // JavaScript auto-sorts numeric object keys, breaking our custom order
  return clusters
})

// Compute HPO classification statistics per cluster for hover tooltips
const clusterStatistics = computed(() => {
  const stats = new Map()

  // Need both network data and HPO classifications
  if (!props.networkData?.cytoscape_json?.elements || !props.hpoClassifications?.data) {
    return stats
  }

  window.logService?.debug('[ClusterStats] Computing HPO statistics per cluster')

  // Group genes by cluster
  const clusterGenes = new Map()
  props.networkData.cytoscape_json.elements
    .filter(el => el.data?.gene_id && el.data?.cluster_id !== undefined)
    .forEach(node => {
      const clusterId = node.data.cluster_id
      if (!clusterGenes.has(clusterId)) {
        clusterGenes.set(clusterId, [])
      }
      clusterGenes.get(clusterId).push(node.data.gene_id)
    })

  // Build HPO lookup for O(1) access
  const hpoLookup = new Map()
  props.hpoClassifications.data.forEach(item => {
    hpoLookup.set(item.gene_id, item)
  })

  // Compute statistics for each cluster
  clusterGenes.forEach((geneIds, clusterId) => {
    stats.set(clusterId, computeHpoClusterStats(geneIds, hpoLookup))
  })

  window.logService?.info(`[ClusterStats] ✓ Computed statistics for ${stats.size} clusters`, {
    totalClusters: stats.size,
    avgHpoDataCoverage:
      Array.from(stats.values()).reduce((sum, s) => sum + parseFloat(s.hpoDataPercentage), 0) /
      stats.size
  })

  return stats
})

// Compute node colors based on color mode
const nodeColorMap = computed(() => {
  const colorMap = new Map()

  if (!props.networkData?.cytoscape_json?.elements) {
    return colorMap
  }

  const nodes = props.networkData.cytoscape_json.elements.filter(el => el.data.gene_id)

  // Cluster coloring (default)
  if (props.colorMode === 'cluster') {
    nodes.forEach(node => {
      const clusterId = node.data.cluster_id
      if (clusterId !== undefined && props.clusterColorsMap.has(clusterId)) {
        colorMap.set(node.data.gene_id, props.clusterColorsMap.get(clusterId))
      } else {
        colorMap.set(node.data.gene_id, DEFAULT_NODE_COLOR)
      }
    })
    return colorMap
  }

  // HPO-based coloring
  if (!props.hpoClassifications?.data) {
    // No HPO data available, use default color
    nodes.forEach(node => {
      colorMap.set(node.data.gene_id, OTHER_CLUSTER_COLOR)
    })
    return colorMap
  }

  // Create lookup map of gene_id -> classification
  const hpoLookup = new Map()
  props.hpoClassifications.data.forEach(item => {
    hpoLookup.set(item.gene_id, item)
  })

  // Get color schemes from config
  const colorSchemes = networkAnalysisConfig.nodeColoring.colorSchemes

  nodes.forEach(node => {
    const geneId = node.data.gene_id
    const classification = hpoLookup.get(geneId)

    if (!classification) {
      colorMap.set(geneId, colorSchemes[props.colorMode]?.null || OTHER_CLUSTER_COLOR)
      return
    }

    let value
    if (props.colorMode === 'clinical_group') {
      value = classification.clinical_group
    } else if (props.colorMode === 'onset_group') {
      value = classification.onset_group
    } else if (props.colorMode === 'syndromic') {
      value = classification.is_syndromic
    }

    const color =
      colorSchemes[props.colorMode]?.[value] ||
      colorSchemes[props.colorMode]?.null ||
      OTHER_CLUSTER_COLOR
    colorMap.set(geneId, color)
  })

  return colorMap
})

// Layout options
const layoutOptions = [
  { title: 'COSE Bilkent (Force-directed)', value: 'cose-bilkent' },
  { title: 'COSE (Force-directed)', value: 'cose' },
  { title: 'Circle', value: 'circle' },
  { title: 'Grid', value: 'grid' },
  { title: 'Concentric', value: 'concentric' }
]

// Tinted legend chip; text stays text-foreground so every cluster color passes contrast
const legendChipStyle = color => ({
  backgroundColor: `color-mix(in srgb, ${color} 20%, transparent)`,
  borderColor: color
})

// Methods
const getClusterDisplayName = backendClusterId => {
  if (!props.clusterIdMapping || props.clusterIdMapping.size === 0) {
    return `Cluster ${backendClusterId + 1}`
  }
  const displayId = props.clusterIdMapping.get(backendClusterId)
  return `Cluster ${(displayId ?? backendClusterId) + 1}`
}

const showTooltip = (node, event) => {
  const backendClusterId = node.data('cluster_id')
  const clusterName =
    backendClusterId !== undefined ? getClusterDisplayName(backendClusterId) : null

  // Look up HPO classification data for this gene
  const geneId = node.data('gene_id')
  let hpoData = null
  let hpoPercentages = null

  if (props.hpoClassifications?.data && geneId) {
    hpoData = props.hpoClassifications.data.find(item => item.gene_id === geneId)

    // Calculate percentages within cluster for context
    if (
      hpoData &&
      backendClusterId !== undefined &&
      clusterStatistics.value.has(backendClusterId)
    ) {
      const clusterStats = clusterStatistics.value.get(backendClusterId)

      hpoPercentages = {}

      // Clinical group percentage
      if (hpoData.clinical_group) {
        const stat = clusterStats.clinical.find(s => s.key === hpoData.clinical_group)
        if (stat) hpoPercentages.clinical = stat.percentage
      }

      // Onset group percentage
      if (hpoData.onset_group) {
        const stat = clusterStats.onset.find(s => s.key === hpoData.onset_group)
        if (stat) hpoPercentages.onset = stat.percentage
      }

      // Syndromic percentage
      if (hpoData.is_syndromic !== null) {
        hpoPercentages.syndromic = hpoData.is_syndromic
          ? clusterStats.syndromic.syndromicPercentage
          : clusterStats.syndromic.isolatedPercentage
      }
    }
  }

  tooltipData.value = {
    geneSymbol: node.data('label') || node.data('gene_id'),
    clusterName,
    hpoData,
    hpoPercentages
  }

  // Top-left corner at the bottom-right of the pointer, kept inside the canvas
  const width = cytoscapeContainer.value?.clientWidth ?? 0
  const x = (event.renderedPosition?.x || event.position?.x || 0) + 15
  tooltipX.value = width ? Math.max(0, Math.min(x, width - 260)) : x
  tooltipY.value = (event.renderedPosition?.y || event.position?.y || 0) + 15

  tooltipVisible.value = true
}

const hideTooltip = () => {
  tooltipVisible.value = false
}

const highlightCluster = clusterId => {
  if (!cyInstance.value || clusterId === undefined) return

  // Use batch for performance (prevents multiple redraws)
  cyInstance.value.batch(() => {
    const allNodes = cyInstance.value.nodes()
    const allEdges = cyInstance.value.edges()

    // Find nodes in the cluster
    const clusterNodes = allNodes.filter(node => node.data('cluster_id') === clusterId)

    // Find edges between cluster nodes
    const clusterEdges = allEdges.filter(edge => {
      const sourceCluster = edge.source().data('cluster_id')
      const targetCluster = edge.target().data('cluster_id')
      return sourceCluster === clusterId && targetCluster === clusterId
    })

    // Highlight cluster nodes and their edges
    clusterNodes.addClass('highlighted')
    clusterEdges.addClass('highlighted')

    // Dim everything else
    allNodes.difference(clusterNodes).addClass('dimmed')
    allEdges.difference(clusterEdges).addClass('dimmed')
  })
}

const clearHighlight = () => {
  if (!cyInstance.value) return

  // Use batch for performance
  cyInstance.value.batch(() => {
    cyInstance.value.elements().removeClass('highlighted dimmed')
  })
}

/**
 * Compute cluster centroids from node positions
 * O(N) complexity - very fast even for large networks
 * Called after layout completes (layoutstop event)
 */
const computeClusterCentroids = () => {
  if (!cyInstance.value) return

  const centroids = {}
  const clusterNodes = {} // { clusterId: [nodes...] }

  // Group nodes by cluster
  cyInstance.value.nodes().forEach(node => {
    const clusterId = node.data('cluster_id')
    if (clusterId === undefined) return

    if (!clusterNodes[clusterId]) {
      clusterNodes[clusterId] = []
    }
    clusterNodes[clusterId].push(node)
  })

  // Compute centroid for each cluster (average of all node positions)
  Object.entries(clusterNodes).forEach(([clusterId, nodes]) => {
    if (nodes.length === 0) return

    let sumX = 0
    let sumY = 0
    nodes.forEach(node => {
      const pos = node.position()
      sumX += pos.x
      sumY += pos.y
    })

    centroids[clusterId] = {
      x: sumX / nodes.length,
      y: sumY / nodes.length
    }
  })

  clusterCentroids.value = centroids
}

const openClusterDialog = backendClusterId => {
  if (!cyInstance.value || backendClusterId === undefined) return

  // Collect genes for this cluster
  const clusterNodes = cyInstance.value
    .nodes()
    .filter(node => node.data('cluster_id') === backendClusterId)

  const genes = clusterNodes.map(node => ({
    gene_id: node.data('gene_id'),
    hgnc_id: props.hgncIds.get(node.data('gene_id')) ?? null,
    symbol: node.data('label'),
    cluster_id: backendClusterId
  }))

  // Sort genes alphabetically by symbol
  genes.sort((a, b) => a.symbol.localeCompare(b.symbol))

  selectedClusterId.value = backendClusterId
  selectedClusterGenes.value = genes
  clusterDialogOpen.value = true

  // Emit event to select this cluster in enrichment analysis
  emit('selectCluster', backendClusterId)
}

const highlightGeneInNetwork = geneId => {
  if (!cyInstance.value) return

  // Find and highlight the specific gene
  const node = cyInstance.value.nodes().filter(n => n.data('gene_id') === geneId)

  if (node.length > 0) {
    // Center on the node and highlight it
    cyInstance.value.animate({
      fit: {
        eles: node,
        padding: 100
      },
      duration: 500
    })

    // Temporarily highlight the node
    node.addClass('highlighted')
    setTimeout(() => {
      node.removeClass('highlighted')
    }, 2000)
  }
}

/**
 * Search Methods
 */

const handleSearchInput = () => {
  // Clear existing timer
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }

  const pattern = localSearchPattern.value?.trim()

  // If empty, clear search immediately
  if (!pattern) {
    clearSearchHighlight()
    return
  }

  // Debounce search by 300ms to avoid searching on every keystroke
  searchDebounceTimer = setTimeout(() => {
    handleSearch(pattern)
  }, 300)
}

const handleSearch = pattern => {
  if (!cyInstance.value) {
    window.logService?.warn('[NetworkSearch] No cytoscape instance available')
    return
  }

  // Don't search if pattern is empty
  if (!pattern || !pattern.trim()) {
    return
  }

  // Perform search using composable (this will update matchCount)
  searchMatchedNodes.value = searchNodes(cyInstance.value, pattern)

  window.logService?.info(
    `[NetworkSearch] Found ${matchCount.value} matches for pattern "${pattern}"`
  )
}

const highlightSearchMatches = () => {
  if (!cyInstance.value || searchMatchedNodes.value.length === 0) {
    window.logService?.warn('[NetworkSearch] No matches to highlight')
    return
  }

  // Use batch for performance (single redraw)
  cyInstance.value.batch(() => {
    // Dim all nodes and edges
    cyInstance.value.nodes().addClass('dimmed')
    cyInstance.value.edges().addClass('dimmed')

    // Highlight matched nodes with orange border
    searchMatchedNodes.value.forEach(node => {
      node.addClass('search-match')
      node.removeClass('dimmed')

      // Also highlight edges connected to matched nodes
      const connectedEdges = node.connectedEdges()
      connectedEdges.forEach(edge => {
        // If both source and target are matched, highlight the edge
        const source = edge.source()
        const target = edge.target()
        const sourceMatched = searchMatchedNodes.value.includes(source)
        const targetMatched = searchMatchedNodes.value.includes(target)

        if (sourceMatched && targetMatched) {
          edge.addClass('search-edge-match')
          edge.removeClass('dimmed')
        }
      })
    })
  })

  window.logService?.info(`[NetworkSearch] Highlighted ${matchCount.value} matched nodes`)
}

const fitSearchMatches = () => {
  if (!cyInstance.value || searchMatchedNodes.value.length === 0) {
    window.logService?.warn('[NetworkSearch] No matches to fit')
    return
  }

  // Create collection of matched nodes
  const collection = cyInstance.value.collection(searchMatchedNodes.value)

  // Animate zoom/pan to fit matched nodes
  cyInstance.value.animate(
    {
      fit: {
        eles: collection,
        padding: 80
      },
      duration: 500,
      easing: 'ease-out-cubic'
    },
    {
      complete: () => {
        // Highlight after animation completes
        highlightSearchMatches()
      }
    }
  )

  window.logService?.info('[NetworkSearch] Fitted view to matched nodes')
}

const clearSearchHighlight = () => {
  if (!cyInstance.value) return

  // Use batch for performance
  cyInstance.value.batch(() => {
    cyInstance.value.elements().removeClass('search-match search-edge-match dimmed')
  })

  searchMatchedNodes.value = []
  localSearchPattern.value = ''
  clearSearch()

  window.logService?.debug('[NetworkSearch] Cleared search highlights')
}

const initializeCytoscape = () => {
  if (!cytoscapeContainer.value || !props.networkData) return

  // Extract cluster colors if present
  const colors = {}
  if (props.networkData.cytoscape_json?.elements) {
    props.networkData.cytoscape_json.elements.forEach(element => {
      const clusterId = element.data?.cluster_id
      // Size-ranked token colours from the parent; the backend's hex palette is ignored (#325)
      if (clusterId !== undefined) {
        colors[clusterId] = props.clusterColorsMap.get(clusterId) ?? OTHER_CLUSTER_COLOR
      }
    })
  }
  clusterColors.value = colors

  // Initialize Cytoscape
  cyInstance.value = cytoscape({
    container: cytoscapeContainer.value,
    elements: props.networkData.cytoscape_json?.elements || [],
    style: buildStylesheet(),
    layout: {
      name: layoutType.value,
      animate: true,
      animationDuration: 500
    },
    // Performance optimizations
    hideEdgesOnViewport: true, // Hide edges during pan/zoom for better performance
    pixelRatio: 1, // Use standard pixel ratio for better performance
    minZoom: 0.1,
    maxZoom: 5
  })

  // Add event listeners
  // Node click event
  cyInstance.value.on('tap', 'node', event => {
    const node = event.target
    emit('nodeClick', {
      gene_id: node.data('gene_id'),
      label: node.data('label'),
      cluster_id: node.data('cluster_id')
    })
  })

  // Node hover events for cluster highlighting and tooltip
  cyInstance.value.on('mouseover', 'node', event => {
    if (cytoscapeContainer.value) cytoscapeContainer.value.style.cursor = 'pointer'
    highlightCluster(event.target.data('cluster_id'))
    showTooltip(event.target, event)
  })

  cyInstance.value.on('mouseout', 'node', () => {
    if (cytoscapeContainer.value) cytoscapeContainer.value.style.cursor = ''
    clearHighlight()
    hideTooltip()
  })

  // Layout completion event - compute centroids after layout finishes
  cyInstance.value.on('layoutstop', () => {
    computeClusterCentroids()
  })

  // Auto-fit on load
  nextTick(() => {
    fitGraph()
  })
}

const nodeColor = ele => nodeColorMap.value.get(ele.data('gene_id')) || DEFAULT_NODE_COLOR

/** Stylesheet from theme tokens; canvasColor() turns them into colours Cytoscape can parse */
const buildStylesheet = () => {
  const highlight = canvasColor(networkAnalysisConfig.search.highlightColor)
  const edge = canvasColor('var(--muted-foreground)')
  return [
    {
      selector: 'node',
      style: {
        'background-color': ele => canvasColor(nodeColor(ele)),
        // Outline keeps light fills (e.g. the yellow series) >= 3:1 on the canvas
        'border-width': 1,
        'border-color': ele => canvasColor(markOutline(nodeColor(ele))),
        label: 'data(label)',
        width: 40,
        height: 40,
        'font-size': 12,
        'text-valign': 'center',
        'text-halign': 'center',
        'text-outline-width': 2,
        'text-outline-color': canvasColor('var(--background)'),
        'min-zoomed-font-size': 8,
        color: canvasColor('var(--foreground)'),
        'transition-property': 'border-width, border-color, opacity, overlay-opacity',
        'transition-duration': '0.2s'
      }
    },
    {
      selector: 'node.highlighted, node.search-match',
      style: {
        'border-width': 5,
        'border-color': highlight,
        'border-opacity': 1,
        'overlay-color': highlight,
        'overlay-opacity': 0.2,
        'overlay-padding': 12,
        'z-index': 999
      }
    },
    {
      selector: 'node.dimmed',
      style: {
        opacity: 0.25,
        'text-opacity': 0.25
      }
    },
    {
      selector: 'edge',
      style: {
        width: ele => Math.max(1, (ele.data('weight') || 0.5) * 5),
        'line-color': edge,
        'target-arrow-color': edge,
        opacity: 0.35,
        'curve-style': 'bezier',
        'transition-property': 'line-color, width, opacity',
        'transition-duration': '0.2s'
      }
    },
    {
      selector: 'edge.highlighted, edge.search-edge-match',
      style: {
        'line-color': highlight,
        'target-arrow-color': highlight,
        width: 4,
        opacity: 1,
        'z-index': 999
      }
    },
    {
      selector: 'edge.dimmed',
      style: {
        opacity: 0.1
      }
    },
    {
      selector: 'node:selected',
      style: {
        'border-width': 3,
        'border-color': canvasColor('var(--foreground)')
      }
    }
  ]
}

const destroyCytoscape = () => {
  if (cyInstance.value) {
    const instance = cyInstance.value
    cyInstance.value = null // Null ref FIRST to prevent watchers from using destroyed instance
    instance.destroy()
  }
}

const applyLayout = () => {
  if (!cyInstance.value) return

  const layout = cyInstance.value.layout({
    name: layoutType.value,
    animate: true,
    animationDuration: 500,
    // COSE Bilkent specific options
    ...(layoutType.value === 'cose-bilkent' && {
      quality: 'default',
      randomize: false,
      idealEdgeLength: 100,
      edgeElasticity: 0.45,
      nestingFactor: 0.1,
      gravity: 0.25,
      numIter: 2500,
      tile: true,
      tilingPaddingVertical: 10,
      tilingPaddingHorizontal: 10
    })
  })

  layout.run()
}

const fitGraph = () => {
  if (cyInstance.value) {
    cyInstance.value.fit(null, 50)
  }
}

const exportGraph = () => {
  if (!cyInstance.value) return

  const png = cyInstance.value.png({
    output: 'blob',
    bg: canvasColor('var(--background)'),
    full: true,
    scale: 2
  })

  const link = document.createElement('a')
  link.href = URL.createObjectURL(png)
  link.download = `network_${Date.now()}.png`
  link.click()
}

// Watchers
watch(
  () => props.networkData,
  newData => {
    destroyCytoscape()
    if (newData) {
      // Double nextTick + rAF ensures the container is fully rendered
      // before Cytoscape tries to measure it
      nextTick(() => {
        window.requestAnimationFrame(() => {
          initializeCytoscape()
        })
      })
    }
  }
)

// Watch for color mode or HPO classification changes and update node colors
watch([() => props.colorMode, () => props.hpoClassifications], ([newColorMode], [oldColorMode]) => {
  window.logService?.info('[NetworkGraph] Color mode or HPO data changed', {
    colorMode: newColorMode,
    oldColorMode,
    hasHPOData: !!props.hpoClassifications?.data,
    hpoDataCount: props.hpoClassifications?.data?.length || 0,
    hasCyInstance: !!cyInstance.value
  })

  if (!cyInstance.value || cyInstance.value.destroyed()) {
    window.logService?.warn('[NetworkGraph] No cytoscape instance, skipping color update')
    return
  }

  const nodeCount = cyInstance.value.nodes().length
  let updatedCount = 0

  // Update node colors based on new color map
  try {
    cyInstance.value.nodes().forEach(node => {
      const color = nodeColor(node)
      node.style({
        'background-color': canvasColor(color),
        'border-color': canvasColor(markOutline(color))
      })
      updatedCount++
    })
  } catch {
    // Cytoscape instance may be in a transitional state during destroy/recreate
    window.logService?.warn('[NetworkGraph] Skipped color update — instance transitioning')
    return
  }

  window.logService?.info(
    `[NetworkGraph] ✓ Updated colors for ${updatedCount}/${nodeCount} nodes`,
    {
      colorMode: newColorMode,
      uniqueColors: new Set([...nodeColorMap.value.values()]).size
    }
  )
})

// Theme switch: re-resolve the token colours for the canvas
watch(isDark, () => {
  clearCanvasColors()
  if (cyInstance.value && !cyInstance.value.destroyed()) {
    cyInstance.value.style(buildStylesheet())
  }
})

// Lifecycle
onMounted(async () => {
  if (props.networkData) {
    await nextTick()
    initializeCytoscape()
  }
})

onUnmounted(() => {
  // Cleanup search debounce timer to prevent memory leaks
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
    searchDebounceTimer = null
  }

  destroyCytoscape()
})
</script>

<style scoped>
.network-graph-card {
  position: relative;
}

.network-container-wrapper {
  position: relative;
  width: 100%;
}

.cytoscape-container {
  width: 100%;
  background-color: var(--background);
  border-radius: 4px;
  position: relative;
}

.cluster-chip {
  cursor: pointer;
  transition: filter 0.2s;
}

.cluster-chip:hover {
  filter: brightness(0.95);
}

/* Node tooltip: popover tokens in both themes */
.node-tooltip {
  position: absolute;
  max-width: 260px;
  background: var(--popover);
  color: var(--popover-foreground);
  border: 1px solid var(--border);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  pointer-events: none;
  z-index: 50;
  white-space: nowrap;
}

.tooltip-gene {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}

.tooltip-cluster {
  font-size: 12px;
  color: var(--muted-foreground);
  font-weight: 500;
}

.tooltip-hpo {
  margin-top: 8px;
  font-size: 12px;
}

.tooltip-hpo-divider {
  height: 1px;
  background: var(--border);
  margin: 6px 0;
}

.tooltip-hpo-section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--muted-foreground);
  margin-bottom: 4px;
}

.tooltip-hpo-item {
  line-height: 1.6;
  margin-bottom: 2px;
}

.tooltip-hpo-label {
  font-weight: 600;
  margin-right: 4px;
}

.tooltip-cluster-context {
  margin-top: 4px;
}

.tooltip-context-item {
  line-height: 1.6;
  margin-bottom: 2px;
  display: flex;
  align-items: baseline;
}

.tooltip-context-percent {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  margin-right: 6px;
  min-width: 42px;
}

.tooltip-context-label {
  color: var(--muted-foreground);
}
</style>
