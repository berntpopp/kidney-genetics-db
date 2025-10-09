<template>
  <v-card elevation="2" class="network-graph-card" rounded="lg">
    <v-card-title class="d-flex align-center justify-space-between pa-4">
      <div>
        <h3 class="text-h6 font-weight-medium">Protein-Protein Interaction Network</h3>
        <p class="text-caption text-medium-emphasis mt-1">
          {{ networkStats }}
        </p>
      </div>
      <div class="d-flex ga-2">
        <v-tooltip location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              icon="mdi-download"
              variant="text"
              size="small"
              v-bind="tooltipProps"
              :disabled="!cyInstance"
              @click="exportGraph"
            />
          </template>
          <span>Export graph as PNG</span>
        </v-tooltip>

        <v-tooltip location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              icon="mdi-fit-to-screen"
              variant="text"
              size="small"
              v-bind="tooltipProps"
              :disabled="!cyInstance"
              @click="fitGraph"
            />
          </template>
          <span>Fit to screen</span>
        </v-tooltip>

        <v-tooltip location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              icon="mdi-refresh"
              variant="text"
              size="small"
              v-bind="tooltipProps"
              :loading="loading"
              @click="$emit('refresh')"
            />
          </template>
          <span>Refresh network</span>
        </v-tooltip>
      </div>
    </v-card-title>

    <v-divider />

    <!-- Network Controls -->
    <v-card-text class="pa-3">
      <v-row dense align="center">
        <v-col cols="12" sm="3">
          <v-select
            v-model="layoutType"
            :items="layoutOptions"
            label="Layout"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="applyLayout"
          />
        </v-col>

        <v-col cols="12" sm="3">
          <v-select
            v-model="clusterAlgorithm"
            :items="clusterOptions"
            label="Clustering"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="$emit('cluster', clusterAlgorithm)"
          />
        </v-col>

        <v-col cols="12" sm="3">
          <v-select
            :model-value="colorMode"
            :items="networkAnalysisConfig.nodeColoring.modes"
            item-title="label"
            item-value="value"
            label="Node Color"
            prepend-inner-icon="mdi-palette"
            density="compact"
            variant="outlined"
            hide-details
            :loading="loadingHPOData"
            @update:model-value="$emit('update:colorMode', $event)"
          />
        </v-col>

        <v-col cols="12" sm="3">
          <v-text-field
            :model-value="minStringScore"
            label="Min STRING Score"
            type="number"
            min="0"
            max="1000"
            step="50"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="$emit('update:minStringScore', Number($event))"
          />
        </v-col>
      </v-row>
    </v-card-text>

    <v-divider />

    <!-- Cytoscape Graph Container -->
    <v-card-text class="pa-0">
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
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div
        v-if="loading"
        class="d-flex align-center justify-center"
        :style="{ height: graphHeight }"
      >
        <div class="text-center">
          <v-progress-circular indeterminate color="primary" size="64" />
          <p class="text-body-2 text-medium-emphasis mt-4">Loading network...</p>
        </div>
      </div>

      <!-- Error State -->
      <div v-if="error" class="d-flex align-center justify-center" :style="{ height: graphHeight }">
        <v-alert type="error" variant="outlined" max-width="500">
          <template #title>Network Error</template>
          {{ error }}
        </v-alert>
      </div>

      <!-- Empty State -->
      <div
        v-if="!loading && !error && !cyInstance"
        class="d-flex align-center justify-center"
        :style="{ height: graphHeight }"
      >
        <div class="text-center text-medium-emphasis">
          <v-icon icon="mdi-graph-outline" size="64" class="mb-4" />
          <p class="text-body-1">No network data available</p>
          <p class="text-caption">Build a network to visualize interactions</p>
        </div>
      </div>
    </v-card-text>

    <!-- Dynamic Legend (Clusters or HPO Classifications) -->
    <v-divider v-if="showLegend" />
    <v-card-text v-if="showLegend" class="pa-3">
      <!-- HPO Classification Legend (when in HPO mode) -->
      <div v-if="hpoLegendItems.length > 0" class="mb-3">
        <div class="d-flex align-center mb-2">
          <span class="text-caption text-medium-emphasis font-weight-medium">{{
            legendTitle
          }}</span>
        </div>
        <div class="d-flex flex-wrap ga-2">
          <v-chip
            v-for="item in hpoLegendItems"
            :key="item.id"
            :color="item.color"
            size="small"
            label
          >
            {{ item.label }}
          </v-chip>
        </div>
      </div>

      <!-- Cluster Legend (always visible when clusters exist) -->
      <div v-if="clusterLegendItems.length > 0">
        <div class="d-flex align-center justify-space-between mb-2">
          <span class="text-caption text-medium-emphasis font-weight-medium">
            {{ colorMode === 'cluster' ? legendTitle : 'Clusters' }}
            <v-chip v-if="colorMode !== 'cluster'" size="x-small" variant="text" class="ml-1" label>
              (inactive)
            </v-chip>
          </span>
          <!-- Sort options only for cluster mode -->
          <v-btn-toggle
            v-if="colorMode === 'cluster'"
            v-model="clusterSortMethod"
            mandatory
            density="compact"
            variant="outlined"
            divided
            size="x-small"
          >
            <v-btn value="size" title="Sort by cluster size (largest first)">
              <v-icon size="small">mdi-sort-numeric-descending</v-icon>
              <span class="ml-1">Size</span>
            </v-btn>
            <v-btn value="spatial" title="Sort by spatial proximity in graph">
              <v-icon size="small">mdi-map-marker-distance</v-icon>
              <span class="ml-1">Spatial</span>
            </v-btn>
          </v-btn-toggle>
        </div>
        <div class="d-flex flex-wrap ga-2">
          <v-menu
            v-for="item in clusterLegendItems"
            :key="item.id"
            open-on-hover
            :open-delay="300"
            :close-delay="100"
            location="top"
            :disabled="!clusterStatistics.has(item.id) || !hpoClassifications?.data"
          >
            <template #activator="{ props: menuProps }">
              <v-chip
                v-bind="menuProps"
                :color="item.isActive ? item.color : undefined"
                :variant="item.isActive ? 'flat' : 'outlined'"
                size="small"
                label
                class="cluster-chip cursor-pointer"
                :class="{ 'inactive-chip': !item.isActive }"
                @mouseenter="highlightCluster(item.id)"
                @mouseleave="clearHighlight()"
                @click="openClusterDialog(item.id)"
              >
                {{ item.label }}
              </v-chip>
            </template>

            <!-- HPO Statistics Tooltip -->
            <v-card
              v-if="clusterStatistics.has(item.id)"
              class="pa-3"
              elevation="8"
              max-width="320"
            >
              <v-card-title class="text-subtitle-2 pa-0 mb-2">
                {{ item.label }}
                <v-chip size="x-small" class="ml-2" label>
                  {{ clusterStatistics.get(item.id).total }} genes
                </v-chip>
              </v-card-title>

              <v-divider class="mb-2" />

              <!-- HPO Data Coverage -->
              <div class="text-caption text-medium-emphasis mb-3">
                <v-icon size="x-small" icon="mdi-database" class="mr-1" />
                HPO data:
                {{ clusterStatistics.get(item.id).hpoDataCount }} /
                {{ clusterStatistics.get(item.id).total }}
                ({{ clusterStatistics.get(item.id).hpoDataPercentage }}%)
              </div>

              <!-- Clinical Group Breakdown -->
              <div v-if="clusterStatistics.get(item.id).clinical.length > 0" class="mb-2">
                <div class="text-caption font-weight-medium mb-1">Clinical Classification</div>
                <div class="d-flex flex-wrap ga-1">
                  <v-chip
                    v-for="stat in clusterStatistics.get(item.id).clinical"
                    :key="stat.key"
                    :color="stat.color"
                    size="x-small"
                    label
                  >
                    {{ stat.label }}: {{ stat.percentage }}%
                  </v-chip>
                </div>
              </div>

              <!-- Onset Group Breakdown -->
              <div v-if="clusterStatistics.get(item.id).onset.length > 0" class="mb-2">
                <div class="text-caption font-weight-medium mb-1">Age of Onset</div>
                <div class="d-flex flex-wrap ga-1">
                  <v-chip
                    v-for="stat in clusterStatistics.get(item.id).onset"
                    :key="stat.key"
                    :color="stat.color"
                    size="x-small"
                    label
                  >
                    {{ stat.label }}: {{ stat.percentage }}%
                  </v-chip>
                </div>
              </div>

              <!-- Syndromic Assessment -->
              <div v-if="clusterStatistics.get(item.id).syndromic.syndromicCount > 0">
                <div class="text-caption font-weight-medium mb-1">Syndromic Assessment</div>
                <div class="d-flex ga-1">
                  <v-chip
                    :color="networkAnalysisConfig.nodeColoring.colorSchemes.syndromic.true"
                    size="x-small"
                    label
                  >
                    Syndromic: {{ clusterStatistics.get(item.id).syndromic.syndromicPercentage }}%
                  </v-chip>
                  <v-chip
                    :color="networkAnalysisConfig.nodeColoring.colorSchemes.syndromic.false"
                    size="x-small"
                    label
                  >
                    Isolated: {{ clusterStatistics.get(item.id).syndromic.isolatedPercentage }}%
                  </v-chip>
                </div>
              </div>
            </v-card>
          </v-menu>
        </div>
      </div>
    </v-card-text>

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
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import cytoscape from 'cytoscape'
import coseBilkent from 'cytoscape-cose-bilkent'
import ClusterDetailsDialog from './ClusterDetailsDialog.vue'
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
  hpoData: null
})

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

  window.logService.debug('[ClusterStats] Computing HPO statistics per cluster')

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

  window.logService.info(`[ClusterStats] ✓ Computed statistics for ${stats.size} clusters`, {
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
  if (props.hpoClassifications?.data && geneId) {
    hpoData = props.hpoClassifications.data.find(item => item.gene_id === geneId)
  }

  tooltipData.value = {
    geneSymbol: node.data('label') || node.data('gene_id'),
    clusterName,
    hpoData
  }

  // Position tooltip near cursor with offset
  tooltipX.value = event.renderedPosition?.x || event.position?.x || 0
  tooltipY.value = (event.renderedPosition?.y || event.position?.y || 0) - 40

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
  window.logService.info('[NetworkGraph] Color mode or HPO data changed', {
    colorMode: newColorMode,
    oldColorMode,
    hasHPOData: !!props.hpoClassifications?.data,
    hpoDataCount: props.hpoClassifications?.data?.length || 0,
    hasCyInstance: !!cyInstance.value
  })

  if (!cyInstance.value) {
    window.logService.warn('[NetworkGraph] No cytoscape instance, skipping color update')
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

  window.logService.info(`[NetworkGraph] ✓ Updated colors for ${updatedCount}/${nodeCount} nodes`, {
    colorMode: newColorMode,
    uniqueColors: new Set([...nodeColorMap.value.values()]).size
  })
})

// Lifecycle
onMounted(() => {
  if (props.networkData) {
    initializeCytoscape()
  }
})

onUnmounted(() => {
  destroyCytoscape()
})
</script>

<style scoped>
.network-graph-card {
  width: 100%;
}

.cytoscape-container {
  width: 100%;
  background-color: #fafafa;
  border-radius: 4px;
  position: relative;
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

.inactive-chip {
  opacity: 0.5;
  border-color: rgba(0, 0, 0, 0.3) !important;
}

.inactive-chip:hover {
  opacity: 0.7;
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
  margin-bottom: 6px;
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

/* Dark theme adjustments */
.v-theme--dark .node-tooltip {
  background: rgba(250, 250, 250, 0.95);
  color: #212121;
}

.v-theme--dark .tooltip-cluster {
  color: #1976d2;
}

.v-theme--dark .tooltip-hpo-divider {
  background: rgba(0, 0, 0, 0.1);
}

.v-theme--dark .tooltip-hpo-label {
  color: #1976d2;
}
</style>
