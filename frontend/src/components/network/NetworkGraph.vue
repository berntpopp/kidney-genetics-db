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
        <v-col cols="12" sm="4">
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

        <v-col cols="12" sm="4">
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

        <v-col cols="12" sm="4">
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

    <!-- Legend for Clusters -->
    <v-divider v-if="showClusterLegend" />
    <v-card-text v-if="showClusterLegend" class="pa-3">
      <div class="d-flex flex-wrap ga-2">
        <v-chip
          v-for="cluster in sortedClusterColors"
          :key="cluster.backendId"
          :color="cluster.color"
          size="small"
          label
          class="cluster-chip"
          @mouseenter="highlightCluster(cluster.backendId)"
          @mouseleave="clearHighlight"
          @click="openClusterDialog(cluster.backendId)"
        >
          {{ getClusterDisplayName(cluster.backendId) }}
        </v-chip>
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
      @highlight-gene="highlightGeneInNetwork"
    />
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import cytoscape from 'cytoscape'
import coseBilkent from 'cytoscape-cose-bilkent'
import ClusterDetailsDialog from './ClusterDetailsDialog.vue'

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
  }
})

// Emits
const emit = defineEmits([
  'refresh',
  'cluster',
  'update:minStringScore',
  'nodeClick',
  'selectCluster'
])

// Refs
const cytoscapeContainer = ref(null)
const cyInstance = ref(null)
const layoutType = ref('cose-bilkent')
const clusterAlgorithm = ref('leiden')
const clusterColors = ref({})

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
  clusterName: ''
})

// Computed
const graphHeight = computed(() => props.height)

const networkStats = computed(() => {
  if (!props.networkData) return 'No network loaded'
  const { nodes, edges, components } = props.networkData
  return `${nodes} genes, ${edges} interactions, ${components} component(s)`
})

const showClusterLegend = computed(() => {
  return Object.keys(clusterColors.value).length > 0
})

const selectedClusterColor = computed(() => {
  if (selectedClusterId.value === null) return '#1976D2'
  return clusterColors.value[selectedClusterId.value] || '#1976D2'
})

// Sort cluster colors by display ID for consistent legend order
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

  // Create array of cluster objects with display info
  const clusters = Object.entries(clusterColors.value).map(([backendId, color]) => ({
    backendId: parseInt(backendId),
    displayId: props.clusterIdMapping.get(parseInt(backendId)) ?? parseInt(backendId),
    color
  }))

  // Sort by displayId (size-based ranking: 0 = largest cluster)
  clusters.sort((a, b) => a.displayId - b.displayId)

  // Return array (NOT object) to preserve sort order
  // JavaScript auto-sorts numeric object keys, breaking our size-based order
  return clusters
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

  tooltipData.value = {
    geneSymbol: node.data('label') || node.data('gene_id'),
    clusterName
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
          'background-color': ele => ele.data('color') || '#1976D2',
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

/* Dark theme adjustments */
.v-theme--dark .node-tooltip {
  background: rgba(250, 250, 250, 0.95);
  color: #212121;
}

.v-theme--dark .tooltip-cluster {
  color: #1976d2;
}
</style>
