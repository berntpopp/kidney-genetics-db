<template>
  <v-container fluid>
    <!-- Page Header -->
    <div class="mb-6">
      <h1 class="text-h3 font-weight-bold mb-2">Network Analysis & Clustering</h1>
      <p class="text-body-1 text-medium-emphasis">
        Explore protein-protein interactions and functional clusters across kidney disease genes
      </p>
    </div>

    <!-- Gene Selection Card -->
    <v-card elevation="2" class="mb-6" rounded="lg">
      <v-card-title class="pa-4">
        <v-icon icon="mdi-filter" class="mr-2" />
        Gene Selection
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-4">
        <v-row align="center">
          <v-col cols="12" md="4">
            <v-select
              v-model="selectedTiers"
              :items="tierOptions"
              label="Evidence Tiers"
              multiple
              chips
              closable-chips
              density="comfortable"
              variant="outlined"
              hint="Select which evidence tiers to include"
              persistent-hint
            />
          </v-col>

          <v-col cols="12" md="3">
            <v-text-field
              v-model.number="minScore"
              label="Min Evidence Score"
              type="number"
              min="0"
              max="100"
              density="comfortable"
              variant="outlined"
              hint="Minimum evidence score"
              persistent-hint
            />
          </v-col>

          <v-col cols="12" md="3">
            <v-text-field
              v-model.number="maxGenes"
              label="Max Genes"
              type="number"
              :min="networkAnalysisConfig.geneSelection.minGenesLimit"
              :max="networkAnalysisConfig.geneSelection.maxGenesHardLimit"
              density="comfortable"
              variant="outlined"
              :hint="`Maximum genes (limit: ${networkAnalysisConfig.geneSelection.maxGenesHardLimit})`"
              persistent-hint
            />
          </v-col>

          <v-col cols="12" md="2" class="d-flex flex-column ga-2">
            <v-btn
              color="primary"
              prepend-icon="mdi-filter"
              :loading="loadingGenes"
              block
              @click="fetchFilteredGenes"
            >
              Filter Genes
            </v-btn>
            <v-chip v-if="filteredGenes.length > 0" color="success" label>
              {{ filteredGenes.length }} genes selected
            </v-chip>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Warning for large networks (config-driven threshold) -->
    <v-alert
      v-if="filteredGenes.length > networkAnalysisConfig.geneSelection.largeNetworkThreshold"
      type="warning"
      variant="outlined"
      class="mb-6"
      prominent
    >
      <template #title>{{ networkAnalysisConfig.ui.warningMessages.largeNetwork.title }}</template>
      {{ networkAnalysisConfig.ui.warningMessages.largeNetwork.message(filteredGenes.length) }}
    </v-alert>

    <!-- Network Construction Card -->
    <v-card elevation="2" class="mb-6" rounded="lg">
      <v-card-title class="pa-4">
        <v-icon icon="mdi-graph" class="mr-2" />
        Network Construction
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-4">
        <v-row align="center">
          <v-col cols="12" md="3">
            <v-text-field
              v-model.number="minStringScore"
              label="Min STRING Score"
              type="number"
              :min="networkAnalysisConfig.networkConstruction.minStringScoreRange.min"
              :max="networkAnalysisConfig.networkConstruction.minStringScoreRange.max"
              :step="networkAnalysisConfig.networkConstruction.minStringScoreRange.step"
              density="comfortable"
              variant="outlined"
              :hint="`Minimum interaction confidence (${networkAnalysisConfig.networkConstruction.minStringScoreRange.min}-${networkAnalysisConfig.networkConstruction.minStringScoreRange.max})`"
              persistent-hint
            />
          </v-col>

          <v-col cols="12" md="3">
            <v-select
              v-model="clusterAlgorithm"
              :items="algorithmOptions"
              label="Clustering Algorithm"
              density="comfortable"
              variant="outlined"
              hint="Algorithm for community detection"
              persistent-hint
            />
          </v-col>

          <v-col cols="12" md="3" class="d-flex flex-column ga-2">
            <v-btn
              color="primary"
              prepend-icon="mdi-graph"
              :loading="buildingNetwork"
              :disabled="filteredGenes.length === 0"
              block
              @click="buildNetwork"
            >
              Build Network
            </v-btn>
            <v-btn
              color="secondary"
              prepend-icon="mdi-chart-scatter-plot"
              :loading="clustering"
              :disabled="!networkData"
              block
              @click="clusterNetwork"
            >
              Detect Clusters
            </v-btn>
          </v-col>

          <v-col v-if="networkStats" cols="12" md="3">
            <v-card variant="outlined">
              <v-card-text class="pa-3">
                <div class="text-caption text-medium-emphasis mb-1">Network Statistics</div>
                <div class="text-h6">{{ networkStats.nodes }} genes</div>
                <div class="text-body-2">{{ networkStats.edges }} interactions</div>
                <div class="text-body-2">{{ networkStats.components }} component(s)</div>
                <div v-if="clusterStats" class="text-body-2 mt-2">
                  <v-chip size="x-small" color="info" label>
                    {{ clusterStats.num_clusters }} clusters
                  </v-chip>
                  <v-chip size="x-small" color="success" label class="ml-1">
                    Modularity: {{ clusterStats.modularity.toFixed(3) }}
                  </v-chip>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Network Filtering Controls -->
    <v-card elevation="2" class="mb-6" rounded="lg">
      <v-card-title class="pa-4">
        <v-icon icon="mdi-filter-variant" class="mr-2" />
        Network Filtering
        <v-spacer />
        <v-chip size="small" color="info" label>
          Best Practice: Remove isolated nodes and small clusters
        </v-chip>
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-4">
        <v-row align="center">
          <v-col cols="12" md="3">
            <v-checkbox
              v-model="removeIsolated"
              label="Remove Isolated Nodes"
              density="compact"
              hint="Hide genes with no interactions (degree=0)"
              persistent-hint
              color="primary"
            />
          </v-col>

          <v-col cols="12" md="3">
            <v-checkbox
              v-model="largestComponentOnly"
              label="Largest Component Only"
              density="compact"
              hint="Keep only the largest connected subnetwork"
              persistent-hint
              color="primary"
            />
          </v-col>

          <v-col cols="12" md="3">
            <v-text-field
              v-model.number="minDegree"
              label="Min Node Degree"
              type="number"
              min="0"
              max="10"
              density="comfortable"
              variant="outlined"
              hint="Minimum connections per node (0=all, 2+=multiple interactions)"
              persistent-hint
            />
          </v-col>

          <v-col cols="12" md="3">
            <v-text-field
              v-model.number="minClusterSize"
              label="Min Cluster Size"
              type="number"
              min="1"
              max="20"
              density="comfortable"
              variant="outlined"
              hint="Filter out small clusters (1=keep all, 3+=meaningful clusters)"
              persistent-hint
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="12">
            <v-alert type="info" variant="tonal" density="compact">
              <strong>Tip:</strong> For cleaner visualization of large networks, enable "Remove
              Isolated Nodes" and set Min Cluster Size to 3-5. This removes genes with no
              interactions and filters out singleton/doublet clusters.
            </v-alert>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Network Visualization -->
    <NetworkGraph
      v-if="displayNetwork"
      :network-data="displayNetwork"
      :loading="buildingNetwork || clustering"
      :error="networkError"
      :min-string-score="minStringScore"
      :cluster-id-mapping="clusterIdMapping"
      :cluster-colors-map="clusterColors"
      :height="networkAnalysisConfig.ui.defaultGraphHeight"
      class="mb-6"
      @refresh="buildNetwork"
      @cluster="handleClusterRequest"
      @node-click="handleNodeClick"
      @update:min-string-score="minStringScore = $event"
      @select-cluster="handleClusterSelection"
    />

    <!-- Cluster Selection & Enrichment -->
    <v-card v-if="clusterStats" elevation="2" class="mb-6" rounded="lg">
      <v-card-title class="pa-4">
        <v-icon icon="mdi-chart-box" class="mr-2" />
        Functional Enrichment Analysis
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-4">
        <v-row align="center">
          <v-col cols="12" md="4">
            <v-select
              v-model="selectedClusters"
              :items="clusterList"
              label="Select Clusters"
              density="comfortable"
              variant="outlined"
              hint="Choose one or more clusters for enrichment analysis"
              persistent-hint
              multiple
              chips
              closable-chips
            >
              <!-- Custom chip rendering with cluster colors -->
              <template #chip="{ item, props: chipProps }">
                <v-chip v-bind="chipProps" :color="item.raw.color" size="small" closable>
                  {{ item.title }}
                </v-chip>
              </template>

              <!-- Custom dropdown item rendering -->
              <template #item="{ props: itemProps, item }">
                <v-list-item v-bind="itemProps">
                  <template #prepend>
                    <v-icon :color="item.raw.color" icon="mdi-circle" />
                  </template>
                  <template #append>
                    <v-chip :color="item.raw.color" size="small" label variant="tonal">
                      {{ item.raw.size }} genes
                    </v-chip>
                  </template>
                </v-list-item>
              </template>
            </v-select>
          </v-col>

          <v-col cols="12" md="3">
            <v-select
              v-model="enrichmentType"
              :items="enrichmentOptions"
              label="Enrichment Type"
              density="comfortable"
              variant="outlined"
            />
          </v-col>

          <v-col cols="12" md="3">
            <v-text-field
              v-model.number="fdrThreshold"
              label="FDR Threshold"
              type="number"
              min="0.001"
              max="0.2"
              step="0.01"
              density="comfortable"
              variant="outlined"
            />
          </v-col>

          <v-col cols="12" md="2">
            <v-btn
              color="primary"
              prepend-icon="mdi-chart-box"
              :loading="runningEnrichment"
              :disabled="selectedClusters.length === 0"
              block
              @click="runEnrichment"
            >
              Run Analysis
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Enrichment Results -->
    <EnrichmentTable
      v-if="enrichmentResults"
      :results="enrichmentResults.results"
      :loading="runningEnrichment"
      :error="enrichmentError"
      :enrichment-type="enrichmentType"
      :fdr-threshold="fdrThreshold"
      :gene-set="geneSet"
      class="mb-6"
      @refresh="runEnrichment"
      @update:enrichment-type="enrichmentType = $event"
      @update:gene-set="geneSet = $event"
      @update:fdr-threshold="fdrThreshold = $event"
      @gene-click="handleGeneClick"
    />

    <!-- Gene Details Dialog -->
    <v-dialog v-model="geneDialog" max-width="600">
      <v-card v-if="selectedGene">
        <v-card-title>
          <h3 class="text-h6">{{ selectedGene.label }}</h3>
        </v-card-title>
        <v-divider />
        <v-card-text>
          <div class="mb-3"><strong>Gene ID:</strong> {{ selectedGene.gene_id }}</div>
          <div v-if="selectedGene.cluster_id !== undefined" class="mb-3">
            <strong>Cluster:</strong>
            <v-chip size="small" :color="getClusterColor(selectedGene.cluster_id)" label>
              Cluster {{ selectedGene.cluster_id + 1 }}
            </v-chip>
          </div>
          <v-btn color="primary" :to="`/genes/${selectedGene.label}`" block>
            View Gene Details
          </v-btn>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="geneDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { geneApi } from '../api/genes'
import { networkApi } from '../api/network'
import NetworkGraph from '../components/network/NetworkGraph.vue'
import EnrichmentTable from '../components/network/EnrichmentTable.vue'
import { networkAnalysisConfig } from '../config/networkAnalysis'

// Gene Selection (config-driven defaults)
const selectedTiers = ref(['comprehensive_support', 'multi_source_support', 'established_support'])
const minScore = ref(networkAnalysisConfig.geneSelection.defaultMinScore)
const maxGenes = ref(networkAnalysisConfig.geneSelection.defaultMaxGenes)
const filteredGenes = ref([])
const loadingGenes = ref(false)

// Network Construction (config-driven defaults)
const minStringScore = ref(networkAnalysisConfig.networkConstruction.defaultMinStringScore)
const clusterAlgorithm = ref(networkAnalysisConfig.networkConstruction.defaultClusteringAlgorithm)
const buildingNetwork = ref(false)
const clustering = ref(false)
const networkData = ref(null)
const clusterData = ref(null)
const networkStats = ref(null)
const clusterStats = ref(null)
const networkError = ref(null)

// Network Filtering (config-driven defaults)
const removeIsolated = ref(networkAnalysisConfig.filtering.defaultRemoveIsolated)
const minDegree = ref(networkAnalysisConfig.filtering.defaultMinDegree)
const minClusterSize = ref(networkAnalysisConfig.filtering.defaultMinClusterSize)
const largestComponentOnly = ref(networkAnalysisConfig.filtering.defaultLargestComponentOnly)

// Enrichment Analysis (config-driven defaults)
const selectedClusters = ref([]) // Changed to array for multi-select
const enrichmentType = ref(networkAnalysisConfig.enrichment.defaultEnrichmentType)
const geneSet = ref(networkAnalysisConfig.enrichment.goGeneSets[0])
const fdrThreshold = ref(networkAnalysisConfig.enrichment.defaultFdrThreshold)
const runningEnrichment = ref(false)
const enrichmentResults = ref(null)
const enrichmentError = ref(null)

// UI State
const geneDialog = ref(false)
const selectedGene = ref(null)

// Options
const tierOptions = [
  { title: 'Comprehensive Support', value: 'comprehensive_support' },
  { title: 'Multi-Source Support', value: 'multi_source_support' },
  { title: 'Established Support', value: 'established_support' },
  { title: 'Preliminary Evidence', value: 'preliminary_evidence' },
  { title: 'Minimal Evidence', value: 'minimal_evidence' }
]

const algorithmOptions = [
  { title: 'Leiden (Recommended)', value: 'leiden' },
  { title: 'Louvain', value: 'louvain' },
  { title: 'Walktrap', value: 'walktrap' }
]

const enrichmentOptions = [
  { title: 'HPO (Phenotypes)', value: 'hpo' },
  { title: 'GO (Gene Ontology)', value: 'go' }
]

// Computed
const displayNetwork = computed(() => clusterData.value || networkData.value)

// Cluster ID mapping from backend ID to display ID (sorted by size)
const clusterIdMapping = computed(() => {
  if (!clusterStats.value) return new Map()

  // Group genes by cluster
  const clusterMap = {}
  for (const [, clusterId] of Object.entries(clusterStats.value.clusters)) {
    if (!clusterMap[clusterId]) {
      clusterMap[clusterId] = { count: 0, backendId: parseInt(clusterId) }
    }
    clusterMap[clusterId].count++
  }

  // Sort by size descending and create mapping
  const sorted = Object.values(clusterMap).sort((a, b) => b.count - a.count)
  const mapping = new Map()
  sorted.forEach((cluster, displayIndex) => {
    mapping.set(cluster.backendId, displayIndex)
  })

  return mapping
})

// Extract colors from cytoscape data for each cluster
const clusterColors = computed(() => {
  if (!displayNetwork.value?.cytoscape_json?.elements) return new Map()

  const colors = new Map()
  displayNetwork.value.cytoscape_json.elements.forEach(element => {
    if (element.data?.cluster_id !== undefined && element.data?.color) {
      colors.set(element.data.cluster_id, element.data.color)
    }
  })

  return colors
})

const clusterList = computed(() => {
  if (!clusterStats.value) return []

  // Group genes by cluster
  const clusterMap = {}
  for (const [geneId, clusterId] of Object.entries(clusterStats.value.clusters)) {
    if (!clusterMap[clusterId]) {
      clusterMap[clusterId] = []
    }
    clusterMap[clusterId].push(parseInt(geneId))
  }

  // Create list with display IDs (sorted by size), using mapping
  const clusters = Object.entries(clusterMap).map(([backendId, geneIds]) => {
    const displayId = clusterIdMapping.value.get(parseInt(backendId)) ?? parseInt(backendId)
    return {
      title: `Cluster ${displayId + 1}`,
      value: parseInt(backendId), // Keep backend ID as value for selection
      displayId, // Display ID for UI
      backendId: parseInt(backendId), // Backend ID for mapping
      size: geneIds.length,
      genes: geneIds,
      color: clusterColors.value.get(parseInt(backendId)) || getClusterColor(displayId)
    }
  })

  // Sort by size descending (which matches displayId order)
  return clusters.sort((a, b) => b.size - a.size)
})

// Methods
const fetchFilteredGenes = async () => {
  loadingGenes.value = true
  try {
    // Enforce hard limit from config
    const effectiveMaxGenes = Math.min(
      maxGenes.value,
      networkAnalysisConfig.geneSelection.maxGenesHardLimit
    )

    // Fetch all pages up to maxGenes limit (API has 100 per page limit)
    const allGenes = []
    let page = 1
    const perPage = 100 // API maximum

    while (allGenes.length < effectiveMaxGenes) {
      const response = await geneApi.getGenes({
        page,
        perPage,
        tiers: selectedTiers.value,
        minScore: minScore.value,
        hideZeroScores: true
      })

      if (!response.items || response.items.length === 0) {
        break // No more results
      }

      allGenes.push(...response.items)

      // Stop if we've fetched all available genes
      if (allGenes.length >= response.total || response.items.length < perPage) {
        break
      }

      page++
    }

    // Trim to effective maxGenes limit (enforces hard limit from config)
    filteredGenes.value = allGenes.slice(0, effectiveMaxGenes)
    window.logService.info(`Filtered ${filteredGenes.value.length} genes (fetched ${page} page(s))`)
  } catch (error) {
    window.logService.error('Failed to fetch genes:', error)
    filteredGenes.value = []
  } finally {
    loadingGenes.value = false
  }
}

const buildNetwork = async () => {
  if (filteredGenes.value.length === 0) {
    window.logService.warn('No genes selected')
    return
  }

  buildingNetwork.value = true
  networkError.value = null

  try {
    const geneIds = filteredGenes.value.map(g => parseInt(g.id))
    const response = await networkApi.buildNetwork({
      gene_ids: geneIds,
      min_string_score: minStringScore.value,
      remove_isolated: removeIsolated.value,
      min_degree: minDegree.value,
      largest_component_only: largestComponentOnly.value
    })

    networkData.value = response
    clusterData.value = null // Reset cluster data
    clusterStats.value = null

    networkStats.value = {
      nodes: response.nodes,
      edges: response.edges,
      components: response.components
    }

    window.logService.info('Network built successfully')
  } catch (error) {
    window.logService.error('Failed to build network:', error)
    networkError.value = error.message || 'Failed to build network'
  } finally {
    buildingNetwork.value = false
  }
}

const clusterNetwork = async () => {
  if (!networkData.value) return

  clustering.value = true
  networkError.value = null

  try {
    const geneIds = filteredGenes.value.map(g => parseInt(g.id))
    const response = await networkApi.clusterNetwork({
      gene_ids: geneIds,
      min_string_score: minStringScore.value,
      algorithm: clusterAlgorithm.value,
      remove_isolated: removeIsolated.value,
      min_degree: minDegree.value,
      min_cluster_size: minClusterSize.value,
      largest_component_only: largestComponentOnly.value
    })

    // Merge cluster data with original network stats
    clusterData.value = {
      ...response,
      nodes: response.nodes,
      edges: response.edges,
      components: response.components
    }
    clusterStats.value = {
      clusters: response.clusters,
      num_clusters: response.num_clusters,
      modularity: response.modularity
    }

    window.logService.info(
      `Detected ${response.num_clusters} clusters (modularity: ${response.modularity.toFixed(3)})`
    )
  } catch (error) {
    window.logService.error('Failed to cluster network:', error)
    networkError.value = error.message || 'Failed to cluster network'
  } finally {
    clustering.value = false
  }
}

const runEnrichment = async () => {
  if (selectedClusters.value.length === 0) return

  // Combine genes from all selected clusters
  const selectedClusterData = clusterList.value.filter(c =>
    selectedClusters.value.includes(c.value)
  )

  // Merge all gene IDs from selected clusters (remove duplicates with Set)
  const allGenes = [...new Set(selectedClusterData.flatMap(c => c.genes))]

  if (allGenes.length === 0) return

  runningEnrichment.value = true
  enrichmentError.value = null

  try {
    let response
    if (enrichmentType.value === 'hpo') {
      response = await networkApi.enrichHPO({
        cluster_genes: allGenes,
        fdr_threshold: fdrThreshold.value
      })
    } else {
      response = await networkApi.enrichGO({
        cluster_genes: allGenes,
        gene_set: geneSet.value,
        fdr_threshold: fdrThreshold.value
      })
    }

    enrichmentResults.value = response
    const clusterText =
      selectedClusters.value.length === 1
        ? `cluster ${selectedClusters.value[0] + 1}`
        : `${selectedClusters.value.length} clusters`
    window.logService.info(
      `Found ${response.total_terms} significant terms in ${clusterText} (${allGenes.length} genes)`
    )
  } catch (error) {
    window.logService.error('Failed to run enrichment:', error)
    enrichmentError.value = error.message || 'Failed to run enrichment analysis'
  } finally {
    runningEnrichment.value = false
  }
}

const handleClusterRequest = algorithm => {
  clusterAlgorithm.value = algorithm
  clusterNetwork()
}

const handleNodeClick = nodeData => {
  selectedGene.value = nodeData
  geneDialog.value = true
}

const handleClusterSelection = clusterId => {
  // Add the cluster to selected clusters (if not already selected)
  if (!selectedClusters.value.includes(clusterId)) {
    selectedClusters.value.push(clusterId)
  }

  // Smooth scroll to enrichment section with better UX
  nextTick(() => {
    const enrichmentSection = document.querySelector('.v-card:has(.mdi-chart-box)')
    if (enrichmentSection) {
      enrichmentSection.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      })

      // Highlight the section briefly
      enrichmentSection.style.transition = 'box-shadow 0.3s'
      enrichmentSection.style.boxShadow = '0 0 20px rgba(25, 118, 210, 0.5)'
      setTimeout(() => {
        enrichmentSection.style.boxShadow = ''
      }, 1500)
    }
  })
}

const handleGeneClick = geneSymbol => {
  // Navigate to gene detail page
  window.location.href = `/genes/${geneSymbol}`
}

const getClusterColor = clusterId => {
  // Material Design colors matching backend
  const colors = [
    '#1f77b4',
    '#ff7f0e',
    '#2ca02c',
    '#d62728',
    '#9467bd',
    '#8c564b',
    '#e377c2',
    '#7f7f7f',
    '#bcbd22',
    '#17becf'
  ]
  return colors[clusterId % colors.length]
}
</script>

<style scoped>
/* Add any custom styles here */
</style>
