<template>
  <div class="container mx-auto px-4 py-6">
    <!-- Page Header -->
    <div class="mb-6">
      <!-- Breadcrumbs -->
      <Breadcrumb class="mb-2">
        <BreadcrumbList>
          <template v-for="(item, index) in breadcrumbs" :key="index">
            <BreadcrumbSeparator v-if="index > 0">
              <ChevronRight class="size-4" />
            </BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbLink v-if="item.to" :href="item.to">{{ item.title }}</BreadcrumbLink>
              <BreadcrumbPage v-else>{{ item.title }}</BreadcrumbPage>
            </BreadcrumbItem>
          </template>
        </BreadcrumbList>
      </Breadcrumb>

      <div class="flex items-center mb-6">
        <NetworkIcon class="size-8 mr-3 text-primary" />
        <div>
          <h1 class="text-2xl font-bold">Network Analysis & Clustering</h1>
          <p class="text-sm text-muted-foreground">
            Explore protein-protein interactions and functional clusters across kidney disease genes
          </p>
        </div>
      </div>
    </div>

    <!-- Gene Selection Card -->
    <Card class="mb-6">
      <CardHeader class="flex flex-row items-center space-y-0 pb-2">
        <Filter class="size-5 mr-2" />
        <CardTitle class="text-lg">Gene Selection</CardTitle>
      </CardHeader>
      <Separator />
      <CardContent class="pt-4">
        <div class="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
          <!-- Evidence Tiers Multi-Select -->
          <div class="md:col-span-4 space-y-1">
            <label class="text-xs font-medium text-muted-foreground">Evidence Tiers</label>
            <Popover>
              <PopoverTrigger as-child>
                <Button variant="outline" class="w-full justify-start h-auto min-h-9 py-1.5">
                  <div class="flex flex-wrap gap-1">
                    <Badge
                      v-for="tier in selectedTiers"
                      :key="tier"
                      :style="{ backgroundColor: getTierColor(tier), color: 'white' }"
                      class="text-xs"
                    >
                      {{ getTierLabel(tier) }}
                      <button class="ml-1" @click.stop="toggleTier(tier, false)">
                        <X class="size-3" />
                      </button>
                    </Badge>
                    <span v-if="selectedTiers.length === 0" class="text-muted-foreground text-sm">
                      Select tiers...
                    </span>
                  </div>
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-[280px] p-2">
                <div
                  v-for="opt in tierOptions"
                  :key="opt.value"
                  class="flex items-center space-x-2 py-1.5 px-1"
                >
                  <Checkbox
                    :id="`tier-${opt.value}`"
                    :checked="selectedTiers.includes(opt.value)"
                    @update:checked="toggleTier(opt.value, $event)"
                  />
                  <Label :for="`tier-${opt.value}`" class="text-sm cursor-pointer">
                    {{ opt.title }}
                  </Label>
                </div>
              </PopoverContent>
            </Popover>
            <p class="text-xs text-muted-foreground">Select which evidence tiers to include</p>
          </div>

          <!-- Min Evidence Score -->
          <div class="md:col-span-3 space-y-1">
            <label class="text-xs font-medium text-muted-foreground">Min Evidence Score</label>
            <Input v-model.number="minScore" type="number" min="0" max="100" class="h-9" />
            <p class="text-xs text-muted-foreground">Minimum evidence score</p>
          </div>

          <!-- Max Genes -->
          <div class="md:col-span-3 space-y-1">
            <label class="text-xs font-medium text-muted-foreground">Max Genes</label>
            <Input
              v-model.number="maxGenes"
              type="number"
              :min="networkAnalysisConfig.geneSelection.minGenesLimit"
              :max="networkAnalysisConfig.geneSelection.maxGenesHardLimit"
              class="h-9"
            />
            <p class="text-xs text-muted-foreground">
              Maximum genes (limit: {{ networkAnalysisConfig.geneSelection.maxGenesHardLimit }})
            </p>
          </div>

          <!-- Actions -->
          <div class="md:col-span-2 flex flex-col gap-2">
            <Button :disabled="loadingGenes" class="w-full" @click="fetchFilteredGenes">
              <Filter class="size-4 mr-1" />
              <span v-if="loadingGenes">Loading...</span>
              <span v-else>Filter Genes</span>
            </Button>
            <Button
              v-if="filteredGenes.length > 0"
              variant="outline"
              :disabled="isEncoding"
              class="w-full"
              @click="handleShareNetwork"
            >
              <Share2 class="size-4 mr-1" />
              Share
            </Button>
            <Badge v-if="filteredGenes.length > 0" class="bg-green-600 text-white justify-center">
              {{ filteredGenes.length }} genes selected
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Warning for large networks -->
    <Alert
      v-if="filteredGenes.length > networkAnalysisConfig.geneSelection.largeNetworkThreshold"
      class="mb-6"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>{{ networkAnalysisConfig.ui.warningMessages.largeNetwork.title }}</AlertTitle>
      <AlertDescription>
        {{ networkAnalysisConfig.ui.warningMessages.largeNetwork.message(filteredGenes.length) }}
      </AlertDescription>
    </Alert>

    <!-- Network Construction Card -->
    <Card class="mb-6">
      <CardHeader class="flex flex-row items-center space-y-0 pb-2">
        <NetworkIcon class="size-5 mr-2" />
        <CardTitle class="text-lg">Network Construction</CardTitle>
      </CardHeader>
      <Separator />
      <CardContent class="pt-4">
        <div class="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
          <!-- Min STRING Score -->
          <div class="md:col-span-3 space-y-1">
            <label class="text-xs font-medium text-muted-foreground">Min STRING Score</label>
            <Input
              v-model.number="minStringScore"
              type="number"
              :min="networkAnalysisConfig.networkConstruction.minStringScoreRange.min"
              :max="networkAnalysisConfig.networkConstruction.minStringScoreRange.max"
              :step="networkAnalysisConfig.networkConstruction.minStringScoreRange.step"
              class="h-9"
            />
            <p class="text-xs text-muted-foreground">
              Minimum interaction confidence ({{
                networkAnalysisConfig.networkConstruction.minStringScoreRange.min
              }}-{{ networkAnalysisConfig.networkConstruction.minStringScoreRange.max }})
            </p>
          </div>

          <!-- Clustering Algorithm -->
          <div class="md:col-span-3 space-y-1">
            <label class="text-xs font-medium text-muted-foreground">Clustering Algorithm</label>
            <Select v-model="clusterAlgorithm">
              <SelectTrigger class="h-9">
                <SelectValue placeholder="Algorithm" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="opt in algorithmOptions" :key="opt.value" :value="opt.value">
                  {{ opt.title }}
                </SelectItem>
              </SelectContent>
            </Select>
            <p class="text-xs text-muted-foreground">Algorithm for community detection</p>
          </div>

          <!-- Actions -->
          <div class="md:col-span-3 flex flex-col gap-2">
            <Button
              :disabled="filteredGenes.length === 0 || buildingNetwork"
              class="w-full"
              @click="buildNetwork"
            >
              <NetworkIcon class="size-4 mr-1" />
              <span v-if="buildingNetwork">Building...</span>
              <span v-else>Build Network</span>
            </Button>
            <Button
              variant="outline"
              :disabled="!networkData || clustering"
              class="w-full"
              @click="clusterNetwork"
            >
              <ChartScatter class="size-4 mr-1" />
              <span v-if="clustering">Clustering...</span>
              <span v-else>Detect Clusters</span>
            </Button>
          </div>

          <!-- Network Statistics -->
          <div v-if="networkStats" class="md:col-span-3">
            <Card variant="outline">
              <CardContent class="p-3">
                <div class="text-xs text-muted-foreground mb-1">Network Statistics</div>
                <div class="text-lg font-semibold">{{ networkStats.nodes }} genes</div>
                <div class="text-sm">{{ networkStats.edges }} interactions</div>
                <div class="text-sm">{{ networkStats.components }} component(s)</div>
                <div v-if="clusterStats" class="mt-2 flex gap-1">
                  <Badge variant="secondary" class="text-xs">
                    {{ clusterStats.num_clusters }} clusters
                  </Badge>
                  <Badge class="bg-green-600 text-white text-xs">
                    Modularity: {{ clusterStats.modularity.toFixed(3) }}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Network Filtering Controls -->
    <Card class="mb-6">
      <CardHeader class="flex flex-row items-center space-y-0 pb-2">
        <SlidersHorizontal class="size-5 mr-2" />
        <CardTitle class="text-lg">Network Filtering</CardTitle>
        <div class="flex-1" />
        <Badge variant="secondary">Filter network nodes and edges</Badge>
      </CardHeader>
      <Separator />
      <CardContent class="pt-4">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 items-start">
          <!-- Remove Isolated Nodes -->
          <div class="flex items-start space-x-2 pt-2">
            <Checkbox
              id="remove-isolated"
              :checked="removeIsolated"
              @update:checked="removeIsolated = $event"
            />
            <div>
              <Label for="remove-isolated" class="text-sm cursor-pointer">
                Remove Isolated Nodes
              </Label>
              <p class="text-xs text-muted-foreground">
                Hide genes with no interactions (degree=0)
              </p>
            </div>
          </div>

          <!-- Largest Component Only -->
          <div class="flex items-start space-x-2 pt-2">
            <Checkbox
              id="largest-component"
              :checked="largestComponentOnly"
              @update:checked="largestComponentOnly = $event"
            />
            <div>
              <Label for="largest-component" class="text-sm cursor-pointer">
                Largest Component Only
              </Label>
              <p class="text-xs text-muted-foreground">
                Keep only the largest connected subnetwork
              </p>
            </div>
          </div>

          <!-- Min Node Degree -->
          <div class="space-y-1">
            <label class="text-xs font-medium text-muted-foreground">Min Node Degree</label>
            <Input v-model.number="minDegree" type="number" min="0" max="10" class="h-9" />
            <p class="text-xs text-muted-foreground">
              Minimum connections per node (0=all, 2+=multiple)
            </p>
          </div>

          <!-- Min Cluster Size -->
          <div class="space-y-1">
            <label class="text-xs font-medium text-muted-foreground">Min Cluster Size</label>
            <Input v-model.number="minClusterSize" type="number" min="1" max="20" class="h-9" />
            <p class="text-xs text-muted-foreground">
              Filter out small clusters (1=keep all, 3+=meaningful)
            </p>
          </div>
        </div>

        <Alert class="mt-4">
          <AlertDescription>
            <strong>Tip:</strong> For cleaner visualization of large networks, enable "Remove
            Isolated Nodes" and set Min Cluster Size to 3-5. This removes genes with no interactions
            and filters out singleton/doublet clusters.
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>

    <!-- Network Visualization -->
    <NetworkGraph
      v-if="displayNetwork"
      v-model:color-mode="nodeColorMode"
      :network-data="displayNetwork"
      :loading="buildingNetwork || clustering"
      :error="networkError"
      :min-string-score="minStringScore"
      :cluster-id-mapping="clusterIdMapping"
      :cluster-colors-map="clusterColors"
      :hpo-classifications="hpoClassifications"
      :loading-h-p-o-data="loadingHPOClassifications"
      :height="networkAnalysisConfig.ui.defaultGraphHeight"
      class="mb-6"
      @refresh="buildNetwork"
      @cluster="handleClusterRequest"
      @node-click="handleNodeClick"
      @update:min-string-score="minStringScore = $event"
      @select-cluster="handleClusterSelection"
    />

    <!-- Cluster Selection & Enrichment -->
    <Card v-if="clusterStats" ref="enrichmentCard" class="mb-6">
      <CardHeader class="flex flex-row items-center space-y-0 pb-2">
        <ChartBarBig class="size-5 mr-2" />
        <CardTitle class="text-lg">Functional Enrichment Analysis</CardTitle>
      </CardHeader>
      <Separator />
      <CardContent class="pt-4">
        <div class="grid grid-cols-1 md:grid-cols-12 gap-4 items-start">
          <!-- Cluster Multi-Select -->
          <div class="md:col-span-4 space-y-1">
            <label class="text-xs font-medium text-muted-foreground">Select Clusters</label>
            <Popover>
              <PopoverTrigger as-child>
                <Button variant="outline" class="w-full justify-start h-auto min-h-9 py-1.5">
                  <div class="flex flex-wrap gap-1">
                    <Badge
                      v-for="cId in selectedClusters"
                      :key="cId"
                      :style="{
                        backgroundColor: clusterColors.get(cId) || getClusterColor(cId),
                        color: 'white'
                      }"
                      class="text-xs"
                    >
                      Cluster {{ (clusterIdMapping.get(cId) ?? cId) + 1 }}
                      <button class="ml-1" @click.stop="toggleCluster(cId, false)">
                        <X class="size-3" />
                      </button>
                    </Badge>
                    <span
                      v-if="selectedClusters.length === 0"
                      class="text-muted-foreground text-sm"
                    >
                      Select clusters...
                    </span>
                  </div>
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-[280px] p-2">
                <div
                  v-for="cluster in clusterList"
                  :key="cluster.value"
                  class="flex items-center space-x-2 py-1.5 px-1"
                >
                  <Checkbox
                    :id="`cluster-${cluster.value}`"
                    :checked="selectedClusters.includes(cluster.value)"
                    @update:checked="toggleCluster(cluster.value, $event)"
                  />
                  <Circle class="size-4 flex-shrink-0" :style="{ color: cluster.color }" />
                  <Label :for="`cluster-${cluster.value}`" class="text-sm cursor-pointer flex-1">
                    {{ cluster.title }}
                  </Label>
                  <Badge variant="outline" class="text-xs">{{ cluster.size }}</Badge>
                </div>
              </PopoverContent>
            </Popover>
            <p class="text-xs text-muted-foreground">
              Choose one or more clusters for enrichment analysis
            </p>
          </div>

          <!-- Enrichment Type -->
          <div class="md:col-span-3 space-y-1">
            <label class="text-xs font-medium text-muted-foreground">Enrichment Type</label>
            <Select v-model="enrichmentType">
              <SelectTrigger class="h-9">
                <SelectValue placeholder="Enrichment Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="opt in enrichmentOptions" :key="opt.value" :value="opt.value">
                  {{ opt.title }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <!-- FDR Threshold -->
          <div class="md:col-span-3 space-y-1">
            <label class="text-xs font-medium text-muted-foreground">FDR Threshold</label>
            <Input
              v-model.number="fdrThreshold"
              type="number"
              min="0.001"
              max="0.2"
              step="0.01"
              class="h-9"
            />
          </div>

          <!-- Run Analysis -->
          <div class="md:col-span-2">
            <Button
              :disabled="selectedClusters.length === 0 || runningEnrichment"
              class="w-full mt-5"
              @click="runEnrichment"
            >
              <ChartBarBig class="size-4 mr-1" />
              <span v-if="runningEnrichment">Running...</span>
              <span v-else>Run Analysis</span>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>

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
    <Dialog v-model:open="geneDialog">
      <DialogContent v-if="selectedGene" class="max-w-lg">
        <DialogHeader>
          <DialogTitle>{{ selectedGene.label }}</DialogTitle>
        </DialogHeader>
        <Separator />
        <div class="space-y-3 py-2">
          <div><strong>Gene ID:</strong> {{ selectedGene.gene_id }}</div>
          <div v-if="selectedGene.cluster_id !== undefined">
            <strong>Cluster:</strong>
            <Badge
              class="ml-1"
              :style="{
                backgroundColor: getClusterColor(selectedGene.cluster_id),
                color: 'white'
              }"
            >
              Cluster {{ selectedGene.cluster_id + 1 }}
            </Badge>
          </div>
          <Button class="w-full" as-child>
            <router-link :to="`/genes/${selectedGene.label}`">View Gene Details</router-link>
          </Button>
        </div>
        <Separator />
        <DialogFooter>
          <Button variant="ghost" @click="geneDialog = false">Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import {
  AlertTriangle,
  ChartBarBig,
  ChartScatter,
  ChevronRight,
  Circle,
  Filter,
  Network as NetworkIcon,
  Share2,
  SlidersHorizontal,
  X
} from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useRouter, useRoute } from 'vue-router'

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
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter
} from '@/components/ui/dialog'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'

import { geneApi } from '../api/genes'
import { networkApi } from '../api/network'
import NetworkGraph from '../components/network/NetworkGraph.vue'
import EnrichmentTable from '../components/network/EnrichmentTable.vue'
import { networkAnalysisConfig } from '../config/networkAnalysis'
import { TIER_CONFIG } from '../utils/evidenceTiers'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'
import useNetworkUrlState from '../composables/useNetworkUrlState'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getBreadcrumbSchema } from '@/composables/useJsonLd'

// Breadcrumbs
const breadcrumbs = PUBLIC_BREADCRUMBS.networkAnalysis

useJsonLd(getBreadcrumbSchema(breadcrumbs))

useSeoMeta({
  title: 'Network Analysis',
  description:
    'Explore protein-protein interaction networks and functional clusters across kidney disease genes using STRING-DB data.',
  canonicalPath: '/network-analysis'
})

// Enrichment card ref for scroll targeting
const enrichmentCard = ref(null)

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
const selectedClusters = ref([])
const enrichmentType = ref(networkAnalysisConfig.enrichment.defaultEnrichmentType)
const geneSet = ref(networkAnalysisConfig.enrichment.goGeneSets[0])
const fdrThreshold = ref(networkAnalysisConfig.enrichment.defaultFdrThreshold)
const runningEnrichment = ref(false)
const enrichmentResults = ref(null)
const enrichmentError = ref(null)

// UI State
const geneDialog = ref(false)
const selectedGene = ref(null)

// URL State Management
const router = useRouter()
const route = useRoute()
const isRestoringFromUrl = ref(false)
const { syncStateToUrl, restoreStateFromUrl, copyShareableUrl, isEncoding } = useNetworkUrlState({
  debounceMs: 800
})

// Node Coloring State (config-driven defaults)
const nodeColorMode = ref(networkAnalysisConfig.nodeColoring.defaultMode)
const hpoClassifications = ref(null)
const loadingHPOClassifications = ref(false)

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
  { title: 'GO (Gene Ontology)', value: 'go' },
  { title: 'HPO (Phenotypes)', value: 'hpo' }
]

// Computed
const displayNetwork = computed(() => clusterData.value || networkData.value)

const clusterIdMapping = computed(() => {
  if (!clusterStats.value) return new Map()
  const clusterMap = {}
  for (const [, clusterId] of Object.entries(clusterStats.value.clusters)) {
    if (!clusterMap[clusterId]) {
      clusterMap[clusterId] = { count: 0, backendId: parseInt(clusterId) }
    }
    clusterMap[clusterId].count++
  }
  const sorted = Object.values(clusterMap).sort((a, b) => b.count - a.count)
  const mapping = new Map()
  sorted.forEach((cluster, displayIndex) => {
    mapping.set(cluster.backendId, displayIndex)
  })
  return mapping
})

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
  const clusterMap = {}
  for (const [geneId, clusterId] of Object.entries(clusterStats.value.clusters)) {
    if (!clusterMap[clusterId]) {
      clusterMap[clusterId] = []
    }
    clusterMap[clusterId].push(parseInt(geneId))
  }
  const clusters = Object.entries(clusterMap).map(([backendId, geneIds]) => {
    const displayId = clusterIdMapping.value.get(parseInt(backendId)) ?? parseInt(backendId)
    return {
      title: `Cluster ${displayId + 1}`,
      value: parseInt(backendId),
      displayId,
      backendId: parseInt(backendId),
      size: geneIds.length,
      genes: geneIds,
      color: clusterColors.value.get(parseInt(backendId)) || getClusterColor(displayId)
    }
  })
  return clusters.sort((a, b) => b.size - a.size)
})

// Utility Functions
const getTierColor = tierKey => {
  return TIER_CONFIG[tierKey]?.color || 'grey'
}

const getTierLabel = tierKey => {
  const opt = tierOptions.find(o => o.value === tierKey)
  return opt?.title || tierKey
}

const toggleTier = (tier, checked) => {
  if (checked) {
    if (!selectedTiers.value.includes(tier)) {
      selectedTiers.value = [...selectedTiers.value, tier]
    }
  } else {
    selectedTiers.value = selectedTiers.value.filter(t => t !== tier)
  }
}

const toggleCluster = (clusterId, checked) => {
  if (checked) {
    if (!selectedClusters.value.includes(clusterId)) {
      selectedClusters.value = [...selectedClusters.value, clusterId]
    }
  } else {
    selectedClusters.value = selectedClusters.value.filter(c => c !== clusterId)
  }
}

// Methods
const fetchFilteredGenes = async () => {
  loadingGenes.value = true
  try {
    const effectiveMaxGenes = Math.min(
      maxGenes.value,
      networkAnalysisConfig.geneSelection.maxGenesHardLimit
    )
    const allGenes = []
    let page = 1
    const perPage = 100

    while (allGenes.length < effectiveMaxGenes) {
      const response = await geneApi.getGenes({
        page,
        perPage,
        tiers: selectedTiers.value,
        minScore: minScore.value,
        hideZeroScores: true
      })
      if (!response.items || response.items.length === 0) break
      allGenes.push(...response.items)
      if (allGenes.length >= response.total || response.items.length < perPage) break
      page++
    }

    filteredGenes.value = allGenes.slice(0, effectiveMaxGenes)
    window.logService?.info(
      `Filtered ${filteredGenes.value.length} genes (fetched ${page} page(s))`
    )
  } catch (error) {
    window.logService?.error('Failed to fetch genes:', error)
    filteredGenes.value = []
  } finally {
    loadingGenes.value = false
  }
}

const buildNetwork = async () => {
  if (filteredGenes.value.length === 0) {
    window.logService?.warn('No genes selected')
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
    clusterData.value = null
    clusterStats.value = null
    networkStats.value = {
      nodes: response.nodes,
      edges: response.edges,
      components: response.components
    }
    window.logService?.info('Network built successfully')
  } catch (error) {
    window.logService?.error('Failed to build network:', error)
    networkError.value = error.message || 'Failed to build network'
  } finally {
    buildingNetwork.value = false
    fetchHPOClassifications()
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
    window.logService?.info(
      `Detected ${response.num_clusters} clusters (modularity: ${response.modularity.toFixed(3)})`
    )
  } catch (error) {
    window.logService?.error('Failed to cluster network:', error)
    networkError.value = error.message || 'Failed to cluster network'
  } finally {
    clustering.value = false
    fetchHPOClassifications()
  }
}

const runEnrichment = async () => {
  if (selectedClusters.value.length === 0) return
  const selectedClusterData = clusterList.value.filter(c =>
    selectedClusters.value.includes(c.value)
  )
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
    window.logService?.info(
      `Found ${response.total_terms} significant terms in ${clusterText} (${allGenes.length} genes)`
    )
  } catch (error) {
    window.logService?.error('Failed to run enrichment:', error)
    enrichmentError.value = error.message || 'Failed to run enrichment analysis'
  } finally {
    runningEnrichment.value = false
  }
}

const fetchHPOClassifications = async () => {
  window.logService?.info('[HPO] fetchHPOClassifications called', {
    hasNetworkData: !!networkData.value,
    colorMode: nodeColorMode.value
  })
  if (!networkData.value) return
  if (!networkData.value.cytoscape_json?.elements) return

  const geneIds = networkData.value.cytoscape_json.elements
    .filter(el => el.data?.id && !el.data?.source)
    .map(el => el.data?.gene_id)
    .filter(id => id)

  if (geneIds.length === 0) return
  loadingHPOClassifications.value = true
  try {
    const response = await geneApi.getHPOClassifications(geneIds)
    hpoClassifications.value = response
    window.logService?.info(
      `[HPO] ✓ Fetched HPO classifications for ${response.data.length}/${geneIds.length} genes`
    )
  } catch (error) {
    window.logService?.error('[HPO] ✗ Failed to fetch HPO classifications:', error)
    hpoClassifications.value = null
  } finally {
    loadingHPOClassifications.value = false
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
  if (!selectedClusters.value.includes(clusterId)) {
    selectedClusters.value.push(clusterId)
  }
  nextTick(() => {
    if (enrichmentCard.value?.$el) {
      enrichmentCard.value.$el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  })
}

const handleGeneClick = geneSymbol => {
  window.location.href = `/genes/${geneSymbol}`
}

const getClusterColor = clusterId => {
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

// URL State Management
const getStateSnapshot = () => ({
  geneIds: filteredGenes.value.map(g => parseInt(g.id)),
  selectedTiers: selectedTiers.value,
  minScore: minScore.value,
  maxGenes: maxGenes.value,
  minStringScore: minStringScore.value,
  clusterAlgorithm: clusterAlgorithm.value,
  removeIsolated: removeIsolated.value,
  minDegree: minDegree.value,
  minClusterSize: minClusterSize.value,
  largestComponentOnly: largestComponentOnly.value,
  nodeColorMode: nodeColorMode.value,
  enrichmentType: enrichmentType.value,
  fdrThreshold: fdrThreshold.value,
  selectedClusters: selectedClusters.value,
  highlightedCluster: null,
  isClustered: !!clusterStats.value
})

const applyRestoredState = async urlState => {
  isRestoringFromUrl.value = true
  try {
    if (urlState.selectedTiers) selectedTiers.value = urlState.selectedTiers
    if (urlState.minScore !== undefined) minScore.value = urlState.minScore
    if (urlState.maxGenes !== undefined) maxGenes.value = urlState.maxGenes
    if (urlState.minStringScore !== undefined) minStringScore.value = urlState.minStringScore
    if (urlState.clusterAlgorithm) clusterAlgorithm.value = urlState.clusterAlgorithm
    if (urlState.removeIsolated !== undefined) removeIsolated.value = urlState.removeIsolated
    if (urlState.minDegree !== undefined) minDegree.value = urlState.minDegree
    if (urlState.minClusterSize !== undefined) minClusterSize.value = urlState.minClusterSize
    if (urlState.largestComponentOnly !== undefined)
      largestComponentOnly.value = urlState.largestComponentOnly
    if (urlState.nodeColorMode) nodeColorMode.value = urlState.nodeColorMode
    if (urlState.enrichmentType) enrichmentType.value = urlState.enrichmentType
    if (urlState.fdrThreshold !== undefined) fdrThreshold.value = urlState.fdrThreshold
    if (urlState.selectedClusters) selectedClusters.value = urlState.selectedClusters

    if (urlState.geneIds && urlState.geneIds.length > 0) {
      loadingGenes.value = true
      try {
        const response = await geneApi.getGenesByIds(urlState.geneIds)
        filteredGenes.value = response.items
        await nextTick()
        await buildNetwork()
        if (urlState.isClustered) {
          await nextTick()
          await clusterNetwork()
        }
      } catch (error) {
        window.logService?.error('[NetworkAnalysis] ✗ Failed to restore genes:', error)
        toast.error(`Failed to restore genes from URL: ${error.message}`, { duration: Infinity })
      } finally {
        loadingGenes.value = false
      }
    }
  } catch (error) {
    window.logService?.error('[NetworkAnalysis] ✗ Failed to apply restored state:', error)
    toast.error('Failed to restore network state from URL', { duration: Infinity })
  } finally {
    isRestoringFromUrl.value = false
  }
}

const handleShareNetwork = async () => {
  const state = getStateSnapshot()
  await copyShareableUrl(state)
}

// Lifecycle
onMounted(async () => {
  await router.isReady()
  const hasUrlState = !!(route.query.v && (route.query.c || route.query.genes))
  if (hasUrlState) {
    const urlState = restoreStateFromUrl()
    if (urlState) await applyRestoredState(urlState)
  }
})

// Watchers
watch(nodeColorMode, async () => {
  if (networkData.value && !hpoClassifications.value) {
    await fetchHPOClassifications()
  }
})

watch(
  () => ({
    geneIds: filteredGenes.value.map(g => parseInt(g.id)),
    selectedTiers: selectedTiers.value,
    minScore: minScore.value,
    maxGenes: maxGenes.value,
    minStringScore: minStringScore.value,
    clusterAlgorithm: clusterAlgorithm.value,
    removeIsolated: removeIsolated.value,
    minDegree: minDegree.value,
    minClusterSize: minClusterSize.value,
    largestComponentOnly: largestComponentOnly.value,
    nodeColorMode: nodeColorMode.value,
    enrichmentType: enrichmentType.value,
    fdrThreshold: fdrThreshold.value,
    selectedClusters: selectedClusters.value,
    isClustered: !!clusterStats.value
  }),
  state => {
    if (isRestoringFromUrl.value) return
    if (state.geneIds && state.geneIds.length > 0) {
      syncStateToUrl(state)
    }
  },
  { deep: true }
)
</script>

<style scoped>
/* Custom styles if needed */
</style>
