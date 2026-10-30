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
      <div class="flex items-center gap-1">
        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button
              variant="ghost"
              size="sm"
              class="h-8 gap-1.5 px-2"
              :disabled="!cyInstance || layingOut"
            >
              <Download class="size-4" aria-hidden="true" />
              Export
              <ChevronDown class="size-3.5 text-muted-foreground" aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" class="w-60">
            <DropdownMenuLabel class="text-xs text-muted-foreground">Image</DropdownMenuLabel>
            <DropdownMenuItem @click="exportPng">
              <FileImage aria-hidden="true" />
              PNG<span class="ml-auto text-xs text-muted-foreground">high resolution</span>
            </DropdownMenuItem>
            <DropdownMenuItem @click="exportSvg">
              <FileImage aria-hidden="true" />
              SVG<span class="ml-auto text-xs text-muted-foreground">vector</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuLabel class="text-xs text-muted-foreground"
              >Network data</DropdownMenuLabel
            >
            <DropdownMenuItem @click="exportData('cyjs')">
              <FileJson aria-hidden="true" />
              Cytoscape JSON<span class="ml-auto text-xs text-muted-foreground">.cyjs</span>
            </DropdownMenuItem>
            <DropdownMenuItem @click="exportData('graphml')">
              <FileCode aria-hidden="true" />
              GraphML<span class="ml-auto text-xs text-muted-foreground">.graphml</span>
            </DropdownMenuItem>
            <DropdownMenuItem @click="exportData('nodes')">
              <FileSpreadsheet aria-hidden="true" />
              Nodes<span class="ml-auto text-xs text-muted-foreground">.csv</span>
            </DropdownMenuItem>
            <DropdownMenuItem @click="exportData('edges')">
              <FileSpreadsheet aria-hidden="true" />
              Edges<span class="ml-auto text-xs text-muted-foreground">.csv</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <TooltipProvider>
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
          <span v-if="searchError" class="text-sm text-destructive" role="alert">
            {{ searchError }}
          </span>
          <span
            v-else-if="localSearchPattern && hasPattern && matchCount === 0"
            class="text-sm text-muted-foreground"
            aria-live="polite"
          >
            No genes match “{{ searchPattern }}”
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
        role="img"
        :aria-label="graphSummary"
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
        v-if="loading || layingOut"
        class="absolute inset-0 flex items-center justify-center"
        :class="loading ? 'bg-muted/40' : 'pointer-events-none'"
        role="status"
      >
        <p
          class="flex items-center gap-2 rounded-md bg-background/90 px-3 py-2 text-sm text-muted-foreground shadow-sm"
        >
          <LoaderCircle class="size-5 motion-safe:animate-spin" aria-hidden="true" />
          {{ loading ? 'Building the network…' : 'Laying out the network…' }}
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
        v-if="!loading && !error && !hasElements"
        class="absolute inset-0 flex items-center justify-center"
      >
        <div class="text-center text-muted-foreground">
          <NetworkIcon class="size-12 mb-3 mx-auto" aria-hidden="true" />
          <p class="text-base font-medium text-foreground">No interactions to show</p>
          <p class="text-sm">Build a network to see its protein-protein interactions.</p>
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
            <span
              class="size-2.5 shrink-0 rounded-full border"
              :style="swatchStyle(item.color)"
              aria-hidden="true"
            />
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
                  class="cluster-chip min-h-6 cursor-pointer focus-visible:ring-ring focus-visible:outline-none"
                  :class="item.isActive ? 'text-foreground' : 'text-muted-foreground'"
                  :style="item.isActive ? legendChipStyle(item.color) : {}"
                  :aria-label="`${item.label}, ${item.size} genes. Open cluster details`"
                  @mouseenter="highlightCluster(item.id)"
                  @mouseleave="clearHighlight()"
                  @focus="highlightCluster(item.id)"
                  @blur="clearHighlight()"
                  @click="openClusterDialog(item.id)"
                  @keydown.enter.prevent="openClusterDialog(item.id)"
                  @keydown.space.prevent="openClusterDialog(item.id)"
                >
                  <span
                    v-if="item.isActive"
                    class="size-2.5 shrink-0 border"
                    :class="
                      item.shape === 'round-diamond' ? 'rotate-45 rounded-[2px]' : 'rounded-full'
                    "
                    :style="swatchStyle(item.color)"
                    aria-hidden="true"
                  />
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
import { ref, shallowRef, markRaw, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  ArrowUpDown,
  CheckSquare,
  ChevronDown,
  Database,
  Download,
  FileCode,
  FileImage,
  FileJson,
  FileSpreadsheet,
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
import { toast } from 'vue-sonner'

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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { DataState } from '@/components/shared'
import { useAppTheme } from '@/composables/useAppTheme'
import { downloadFile, isoDate } from '@/utils/csv'
import { cyjs, edgesCsv, graphml, nodesCsv } from '@/utils/networkExport'
import { markOutline } from '../visualizations/chartMarks'
import { canvasColor, clearCanvasColors } from './canvasColor'
import { clusterStyle } from './clusterPalette'

import ClusterDetailsDialog from './ClusterDetailsDialog.vue'
import { useNetworkSearch } from '../../composables/useNetworkSearch'
import { networkAnalysisConfig, OTHER_CLUSTER_COLOR } from '../../config/networkAnalysis'
import { computeHpoClusterStats } from './hpoClusterStats'

// Nodes before clustering, and anything without a category, stay neutral
const DEFAULT_NODE_COLOR = 'var(--muted-foreground)'
// Above this many nodes the layout jumps straight to its result: animating it costs more than it shows
const ANIMATE_MAX_NODES = 200

// Register cose-bilkent layout
cytoscape.use(coseBilkent)

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

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
  /** Kept for compatibility; cluster colours now come from clusterPalette.ts by size rank */
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
  },
  /** Clusters smaller than this are drawn neutral grey */
  minClusterSize: {
    type: Number,
    default: networkAnalysisConfig.filtering.defaultMinClusterSize
  }
})

const { isDark } = useAppTheme()

// Emits
const emit = defineEmits(['refresh', 'update:colorMode', 'nodeClick', 'selectCluster'])

// Refs. Cytoscape objects are never made reactive: a deep proxy over the graph is slow and
// breaks Cytoscape's identity checks
const cytoscapeContainer = ref(null)
const cyInstance = shallowRef(null)
const layingOut = ref(false)
const layoutType = ref('cose-bilkent')
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
const { matchCount, searchNodes, clearSearch, searchError, searchPattern, hasPattern } =
  useNetworkSearch()
const searchMatches = shallowRef(null) // Cytoscape collection
const localSearchPattern = ref('')

// Debounce timer for auto-search
let searchDebounceTimer = null
// Per-cluster node/edge collections, rebuilt per network
let clusterIndex = new Map()
let highlightedCluster
let currentLayout = null
let renderToken = 0

// Computed
const graphHeight = computed(() => props.height)

const elements = computed(() => props.networkData?.cytoscape_json?.elements ?? [])
const hasElements = computed(() => elements.value.length > 0)

const networkStats = computed(() => {
  if (!props.networkData) return 'No network loaded'
  const { nodes, edges, components } = props.networkData
  return `Displayed: ${nodes} genes, ${edges} interactions, ${components} component(s)`
})

// Genes per cluster, for the legend chips and colour ranks
const clusterSizes = computed(() => {
  const sizes = new Map()
  for (const el of elements.value) {
    const id = el.data?.cluster_id
    if (el.data?.gene_id && id !== undefined && id !== null) sizes.set(id, (sizes.get(id) ?? 0) + 1)
  }
  return sizes
})

// Size rank per backend cluster id (0 = largest); the parent's mapping wins when given
const clusterRanks = computed(() => {
  if (props.clusterIdMapping?.size) return props.clusterIdMapping
  const bySize = [...clusterSizes.value].sort((a, b) => b[1] - a[1] || a[0] - b[0])
  return new Map(bySize.map(([id], rank) => [id, rank]))
})

// One source of truth for graph, legend and dialog colours: { color, shape } per cluster
const clusterStyles = computed(
  () =>
    new Map(
      [...clusterSizes.value].map(([id, size]) => [
        id,
        clusterStyle(clusterRanks.value.get(id) ?? -1, size, props.minClusterSize)
      ])
    )
)

const graphSummary = computed(() => {
  const n = props.networkData?.nodes ?? 0
  const m = props.networkData?.edges ?? 0
  const k = clusterStyles.value.size
  return `Protein-protein interaction network: ${n} genes, ${m} interactions${k ? `, ${k} clusters` : ''}. Gene lists are available from the cluster legend and the export menu.`
})

// Legend visibility - show if clusters exist OR HPO data exists
const showLegend = computed(() => {
  const hasHPOData = props.hpoClassifications?.data && props.hpoClassifications.data.length > 0
  return clusterStyles.value.size > 0 || hasHPOData
})

// Sort clusters by display rank or spatial proximity; an array keeps the order
const sortedClusters = computed(() => {
  const clusters = [...clusterStyles.value].map(([backendId, style]) => ({
    backendId,
    displayId: clusterRanks.value.get(backendId) ?? backendId,
    ...style,
    centroid: clusterCentroids.value[backendId] || null
  }))

  if (clusterSortMethod.value === 'spatial' && Object.keys(clusterCentroids.value).length > 0) {
    // Spatial sorting: by angle from center (clockwise from top)
    clusters.sort((a, b) => {
      if (!a.centroid || !b.centroid) return 0
      const angleA = Math.atan2(a.centroid.y, a.centroid.x) + Math.PI
      const angleB = Math.atan2(b.centroid.y, b.centroid.x) + Math.PI
      return angleA - angleB
    })
  } else {
    clusters.sort((a, b) => a.displayId - b.displayId)
  }
  return clusters
})

// Cluster legend items (always available when clusters exist)
const clusterLegendItems = computed(() =>
  sortedClusters.value.map(cluster => ({
    label: getClusterDisplayName(cluster.backendId),
    size: clusterSizes.value.get(cluster.backendId) ?? 0,
    color: cluster.color,
    shape: cluster.shape,
    id: cluster.backendId,
    type: 'cluster',
    isActive: props.colorMode === 'cluster'
  }))
)

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

// Legend title based on color mode
const legendTitle = computed(() => {
  const mode = networkAnalysisConfig.nodeColoring.modes.find(m => m.value === props.colorMode)
  return mode?.label || 'Legend'
})

const selectedClusterColor = computed(
  () => clusterStyles.value.get(selectedClusterId.value)?.color ?? OTHER_CLUSTER_COLOR
)

// gene_id -> HPO classification, for O(1) lookups on hover and per cluster
const hpoLookup = computed(
  () => new Map((props.hpoClassifications?.data ?? []).map(item => [item.gene_id, item]))
)

// Compute HPO classification statistics per cluster for hover tooltips
const clusterStatistics = computed(() => {
  const stats = new Map()
  if (!elements.value.length || !props.hpoClassifications?.data) return stats

  const clusterGenes = new Map()
  for (const node of elements.value) {
    const { gene_id: geneId, cluster_id: clusterId } = node.data ?? {}
    if (!geneId || clusterId === undefined) continue
    if (!clusterGenes.has(clusterId)) clusterGenes.set(clusterId, [])
    clusterGenes.get(clusterId).push(geneId)
  }
  clusterGenes.forEach((geneIds, clusterId) => {
    stats.set(clusterId, computeHpoClusterStats(geneIds, hpoLookup.value))
  })
  return stats
})

// Node colour (token or hex) per gene for the current colour mode
const nodeColorMap = computed(() => {
  const colorMap = new Map()
  const nodes = elements.value.filter(el => el.data?.gene_id)

  if (props.colorMode === 'cluster') {
    for (const { data } of nodes) {
      colorMap.set(
        data.gene_id,
        clusterStyles.value.get(data.cluster_id)?.color ?? DEFAULT_NODE_COLOR
      )
    }
    return colorMap
  }

  const scheme = networkAnalysisConfig.nodeColoring.colorSchemes[props.colorMode]
  const field = {
    clinical_group: 'clinical_group',
    onset_group: 'onset_group',
    syndromic: 'is_syndromic'
  }[props.colorMode]
  for (const { data } of nodes) {
    const classification = hpoLookup.value.get(data.gene_id)
    const value = classification?.[field]
    colorMap.set(data.gene_id, scheme?.[value] || scheme?.null || OTHER_CLUSTER_COLOR)
  }
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
  borderColor: markOutline(color)
})
const swatchStyle = color => ({ backgroundColor: color, borderColor: markOutline(color) })

// Methods
const getClusterDisplayName = backendClusterId => {
  const displayId = clusterRanks.value.get(backendClusterId)
  return `Cluster ${(displayId ?? backendClusterId) + 1}`
}

const showTooltip = (node, event) => {
  const backendClusterId = node.data('cluster_id')
  const clusterName =
    backendClusterId !== undefined ? getClusterDisplayName(backendClusterId) : null

  const geneId = node.data('gene_id')
  const hpoData = (geneId && hpoLookup.value.get(geneId)) || null
  let hpoPercentages = null

  // Percentages within the cluster, for context
  if (hpoData && backendClusterId !== undefined && clusterStatistics.value.has(backendClusterId)) {
    const clusterStats = clusterStatistics.value.get(backendClusterId)
    hpoPercentages = {}
    if (hpoData.clinical_group) {
      const stat = clusterStats.clinical.find(s => s.key === hpoData.clinical_group)
      if (stat) hpoPercentages.clinical = stat.percentage
    }
    if (hpoData.onset_group) {
      const stat = clusterStats.onset.find(s => s.key === hpoData.onset_group)
      if (stat) hpoPercentages.onset = stat.percentage
    }
    if (hpoData.is_syndromic !== null) {
      hpoPercentages.syndromic = hpoData.is_syndromic
        ? clusterStats.syndromic.syndromicPercentage
        : clusterStats.syndromic.isolatedPercentage
    }
  }

  tooltipData.value = {
    geneSymbol: node.data('label') || node.data('gene_id'),
    clusterName,
    hpoData,
    hpoPercentages
  }

  // Top-left corner at the bottom-right of the pointer (or node), kept inside the canvas
  const pos = event.renderedPosition ?? node.renderedPosition()
  const width = cytoscapeContainer.value?.clientWidth ?? 0
  const x = (pos?.x || 0) + 15
  tooltipX.value = width ? Math.max(0, Math.min(x, width - 260)) : x
  tooltipY.value = (pos?.y || 0) + 15
  tooltipVisible.value = true
}

const hideTooltip = () => {
  tooltipVisible.value = false
}

/** Nodes, intra-cluster edges and both, cached per cluster for the current network */
const clusterElements = clusterId => {
  const cy = cyInstance.value
  if (!cy || clusterId === undefined || clusterId === null) return null
  let entry = clusterIndex.get(clusterId)
  if (!entry) {
    const nodes = cy.nodes(`[cluster_id = ${Number(clusterId)}]`)
    const edges = nodes.edgesWith(nodes)
    entry = { nodes, edges, all: nodes.union(edges) }
    clusterIndex.set(clusterId, entry)
  }
  return entry
}

const highlightCluster = clusterId => {
  const cy = cyInstance.value
  if (!cy || clusterId === undefined || clusterId === highlightedCluster) return
  const entry = clusterElements(clusterId)
  if (!entry) return
  highlightedCluster = clusterId
  cy.batch(() => {
    cy.elements().removeClass('highlighted dimmed')
    entry.all.addClass('highlighted')
    cy.elements().not(entry.all).addClass('dimmed')
  })
}

const clearHighlight = () => {
  const cy = cyInstance.value
  highlightedCluster = undefined
  if (!cy) return
  cy.batch(() => {
    cy.elements().removeClass('highlighted dimmed')
  })
}

/** Cluster centroids from node positions, after each layout */
const computeClusterCentroids = () => {
  if (!cyInstance.value) return
  const sums = {}
  cyInstance.value.nodes().forEach(node => {
    const clusterId = node.data('cluster_id')
    if (clusterId === undefined) return
    const pos = node.position()
    const s = (sums[clusterId] ??= { x: 0, y: 0, n: 0 })
    s.x += pos.x
    s.y += pos.y
    s.n++
  })
  clusterCentroids.value = Object.fromEntries(
    Object.entries(sums).map(([id, s]) => [id, { x: s.x / s.n, y: s.y / s.n }])
  )
}

const openClusterDialog = backendClusterId => {
  const entry = clusterElements(backendClusterId)
  if (!entry) return

  // Intra-cluster degree: hubs first, then by symbol
  const genes = entry.nodes.map(node => ({
    gene_id: node.data('gene_id'),
    hgnc_id: props.hgncIds.get(node.data('gene_id')) ?? null,
    symbol: node.data('label'),
    cluster_id: backendClusterId,
    degree: node.neighborhood('node').intersection(entry.nodes).length
  }))
  genes.sort((a, b) => b.degree - a.degree || a.symbol.localeCompare(b.symbol))

  selectedClusterId.value = backendClusterId
  selectedClusterGenes.value = genes
  clusterDialogOpen.value = true

  // Emit event to select this cluster in enrichment analysis
  emit('selectCluster', backendClusterId)
}

const highlightGeneInNetwork = geneId => {
  const cy = cyInstance.value
  if (!cy) return
  const node = cy.nodes(`[gene_id = ${Number(geneId)}]`)
  if (node.length === 0) return
  cy.animate({ fit: { eles: node, padding: 100 }, duration: prefersReducedMotion() ? 0 : 500 })
  node.addClass('highlighted')
  setTimeout(() => node.removeClass('highlighted'), 2000)
}

/**
 * Search Methods
 */

const handleSearchInput = () => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  const pattern = localSearchPattern.value?.trim()
  if (!pattern) {
    clearSearchHighlight()
    return
  }
  // Debounce search by 300ms to avoid searching on every keystroke
  searchDebounceTimer = setTimeout(() => handleSearch(pattern), 300)
}

const removeSearchClasses = () => {
  cyInstance.value?.elements().removeClass('search-match search-edge-match search-dimmed')
}

const handleSearch = pattern => {
  const cy = cyInstance.value
  if (!cy || !pattern || !pattern.trim()) return
  // A new search starts from a clean graph, not on top of the previous highlight
  removeSearchClasses()
  searchMatches.value = markRaw(cy.collection(searchNodes(cy, pattern)))
}

const highlightSearchMatches = () => {
  const cy = cyInstance.value
  const matches = searchMatches.value
  if (!cy || !matches || matches.length === 0) return
  const edges = matches.edgesWith(matches)
  cy.batch(() => {
    removeSearchClasses()
    cy.elements().not(matches.union(edges)).addClass('search-dimmed')
    matches.addClass('search-match')
    edges.addClass('search-edge-match')
  })
}

const fitSearchMatches = () => {
  const cy = cyInstance.value
  const matches = searchMatches.value
  if (!cy || !matches || matches.length === 0) return
  cy.animate(
    {
      fit: { eles: matches, padding: 80 },
      duration: prefersReducedMotion() ? 0 : 500,
      easing: 'ease-out-cubic'
    },
    { complete: highlightSearchMatches }
  )
}

const clearSearchHighlight = () => {
  if (cyInstance.value) cyInstance.value.batch(removeSearchClasses)
  searchMatches.value = null
  localSearchPattern.value = ''
  clearSearch()
}

/** Write each node's resolved colour, outline and shape into its data for 'data(...)' styles */
const applyNodeStyles = () => {
  const cy = cyInstance.value
  if (!cy || cy.destroyed()) return
  const byCluster = props.colorMode === 'cluster'
  cy.batch(() => {
    cy.nodes().forEach(node => {
      const color = nodeColorMap.value.get(node.data('gene_id')) || DEFAULT_NODE_COLOR
      node.data({
        color: canvasColor(color),
        outline: canvasColor(markOutline(color)),
        shape: (byCluster && clusterStyles.value.get(node.data('cluster_id'))?.shape) || 'ellipse'
      })
    })
  })
}

/** Stylesheet from theme tokens; canvasColor() turns them into colours Cytoscape can parse */
const buildStylesheet = () => {
  const highlight = canvasColor(networkAnalysisConfig.search.highlightColor)
  const edge = canvasColor('var(--muted-foreground)')
  const transition = prefersReducedMotion() ? '0s' : '0.2s'
  return [
    {
      selector: 'node',
      style: {
        'background-color': 'data(color)',
        // Outline keeps light fills (e.g. the yellow series) >= 3:1 on the canvas
        'border-width': 1,
        'border-color': 'data(outline)',
        shape: 'data(shape)',
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
        'transition-duration': transition
      }
    },
    {
      selector: 'node.highlighted, node.search-match',
      style: {
        'border-width': 5,
        'border-color': highlight,
        'border-opacity': 1,
        'overlay-opacity': 0,
        'z-index': 999
      }
    },
    {
      selector: 'node.dimmed, node.search-dimmed',
      style: {
        opacity: 0.25,
        'text-opacity': 0.25
      }
    },
    {
      selector: 'edge',
      style: {
        // Equals max(1, weight * 5) for weights in 0-1, without a per-edge function
        width: 'mapData(weight, 0.2, 1, 1, 5)',
        'line-color': edge,
        opacity: 0.35,
        // Undirected, single edges: haystack draws straight lines far cheaper than bezier
        'curve-style': 'haystack',
        'transition-property': 'line-color, width, opacity',
        'transition-duration': transition
      }
    },
    {
      selector: 'edge.highlighted, edge.search-edge-match',
      style: {
        'line-color': highlight,
        width: 4,
        opacity: 1,
        'z-index': 999
      }
    },
    {
      selector: 'edge.dimmed, edge.search-dimmed',
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

/** One options object for the first layout and every layout switch */
const layoutConfig = (name, nodeCount, initial) => {
  const animate = nodeCount <= ANIMATE_MAX_NODES && !prefersReducedMotion()
  return {
    name,
    animate,
    animationDuration: 500,
    fit: true,
    padding: 50,
    ...(name === 'cose-bilkent' && {
      animate: animate ? 'end' : false,
      quality: 'default',
      // Fresh elements sit at the origin; only a layout switch starts from current positions
      randomize: initial,
      idealEdgeLength: 100,
      edgeElasticity: 0.45,
      nestingFactor: 0.1,
      gravity: 0.25,
      numIter: 2500,
      tile: true,
      tilingPaddingVertical: 10,
      tilingPaddingHorizontal: 10
    })
  }
}

// Resolves after the browser has painted, so the "Laying out" state shows before a blocking layout
const afterPaint = () =>
  new Promise(resolve => (window.requestAnimationFrame ?? setTimeout)(() => setTimeout(resolve)))

const runLayout = async (initial = false) => {
  const cy = cyInstance.value
  if (!cy) return
  currentLayout?.stop()
  const token = renderToken
  layingOut.value = true
  await afterPaint()
  if (cy !== cyInstance.value || token !== renderToken || cy.destroyed()) return
  const layout = cy.layout(layoutConfig(layoutType.value, cy.nodes().length, initial))
  currentLayout = layout
  layout.one('layoutstop', () => {
    if (currentLayout !== layout) return
    currentLayout = null
    layingOut.value = false
    computeClusterCentroids()
  })
  layout.run()
}

const applyLayout = () => runLayout(false)

const bindEvents = cy => {
  cy.on('tap', 'node', event => {
    const node = event.target
    showTooltip(node, event) // touch has no hover: a tap shows the same details
    emit('nodeClick', {
      gene_id: node.data('gene_id'),
      label: node.data('label'),
      cluster_id: node.data('cluster_id')
    })
  })
  cy.on('tap', event => {
    if (event.target === cy) hideTooltip()
  })
  cy.on('mouseover', 'node', event => {
    if (cytoscapeContainer.value) cytoscapeContainer.value.style.cursor = 'pointer'
    highlightCluster(event.target.data('cluster_id'))
    showTooltip(event.target, event)
  })
  cy.on('mouseout', 'node', () => {
    if (cytoscapeContainer.value) cytoscapeContainer.value.style.cursor = ''
    clearHighlight()
    hideTooltip()
  })
}

/** Show props.networkData: reuse the instance, replace its elements, lay out once */
const renderNetwork = () => {
  const elementsJson = elements.value
  if (!props.networkData || !cytoscapeContainer.value) {
    destroyCytoscape()
    return
  }
  clusterIndex = new Map()
  highlightedCluster = undefined
  hideTooltip()
  clearSearchHighlight()

  if (!cyInstance.value) {
    const cy = cytoscape({
      container: cytoscapeContainer.value,
      elements: elementsJson,
      style: buildStylesheet(),
      hideEdgesOnViewport: true, // Hide edges during pan/zoom for better performance
      pixelRatio: 1,
      minZoom: 0.1,
      maxZoom: 5
    })
    bindEvents(cy)
    cyInstance.value = markRaw(cy)
  } else {
    const cy = cyInstance.value
    currentLayout?.stop()
    cy.batch(() => {
      cy.elements().remove()
      cy.add(elementsJson)
    })
    cy.resize()
  }
  applyNodeStyles()
  runLayout(true)
}

const scheduleRender = () => {
  const token = ++renderToken
  nextTick(() =>
    (window.requestAnimationFrame ?? setTimeout)(() => {
      if (token === renderToken) renderNetwork()
    })
  )
}

const destroyCytoscape = () => {
  currentLayout?.stop()
  currentLayout = null
  layingOut.value = false
  clusterIndex = new Map()
  if (cyInstance.value) {
    const instance = cyInstance.value
    cyInstance.value = null // Null ref FIRST to prevent watchers from using destroyed instance
    instance.destroy()
  }
}

const fitGraph = () => {
  cyInstance.value?.fit(null, 50)
}

/**
 * Export
 */

const exportBaseName = () =>
  `kgdb_network_${cyInstance.value?.nodes().length ?? 0}genes_${isoDate()}`

const exportPng = () => {
  const cy = cyInstance.value
  if (!cy) return
  // 3x for print, capped so large networks stay under browser canvas limits (Cytoscape
  // ignores maxWidth/maxHeight once a scale is given)
  const { w, h } = cy.elements().boundingBox()
  const png = cy.png({
    output: 'blob',
    bg: canvasColor('var(--background)'),
    full: true,
    scale: Math.min(3, 8000 / Math.max(w, h, 1))
  })
  downloadFile(png, `${exportBaseName()}.png`, 'image/png')
}

let svgRegistered = false
const exportSvg = async () => {
  const cy = cyInstance.value
  if (!cy) return
  try {
    if (!svgRegistered) {
      const { default: svgExtension } = await import('cytoscape-svg')
      cytoscape.use(svgExtension)
      svgRegistered = true
    }
    const svg = cy.svg({ full: true, scale: 1, bg: canvasColor('var(--background)') })
    downloadFile(svg, `${exportBaseName()}.svg`, 'image/svg+xml')
  } catch (error) {
    toast.error('Could not export the network as SVG')
    window.logService?.error('[NetworkGraph] SVG export failed', { error: String(error) })
  }
}

const exportData = format => {
  const cy = cyInstance.value
  if (!cy) return
  const json = cy.elements().jsons() // includes laid-out positions
  const ctx = { hgncIds: props.hgncIds, clusterName: getClusterDisplayName }
  const base = exportBaseName()
  const files = {
    cyjs: () => [cyjs(json, base), `${base}.cyjs`, 'application/json'],
    graphml: () => [graphml(json, ctx), `${base}.graphml`, 'application/graphml+xml'],
    nodes: () => [nodesCsv(json, ctx), `${base}_nodes.csv`, 'text/csv'],
    edges: () => [edgesCsv(json), `${base}_edges.csv`, 'text/csv']
  }
  downloadFile(...files[format]())
}

// Watchers
watch(() => props.networkData, scheduleRender)

// Node colours follow colour mode, HPO data and cluster ranks without a restyle
watch(nodeColorMap, applyNodeStyles)

// Theme switch: re-resolve the token colours after VueUse has toggled the `dark` class
watch(
  isDark,
  () => {
    clearCanvasColors()
    if (cyInstance.value && !cyInstance.value.destroyed()) {
      cyInstance.value.style(buildStylesheet())
    }
    applyNodeStyles()
  },
  { flush: 'post' }
)

// Lifecycle
// The container is laid out once mounted; render straight away, exactly once
onMounted(() => {
  renderToken++
  if (props.networkData) renderNetwork()
})

onUnmounted(() => {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
    searchDebounceTimer = null
  }
  renderToken++
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
