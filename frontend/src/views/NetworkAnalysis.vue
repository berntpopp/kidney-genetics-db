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
              min="10"
              max="2000"
              density="comfortable"
              variant="outlined"
              hint="Maximum genes (performance limit)"
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

    <!-- Warning for large networks -->
    <v-alert
      v-if="filteredGenes.length > 500"
      type="warning"
      variant="outlined"
      class="mb-6"
      prominent
    >
      <template #title>Large Network Warning</template>
      You have selected {{ filteredGenes.length }} genes. Networks with >500 nodes may take longer
      to build and visualize. Consider filtering to higher evidence tiers for better performance.
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
              min="0"
              max="1000"
              step="50"
              density="comfortable"
              variant="outlined"
              hint="Minimum interaction confidence (0-1000)"
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

    <!-- Network Visualization -->
    <NetworkGraph
      v-if="displayNetwork"
      :network-data="displayNetwork"
      :loading="buildingNetwork || clustering"
      :error="networkError"
      :min-string-score="minStringScore"
      height="700px"
      class="mb-6"
      @refresh="buildNetwork"
      @cluster="handleClusterRequest"
      @node-click="handleNodeClick"
      @update:min-string-score="minStringScore = $event"
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
              v-model="selectedCluster"
              :items="clusterList"
              label="Select Cluster"
              density="comfortable"
              variant="outlined"
              hint="Choose a cluster for enrichment analysis"
              persistent-hint
            >
              <template #item="{ props: itemProps, item }">
                <v-list-item v-bind="itemProps">
                  <template #prepend>
                    <v-icon :color="item.raw.color" icon="mdi-circle" />
                  </template>
                  <template #append>
                    <v-chip size="small" label>{{ item.raw.size }} genes</v-chip>
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
              :disabled="selectedCluster === null"
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
import { ref, computed } from 'vue'
import { geneApi } from '../api/genes'
import { networkApi } from '../api/network'
import NetworkGraph from '../components/network/NetworkGraph.vue'
import EnrichmentTable from '../components/network/EnrichmentTable.vue'

// Gene Selection
const selectedTiers = ref(['comprehensive_support', 'multi_source_support', 'established_support'])
const minScore = ref(50)
const maxGenes = ref(500)
const filteredGenes = ref([])
const loadingGenes = ref(false)

// Network Construction
const minStringScore = ref(400)
const clusterAlgorithm = ref('leiden')
const buildingNetwork = ref(false)
const clustering = ref(false)
const networkData = ref(null)
const clusterData = ref(null)
const networkStats = ref(null)
const clusterStats = ref(null)
const networkError = ref(null)

// Enrichment Analysis
const selectedCluster = ref(null)
const enrichmentType = ref('hpo')
const geneSet = ref('GO_Biological_Process_2023')
const fdrThreshold = ref(0.05)
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

  // Create list with colors from cytoscape data
  return Object.entries(clusterMap).map(([clusterId, geneIds]) => ({
    title: `Cluster ${parseInt(clusterId) + 1}`,
    value: parseInt(clusterId),
    size: geneIds.length,
    genes: geneIds,
    color: getClusterColor(parseInt(clusterId))
  }))
})

// Methods
const fetchFilteredGenes = async () => {
  loadingGenes.value = true
  try {
    // Fetch all pages up to maxGenes limit (API has 100 per page limit)
    const allGenes = []
    let page = 1
    const perPage = 100 // API maximum

    while (allGenes.length < maxGenes.value) {
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

    // Trim to maxGenes limit
    filteredGenes.value = allGenes.slice(0, maxGenes.value)
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
      min_string_score: minStringScore.value
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
      algorithm: clusterAlgorithm.value
    })

    // Merge cluster data with original network stats
    clusterData.value = {
      ...response,
      nodes: networkData.value.nodes,
      edges: networkData.value.edges,
      components: networkData.value.components
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
  if (selectedCluster.value === null) return

  const cluster = clusterList.value.find(c => c.value === selectedCluster.value)
  if (!cluster) return

  runningEnrichment.value = true
  enrichmentError.value = null

  try {
    let response
    if (enrichmentType.value === 'hpo') {
      response = await networkApi.enrichHPO({
        cluster_genes: cluster.genes,
        fdr_threshold: fdrThreshold.value
      })
    } else {
      response = await networkApi.enrichGO({
        cluster_genes: cluster.genes,
        gene_set: geneSet.value,
        fdr_threshold: fdrThreshold.value
      })
    }

    enrichmentResults.value = response
    window.logService.info(`Found ${response.total_terms} significant terms`)
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
