<template>
  <div class="container mx-auto px-4 py-4">
    <!-- Header -->
    <div class="mb-3">
      <Breadcrumb class="mb-1">
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

      <div class="flex items-center justify-between">
        <div class="flex items-center">
          <NetworkIcon class="size-7 mr-2 text-primary" />
          <div>
            <h1 class="text-xl font-bold leading-tight">Network Analysis</h1>
            <p class="text-xs text-muted-foreground">
              Protein-protein interactions &amp; functional clusters
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <Badge v-if="filteredGenes.length > 0" class="bg-green-600 text-white">
            {{ filteredGenes.length }} genes
          </Badge>
          <Badge v-if="networkStats" variant="secondary">
            {{ networkStats.nodes }} nodes &middot; {{ networkStats.edges }} edges
          </Badge>
          <Badge v-if="clusterStats" variant="secondary">
            {{ clusterStats.num_clusters }} clusters &middot; Q={{
              clusterStats.modularity.toFixed(3)
            }}
          </Badge>
        </div>
      </div>
    </div>

    <!-- Control Bar -->
    <Card class="mb-3">
      <CardContent class="p-3">
        <!-- Row 1: Parameter inputs -->
        <div class="grid grid-cols-[minmax(160px,280px)_auto_auto_auto_auto] gap-3 items-end">
          <div class="space-y-1">
            <label class="text-xs font-medium text-muted-foreground">Evidence Tiers</label>
            <Popover>
              <PopoverTrigger as-child>
                <Button variant="outline" class="w-full justify-start h-9 text-xs">
                  <span v-if="selectedTiers.length === 0" class="text-muted-foreground">
                    Select...
                  </span>
                  <span v-else>{{ selectedTiers.length }} tier(s) selected</span>
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-[260px] p-2">
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
          </div>
          <div class="space-y-1 w-20">
            <label class="text-xs font-medium text-muted-foreground">Min Score</label>
            <Input
              v-model.number="minScore"
              type="number"
              min="0"
              max="100"
              class="h-9"
              aria-label="Minimum evidence score"
            />
          </div>
          <div class="space-y-1 w-20">
            <label class="text-xs font-medium text-muted-foreground">Max Genes</label>
            <Input
              v-model.number="maxGenes"
              type="number"
              :min="networkAnalysisConfig.geneSelection.minGenesLimit"
              :max="networkAnalysisConfig.geneSelection.maxGenesHardLimit"
              class="h-9"
              aria-label="Maximum number of genes"
            />
          </div>
          <div class="space-y-1 w-24">
            <label class="text-xs font-medium text-muted-foreground">STRING</label>
            <Input
              v-model.number="minStringScore"
              type="number"
              :min="networkAnalysisConfig.networkConstruction.minStringScoreRange.min"
              :max="networkAnalysisConfig.networkConstruction.minStringScoreRange.max"
              :step="networkAnalysisConfig.networkConstruction.minStringScoreRange.step"
              class="h-9"
              aria-label="Minimum STRING interaction score"
            />
          </div>
          <div class="space-y-1 w-40">
            <label class="text-xs font-medium text-muted-foreground">Algorithm</label>
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
          </div>
        </div>

        <!-- Row 2: Step buttons + enrichment controls + utility actions -->
        <div class="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t">
          <!-- Step 1: Filter -->
          <Button :disabled="loadingGenes" size="sm" @click="fetchFilteredGenes">
            <span
              class="inline-flex items-center justify-center size-4 rounded-full bg-white/20 text-[10px] font-bold mr-1.5"
            >
              1
            </span>
            <Filter class="size-3.5 mr-1" />
            <span v-if="loadingGenes">Loading...</span>
            <span v-else>Filter Genes</span>
          </Button>

          <!-- Step 2: Build -->
          <Button
            :disabled="filteredGenes.length === 0 || buildingNetwork"
            size="sm"
            @click="buildNetwork"
          >
            <span
              class="inline-flex items-center justify-center size-4 rounded-full bg-white/20 text-[10px] font-bold mr-1.5"
            >
              2
            </span>
            <NetworkIcon class="size-3.5 mr-1" />
            <span v-if="buildingNetwork">Building...</span>
            <span v-else>Build Network</span>
          </Button>

          <!-- Step 3: Cluster -->
          <Button :disabled="!networkData || clustering" size="sm" @click="clusterNetwork">
            <span
              class="inline-flex items-center justify-center size-4 rounded-full bg-white/20 text-[10px] font-bold mr-1.5"
            >
              3
            </span>
            <ChartScatter class="size-3.5 mr-1" />
            <span v-if="clustering">Clustering...</span>
            <span v-else>Cluster</span>
          </Button>

          <!-- Step 4: Enrichment (appears after clustering) -->
          <template v-if="clusterStats">
            <Separator orientation="vertical" class="h-6 mx-1" />

            <Popover>
              <PopoverTrigger as-child>
                <Button variant="outline" size="sm" class="text-xs min-w-[120px] justify-start">
                  <span v-if="selectedClusters.length === 0" class="text-muted-foreground">
                    Clusters...
                  </span>
                  <span v-else>{{ selectedClusters.length }} cluster(s)</span>
                </Button>
              </PopoverTrigger>
              <PopoverContent class="w-[300px] p-2" align="start" side="bottom">
                <div class="max-h-[300px] overflow-y-auto space-y-0.5">
                  <div
                    v-for="cluster in clusterList"
                    :key="cluster.value"
                    class="flex items-center space-x-2 py-1.5 px-1 rounded cursor-pointer"
                    :class="
                      selectedClusters.includes(cluster.value) ? 'bg-muted' : 'hover:bg-muted/50'
                    "
                    @click="toggleCluster(cluster.value, !selectedClusters.includes(cluster.value))"
                  >
                    <div
                      class="size-4 rounded-sm border flex items-center justify-center flex-shrink-0"
                      :style="
                        selectedClusters.includes(cluster.value)
                          ? { backgroundColor: cluster.color, borderColor: cluster.color }
                          : { borderColor: cluster.color }
                      "
                    >
                      <Check
                        v-if="selectedClusters.includes(cluster.value)"
                        class="size-3 text-white"
                      />
                    </div>
                    <Circle
                      class="size-3 flex-shrink-0"
                      :style="{ color: cluster.color, fill: cluster.color }"
                    />
                    <span class="text-sm flex-1">{{ cluster.title }}</span>
                    <Badge variant="outline" class="text-xs">{{ cluster.size }}</Badge>
                  </div>
                </div>
              </PopoverContent>
            </Popover>

            <Select v-model="enrichmentType">
              <SelectTrigger class="h-8 w-32 text-xs">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="opt in enrichmentOptions" :key="opt.value" :value="opt.value">
                  {{ opt.title }}
                </SelectItem>
              </SelectContent>
            </Select>

            <Button
              size="sm"
              :disabled="selectedClusters.length === 0 || runningEnrichment"
              @click="runEnrichmentAndSwitch"
            >
              <span
                class="inline-flex items-center justify-center size-4 rounded-full bg-white/20 text-[10px] font-bold mr-1.5"
              >
                4
              </span>
              <ChartBarBig class="size-3.5 mr-1" />
              <span v-if="runningEnrichment">Running...</span>
              <span v-else>Enrich</span>
            </Button>
          </template>

          <!-- Right side: utility actions -->
          <div class="flex gap-1 ml-auto">
            <Button
              v-if="filteredGenes.length > 0"
              variant="ghost"
              size="icon"
              class="size-8"
              :disabled="isEncoding"
              title="Share URL"
              @click="handleShareNetwork"
            >
              <Share2 class="size-3.5" />
            </Button>
            <Button
              v-if="hasAnyState"
              variant="ghost"
              size="icon"
              class="size-8 text-destructive hover:text-destructive"
              title="Reset all"
              @click="resetAll"
            >
              <RotateCcw class="size-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              class="size-8"
              title="Advanced filters"
              @click="showAdvanced = !showAdvanced"
            >
              <SlidersHorizontal class="size-3.5" :class="{ 'text-primary': showAdvanced }" />
            </Button>
          </div>
        </div>

        <!-- Row 3: Advanced filters (collapsible) -->
        <div v-if="showAdvanced" class="flex flex-wrap items-end gap-4 mt-3 pt-3 border-t">
          <div class="flex items-center space-x-2">
            <Checkbox
              id="remove-isolated"
              :checked="removeIsolated"
              @update:checked="removeIsolated = $event"
            />
            <Label for="remove-isolated" class="text-xs cursor-pointer">Remove Isolated</Label>
          </div>
          <div class="flex items-center space-x-2">
            <Checkbox
              id="largest-component"
              :checked="largestComponentOnly"
              @update:checked="largestComponentOnly = $event"
            />
            <Label for="largest-component" class="text-xs cursor-pointer">
              Largest Component Only
            </Label>
          </div>
          <div class="space-y-1 w-20">
            <label class="text-xs font-medium text-muted-foreground">Min Degree</label>
            <Input
              v-model.number="minDegree"
              type="number"
              min="0"
              max="10"
              class="h-8"
              aria-label="Minimum node degree"
            />
          </div>
          <div class="space-y-1 w-24">
            <label class="text-xs font-medium text-muted-foreground">Min Cluster</label>
            <Input
              v-model.number="minClusterSize"
              type="number"
              min="1"
              max="20"
              class="h-8"
              aria-label="Minimum cluster size"
            />
          </div>
          <div class="space-y-1 w-20">
            <label class="text-xs font-medium text-muted-foreground">FDR</label>
            <Input
              v-model.number="fdrThreshold"
              type="number"
              min="0.001"
              max="0.2"
              step="0.01"
              class="h-8"
              aria-label="FDR threshold"
            />
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Large network warning -->
    <Alert
      v-if="filteredGenes.length > networkAnalysisConfig.geneSelection.largeNetworkThreshold"
      class="mb-3"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>{{ networkAnalysisConfig.ui.warningMessages.largeNetwork.title }}</AlertTitle>
      <AlertDescription>
        {{ networkAnalysisConfig.ui.warningMessages.largeNetwork.message(filteredGenes.length) }}
      </AlertDescription>
    </Alert>

    <!-- Main content: Tabs for Network / Enrichment -->
    <Tabs v-model="activeTab">
      <TabsList v-if="displayNetwork" class="mb-3">
        <TabsTrigger value="network">
          <NetworkIcon class="size-4 mr-1.5" />
          Network
        </TabsTrigger>
        <TabsTrigger value="enrichment" :disabled="!clusterStats">
          <ChartBarBig class="size-4 mr-1.5" />
          Enrichment
          <Badge
            v-if="enrichmentResults"
            variant="secondary"
            class="ml-1.5 text-[10px] px-1.5 py-0"
          >
            {{ enrichmentResults.total_terms }}
          </Badge>
        </TabsTrigger>
      </TabsList>

      <TabsContent value="network" class="mt-0">
        <!-- Network Visualization -->
        <div v-if="displayNetwork">
          <NetworkGraph
            :key="networkGraphKey"
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
            @refresh="buildNetwork"
            @cluster="handleClusterRequest"
            @node-click="handleNodeClick"
            @update:min-string-score="minStringScore = $event"
            @select-cluster="handleClusterSelection"
          />
        </div>

        <!-- Empty state -->
        <Card v-if="!displayNetwork">
          <CardContent class="flex flex-col items-center justify-center py-16 text-center">
            <NetworkIcon class="size-16 text-muted-foreground/30 mb-4" />
            <p class="text-lg font-medium text-muted-foreground">No network loaded</p>
            <p class="text-sm text-muted-foreground mt-1">
              Click
              <strong>Filter</strong>
              then
              <strong>Build</strong>
              to create a protein-protein interaction network
            </p>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="enrichment" class="mt-0">
        <Card v-if="!enrichmentResults && !runningEnrichment">
          <CardContent class="flex flex-col items-center justify-center py-16 text-center">
            <ChartBarBig class="size-16 text-muted-foreground/30 mb-4" />
            <p class="text-lg font-medium text-muted-foreground">No enrichment results</p>
            <p class="text-sm text-muted-foreground mt-1">
              Select clusters above and click
              <strong>Enrich</strong>
              to run functional enrichment analysis
            </p>
          </CardContent>
        </Card>

        <EnrichmentTable
          v-if="enrichmentResults || runningEnrichment"
          :results="enrichmentResults?.results || []"
          :loading="runningEnrichment"
          :error="enrichmentError"
          :enrichment-type="enrichmentType"
          :fdr-threshold="fdrThreshold"
          :gene-set="geneSet"
          @refresh="runEnrichment"
          @update:enrichment-type="enrichmentType = $event"
          @update:gene-set="geneSet = $event"
          @update:fdr-threshold="fdrThreshold = $event"
          @gene-click="handleGeneClick"
        />
      </TabsContent>
    </Tabs>

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
import { ref, computed, watch, nextTick, onMounted, defineAsyncComponent } from 'vue'
import ComponentSkeleton from '@/components/ui/ComponentSkeleton.vue'
import ComponentError from '@/components/ui/ComponentError.vue'
import {
  AlertTriangle,
  ChartBarBig,
  ChartScatter,
  Check,
  ChevronRight,
  Circle,
  Filter,
  Network as NetworkIcon,
  RotateCcw,
  Share2,
  SlidersHorizontal
} from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { useRouter, useRoute } from 'vue-router'

import { Card, CardContent } from '@/components/ui/card'
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'

import { geneApi } from '../api/genes'
import { networkApi } from '../api/network'
const NetworkGraph = defineAsyncComponent({
  loader: () => import('../components/network/NetworkGraph.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,
  timeout: 10000
})
import EnrichmentTable from '../components/network/EnrichmentTable.vue'
import { networkAnalysisConfig } from '../config/networkAnalysis'
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

// UI State
const showAdvanced = ref(false)
const activeTab = ref('network')
const geneDialog = ref(false)
const selectedGene = ref(null)

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

// Key for forcing NetworkGraph re-creation (fixes Cytoscape null style error)
const networkGraphKey = ref(0)

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

const hasAnyState = computed(
  () => filteredGenes.value.length > 0 || networkData.value || clusterData.value
)

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

const resetAll = () => {
  // Reset all state to defaults
  filteredGenes.value = []
  networkData.value = null
  clusterData.value = null
  networkStats.value = null
  clusterStats.value = null
  networkError.value = null
  selectedClusters.value = []
  enrichmentResults.value = null
  enrichmentError.value = null
  hpoClassifications.value = null
  activeTab.value = 'network'
  networkGraphKey.value++

  // Reset controls to defaults
  selectedTiers.value = ['comprehensive_support', 'multi_source_support', 'established_support']
  minScore.value = networkAnalysisConfig.geneSelection.defaultMinScore
  maxGenes.value = networkAnalysisConfig.geneSelection.defaultMaxGenes
  minStringScore.value = networkAnalysisConfig.networkConstruction.defaultMinStringScore
  clusterAlgorithm.value = networkAnalysisConfig.networkConstruction.defaultClusteringAlgorithm
  removeIsolated.value = networkAnalysisConfig.filtering.defaultRemoveIsolated
  minDegree.value = networkAnalysisConfig.filtering.defaultMinDegree
  minClusterSize.value = networkAnalysisConfig.filtering.defaultMinClusterSize
  largestComponentOnly.value = networkAnalysisConfig.filtering.defaultLargestComponentOnly
  nodeColorMode.value = networkAnalysisConfig.nodeColoring.defaultMode
  enrichmentType.value = networkAnalysisConfig.enrichment.defaultEnrichmentType
  fdrThreshold.value = networkAnalysisConfig.enrichment.defaultFdrThreshold

  // Clear URL params
  router.replace({ path: route.path })
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
    networkGraphKey.value++
    await nextTick()
    networkData.value = response
    clusterData.value = null
    clusterStats.value = null
    networkStats.value = {
      nodes: response.nodes,
      edges: response.edges,
      components: response.components
    }
    activeTab.value = 'network'
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
    networkGraphKey.value++
    await nextTick()
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

const runEnrichmentAndSwitch = async () => {
  await runEnrichment()
  if (enrichmentResults.value) {
    activeTab.value = 'enrichment'
  }
}

const fetchHPOClassifications = async () => {
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
  } catch (error) {
    window.logService?.error('[HPO] Failed to fetch HPO classifications:', error)
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
        window.logService?.error('[NetworkAnalysis] Failed to restore genes:', error)
        toast.error(`Failed to restore genes from URL: ${error.message}`, { duration: Infinity })
      } finally {
        loadingGenes.value = false
      }
    }
  } catch (error) {
    window.logService?.error('[NetworkAnalysis] Failed to apply restored state:', error)
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
