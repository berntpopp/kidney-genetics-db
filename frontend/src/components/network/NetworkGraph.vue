<template>
  <Card class="network-graph-card w-full">
    <CardHeader class="flex flex-row items-center justify-between space-y-0 p-4">
      <div>
        <CardTitle class="text-lg font-medium">Protein-Protein Interaction Network</CardTitle>
        <p class="text-sm text-muted-foreground mt-1">
          {{ networkStats }}
        </p>
      </div>
      <div class="flex gap-2">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
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
      <div class="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <div class="space-y-1">
          <label class="text-xs font-medium text-muted-foreground">Layout</label>
          <Select v-model="layoutType" @update:model-value="applyLayout">
            <SelectTrigger class="h-9">
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
          <label class="text-xs font-medium text-muted-foreground">Clustering</label>
          <Select
            v-model="clusterAlgorithm"
            @update:model-value="$emit('cluster', clusterAlgorithm)"
          >
            <SelectTrigger class="h-9">
              <SelectValue placeholder="Clustering" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="opt in clusterOptions" :key="opt.value" :value="opt.value">
                {{ opt.title }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="space-y-1">
          <label class="text-xs font-medium text-muted-foreground">Node Color</label>
          <Select :model-value="colorMode" @update:model-value="$emit('update:colorMode', $event)">
            <SelectTrigger class="h-9">
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

        <div class="space-y-1">
          <label class="text-xs font-medium text-muted-foreground">Min STRING Score</label>
          <Input
            :model-value="String(minStringScore)"
            type="number"
            min="0"
            max="1000"
            step="50"
            class="h-9"
            @update:model-value="$emit('update:minStringScore', Number($event))"
          />
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
            class="pl-8 h-9"
            :class="{ 'pr-24': matchCount > 0 }"
            @input="handleSearchInput"
            @keyup.enter="handleSearch(localSearchPattern)"
          />
          <button
            v-if="localSearchPattern"
            class="absolute right-2 top-2.5 text-muted-foreground hover:text-foreground"
            @click="clearSearchHighlight"
          >
            <X class="size-4" />
          </button>
          <Badge
            v-if="matchCount > 0"
            class="absolute right-8 top-1.5 bg-green-600 text-white text-xs"
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
        v-show="!loading && !error"
        ref="cytoscapeContainer"
        class="cytoscape-container"
        :style="{ height: graphHeight }"
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

      <!-- Loading State -->
      <div v-if="loading" class="flex items-center justify-center" :style="{ height: graphHeight }">
        <div class="text-center">
          <div
            class="h-16 w-16 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto"
          />
          <p class="text-sm text-muted-foreground mt-4">Loading network...</p>
        </div>
      </div>

      <!-- Error State -->
      <div v-if="error" class="flex items-center justify-center" :style="{ height: graphHeight }">
        <Alert variant="destructive" class="max-w-md">
          <AlertCircle class="size-4" />
          <AlertTitle>Network Error</AlertTitle>
          <AlertDescription>{{ error }}</AlertDescription>
        </Alert>
      </div>

      <!-- Empty State -->
      <div
        v-if="!loading && !error && !cyInstance"
        class="flex items-center justify-center"
        :style="{ height: graphHeight }"
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
            :style="{ backgroundColor: item.color, color: 'white' }"
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
            <span v-if="colorMode !== 'cluster'" class="ml-1 opacity-60">(inactive)</span>
          </span>
          <!-- Sort options only for cluster mode -->
          <div v-if="colorMode === 'cluster'" class="inline-flex rounded-md border">
            <Button
              :variant="clusterSortMethod === 'size' ? 'default' : 'ghost'"
              size="sm"
              class="h-7 rounded-none rounded-l-md text-xs px-2"
              title="Sort by cluster size (largest first)"
              @click="clusterSortMethod = 'size'"
            >
              <ArrowUpDown class="size-3 mr-1" />
              Size
            </Button>
            <Button
              :variant="clusterSortMethod === 'spatial' ? 'default' : 'ghost'"
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
                  :variant="item.isActive ? 'default' : 'outline'"
                  class="cursor-pointer cluster-chip"
                  :class="{ 'opacity-50': !item.isActive }"
                  :style="
                    item.isActive
                      ? { backgroundColor: item.color, borderColor: item.color, color: 'white' }
                      : {}
                  "
                  @mouseenter="highlightCluster(item.id)"
                  @mouseleave="clearHighlight()"
                  @click="openClusterDialog(item.id)"
                >
                  {{ item.label }}
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

                <!-- HPO Data Coverage -->
                <div class="text-xs text-muted-foreground mb-2 flex items-center gap-1">
                  <Database class="size-3" />
                  HPO data: {{ clusterStatistics.get(item.id).hpoDataCount }} /
                  {{ clusterStatistics.get(item.id).total }}
                  ({{ clusterStatistics.get(item.id).hpoDataPercentage }}%)
                </div>

                <!-- Clinical Group Breakdown -->
                <div v-if="clusterStatistics.get(item.id).clinical.length > 0" class="mb-2">
                  <div class="text-xs font-medium mb-1">Clinical Classification</div>
                  <div class="flex flex-wrap gap-1">
                    <Badge
                      v-for="stat in clusterStatistics.get(item.id).clinical"
                      :key="stat.key"
                      class="text-xs"
                      :style="{ backgroundColor: stat.color, color: 'white' }"
                    >
                      {{ stat.label }}: {{ stat.percentage }}%
                    </Badge>
                  </div>
                </div>

                <!-- Onset Group Breakdown -->
                <div v-if="clusterStatistics.get(item.id).onset.length > 0" class="mb-2">
                  <div class="text-xs font-medium mb-1">Age of Onset</div>
                  <div class="flex flex-wrap gap-1">
                    <Badge
                      v-for="stat in clusterStatistics.get(item.id).onset"
                      :key="stat.key"
                      class="text-xs"
                      :style="{ backgroundColor: stat.color, color: 'white' }"
                    >
                      {{ stat.label }}: {{ stat.percentage }}%
                    </Badge>
                  </div>
                </div>

                <!-- Syndromic Assessment -->
                <div v-if="clusterStatistics.get(item.id).syndromic.syndromicCount > 0">
                  <div class="text-xs font-medium mb-1">Syndromic Assessment</div>
                  <div class="flex gap-1">
                    <Badge
                      class="text-xs"
                      :style="{
                        backgroundColor:
                          networkAnalysisConfig.nodeColoring.colorSchemes.syndromic.true,
                        color: 'white'
                      }"
                    >
                      Syndromic:
                      {{ clusterStatistics.get(item.id).syndromic.syndromicPercentage }}%
                    </Badge>
                    <Badge
                      class="text-xs"
                      :style="{
                        backgroundColor:
                          networkAnalysisConfig.nodeColoring.colorSchemes.syndromic.false,
                        color: 'white'
                      }"
                    >
                      Isolated:
                      {{ clusterStatistics.get(item.id).syndromic.isolatedPercentage }}%
                    </Badge>
                  </div>
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
      @highlight-gene="highlightGeneInNetwork"
    />
  </Card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  AlertCircle,
  ArrowUpDown,
  CheckSquare,
  Database,
  Download,
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
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

import ClusterDetailsDialog from './ClusterDetailsDialog.vue'
import { useNetworkSearch } from '../../composables/useNetworkSearch'
import { networkAnalysisConfig } from '../../config/networkAnalysis'

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
  minStringScore: {
    type: Number,
    default: 400
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
  }
})

// Emits
const emit = defineEmits([
  'refresh',
  'cluster',
  'update:minStringScore',
  'update:colorMode',
  'nodeClick',
  'selectCluster'
])

// Refs
const cytoscapeContainer = ref(null)
const cyInstance = ref(null)
const layoutType = ref('cose-bilkent')
const clusterAlgorithm = ref('leiden')
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
  return `${nodes} genes, ${edges} interactions, ${components} component(s)`
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

// Legend title based on color mode
const legendTitle = computed(() => {
  const mode = networkAnalysisConfig.nodeColoring.modes.find(m => m.value === props.colorMode)
  return mode?.label || 'Legend'
})

const selectedClusterColor = computed(() => {
  if (selectedClusterId.value === null) return '#1976D2'
  return clusterColors.value[selectedClusterId.value] || '#1976D2'
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
    const clinicalCounts = {}
    const onsetCounts = {}
    let syndromicCount = 0
    let isolatedCount = 0
    let hpoDataCount = 0
    const total = geneIds.length

    geneIds.forEach(geneId => {
      const classification = hpoLookup.get(geneId)
      if (classification) {
        hpoDataCount++

        // Clinical group distribution
        const clinicalGroup = classification.clinical_group || 'null'
        clinicalCounts[clinicalGroup] = (clinicalCounts[clinicalGroup] || 0) + 1

        // Onset group distribution
        const onsetGroup = classification.onset_group || 'null'
        onsetCounts[onsetGroup] = (onsetCounts[onsetGroup] || 0) + 1

        // Syndromic status
        if (classification.is_syndromic) {
          syndromicCount++
        } else {
          isolatedCount++
        }
      }
    })

    // Convert to percentage arrays, sorted by count descending
    const clinicalBreakdown = Object.entries(clinicalCounts)
      .map(([key, count]) => ({
        key,
        label: networkAnalysisConfig.nodeColoring.labels.clinical_group[key] || key,
        color: networkAnalysisConfig.nodeColoring.colorSchemes.clinical_group[key],
        count,
        percentage: ((count / hpoDataCount) * 100).toFixed(1)
      }))
      .sort((a, b) => b.count - a.count)

    const onsetBreakdown = Object.entries(onsetCounts)
      .map(([key, count]) => ({
        key,
        label: networkAnalysisConfig.nodeColoring.labels.onset_group[key] || key,
        color: networkAnalysisConfig.nodeColoring.colorSchemes.onset_group[key],
        count,
        percentage: ((count / hpoDataCount) * 100).toFixed(1)
      }))
      .sort((a, b) => b.count - a.count)

    stats.set(clusterId, {
      total,
      hpoDataCount,
      hpoDataPercentage: ((hpoDataCount / total) * 100).toFixed(1),
      clinical: clinicalBreakdown,
      onset: onsetBreakdown,
      syndromic: {
        syndromicCount,
        syndromicPercentage: ((syndromicCount / hpoDataCount) * 100).toFixed(1),
        isolatedCount,
        isolatedPercentage: ((isolatedCount / hpoDataCount) * 100).toFixed(1)
      }
    })
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
        colorMap.set(node.data.gene_id, node.data.color || '#1976D2')
      }
    })
    return colorMap
  }

  // HPO-based coloring
  if (!props.hpoClassifications?.data) {
    // No HPO data available, use default color
    nodes.forEach(node => {
      colorMap.set(node.data.gene_id, '#9E9E9E') // Grey for no data
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
      colorMap.set(geneId, colorSchemes[props.colorMode]?.null || '#9E9E9E')
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
      colorSchemes[props.colorMode]?.[value] || colorSchemes[props.colorMode]?.null || '#9E9E9E'
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

const clusterOptions = [
  { title: 'Leiden', value: 'leiden' },
  { title: 'Louvain', value: 'louvain' },
  { title: 'Walktrap', value: 'walktrap' },
  { title: 'None', value: 'none' }
]

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

  // Position tooltip's top-left corner at bottom-right of pointer cursor
  tooltipX.value = (event.renderedPosition?.x || event.position?.x || 0) + 15
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
      if (element.data?.cluster_id !== undefined && element.data?.color) {
        colors[element.data.cluster_id] = element.data.color
      }
    })
  }
  clusterColors.value = colors

  // Initialize Cytoscape
  cyInstance.value = cytoscape({
    container: cytoscapeContainer.value,
    elements: props.networkData.cytoscape_json?.elements || [],
    style: [
      {
        selector: 'node',
        style: {
          'background-color': ele => {
            const geneId = ele.data('gene_id')
            return nodeColorMap.value.get(geneId) || ele.data('color') || '#1976D2'
          },
          label: 'data(label)',
          width: 40,
          height: 40,
          'font-size': 12,
          'text-valign': 'center',
          'text-halign': 'center',
          'text-outline-width': 2,
          'text-outline-color': '#ffffff',
          'min-zoomed-font-size': 8,
          color: '#000000',
          'transition-property': 'border-width, border-color, opacity, overlay-opacity',
          'transition-duration': '0.2s'
        }
      },
      {
        selector: 'node.highlighted',
        style: {
          'border-width': 5,
          'border-color': '#FFC107',
          'border-opacity': 1,
          'overlay-color': '#FFC107',
          'overlay-opacity': 0.25,
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
          width: ele => {
            const weight = ele.data('weight') || 0.5
            return Math.max(1, weight * 5)
          },
          'line-color': '#cccccc',
          'target-arrow-color': '#cccccc',
          opacity: 0.6,
          'curve-style': 'bezier',
          'transition-property': 'line-color, width, opacity',
          'transition-duration': '0.2s'
        }
      },
      {
        selector: 'edge.highlighted',
        style: {
          'line-color': '#FFC107',
          'target-arrow-color': '#FFC107',
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
          'border-color': '#FF5722'
        }
      }
    ],
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
    highlightCluster(event.target.data('cluster_id'))
    showTooltip(event.target, event)
  })

  cyInstance.value.on('mouseout', 'node', () => {
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

const destroyCytoscape = () => {
  if (cyInstance.value) {
    cyInstance.value.destroy()
    cyInstance.value = null
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
    bg: '#ffffff',
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
      nextTick(() => {
        initializeCytoscape()
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

  if (!cyInstance.value) {
    window.logService?.warn('[NetworkGraph] No cytoscape instance, skipping color update')
    return
  }

  const nodeCount = cyInstance.value.nodes().length
  let updatedCount = 0

  // Update node colors based on new color map
  cyInstance.value.nodes().forEach(node => {
    const geneId = node.data('gene_id')
    const color = nodeColorMap.value.get(geneId) || node.data('color') || '#1976D2'
    node.style('background-color', color)
    updatedCount++
  })

  window.logService?.info(
    `[NetworkGraph] ✓ Updated colors for ${updatedCount}/${nodeCount} nodes`,
    {
      colorMode: newColorMode,
      uniqueColors: new Set([...nodeColorMap.value.values()]).size
    }
  )
})

// Lifecycle
onMounted(() => {
  if (props.networkData) {
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
  position: relative; /* Allow absolute positioning of search overlay */
}

.network-container-wrapper {
  position: relative;
  width: 100%;
}

.cytoscape-container {
  width: 100%;
  background-color: #fafafa;
  border-radius: 4px;
  position: relative;
}

.dark .cytoscape-container {
  background-color: hsl(var(--muted));
}

.cluster-chip {
  cursor: pointer;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.cluster-chip:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

/* Tooltip styling */
.node-tooltip {
  position: absolute;
  background: rgba(33, 33, 33, 0.95);
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  pointer-events: none;
  z-index: 9999;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  transform: translateX(-50%);
  white-space: nowrap;
}

.tooltip-gene {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}

.tooltip-cluster {
  font-size: 12px;
  color: #bbdefb;
  font-weight: 500;
}

.tooltip-hpo {
  margin-top: 8px;
  font-size: 11px;
}

.tooltip-hpo-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.2);
  margin: 6px 0;
}

.tooltip-hpo-section-title {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  color: #64b5f6;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.tooltip-hpo-item {
  line-height: 1.6;
  margin-bottom: 2px;
}

.tooltip-hpo-label {
  font-weight: 600;
  color: #90caf9;
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
  font-weight: 700;
  color: #ffeb3b;
  margin-right: 6px;
  min-width: 38px;
  font-size: 11px;
}

.tooltip-context-label {
  color: rgba(255, 255, 255, 0.8);
  font-size: 10px;
}

/* Dark theme adjustments */
.dark .node-tooltip {
  background: rgba(250, 250, 250, 0.95);
  color: #212121;
}

.dark .tooltip-cluster {
  color: #1976d2;
}

.dark .tooltip-hpo-divider {
  background: rgba(0, 0, 0, 0.1);
}

.dark .tooltip-hpo-section-title {
  color: #1976d2;
}

.dark .tooltip-hpo-label {
  color: #1976d2;
}

.dark .tooltip-context-percent {
  color: #f57c00;
}

.dark .tooltip-context-label {
  color: rgba(0, 0, 0, 0.7);
}

/* Search match highlighting */
.search-match {
  border-width: 4px !important;
  border-color: #ffc107 !important;
  border-style: solid !important;
  border-opacity: 1 !important;
  z-index: 998;
  box-shadow: 0 0 16px rgba(255, 193, 7, 0.6);
  transition: all 0.3s ease-out;
}

.search-edge-match {
  line-color: #ffc107 !important;
  width: 3 !important;
  opacity: 0.9 !important;
  z-index: 997;
}
</style>
