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
            @update:model-value="$emit('update:minStringScore', $event)"
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
      />

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
          v-for="(color, clusterId) in clusterColors"
          :key="clusterId"
          :color="color"
          size="small"
          label
        >
          Cluster {{ clusterId + 1 }}
        </v-chip>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import cytoscape from 'cytoscape'
import coseBilkent from 'cytoscape-cose-bilkent'

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
  }
})

// Emits
const emit = defineEmits(['refresh', 'cluster', 'update:minStringScore', 'nodeClick'])

// Refs
const cytoscapeContainer = ref(null)
const cyInstance = ref(null)
const layoutType = ref('cose-bilkent')
const clusterAlgorithm = ref('leiden')
const clusterColors = ref({})

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
          color: '#000000'
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
          'curve-style': 'bezier'
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
    wheelSensitivity: 0.2,
    minZoom: 0.1,
    maxZoom: 5
  })

  // Add event listeners
  cyInstance.value.on('tap', 'node', event => {
    const node = event.target
    emit('nodeClick', {
      gene_id: node.data('gene_id'),
      label: node.data('label'),
      cluster_id: node.data('cluster_id')
    })
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
}
</style>
