/**
 * NetworkAnalysis.vue Unit Tests
 *
 * Tests key reactive behaviors: resetAll, displayNetwork, toggleTier,
 * toggleCluster, clusterList computation, and hasAnyState.
 *
 * Uses shallow mounting with stubs to avoid Cytoscape/browser dependencies.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import NetworkAnalysis from '@/views/NetworkAnalysis.vue'
import { networkAnalysisConfig } from '@/config/networkAnalysis'

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// Mock vue-router
const mockRouterReplace = vi.fn()
const mockRouterIsReady = vi.fn().mockResolvedValue(true)
vi.mock('vue-router', () => ({
  useRouter: () => ({
    replace: mockRouterReplace,
    isReady: mockRouterIsReady,
    push: vi.fn()
  }),
  useRoute: () => ({
    path: '/network-analysis',
    query: {}
  })
}))

// Mock API modules
vi.mock('@/api/genes', () => ({
  geneApi: {
    getGenes: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1 }),
    getGenesByIds: vi.fn().mockResolvedValue({ items: [] }),
    getHPOClassifications: vi.fn().mockResolvedValue({ data: [] })
  }
}))

vi.mock('@/api/network', () => ({
  networkApi: {
    buildNetwork: vi.fn().mockResolvedValue({
      nodes: 5,
      edges: 3,
      components: 1,
      cytoscape_json: { elements: [] }
    }),
    clusterNetwork: vi.fn().mockResolvedValue({
      nodes: 5,
      edges: 3,
      components: 1,
      clusters: {},
      num_clusters: 2,
      modularity: 0.5,
      cytoscape_json: { elements: [] }
    }),
    enrichGO: vi.fn().mockResolvedValue({ results: [], total_terms: 0 }),
    enrichHPO: vi.fn().mockResolvedValue({ results: [], total_terms: 0 })
  }
}))

// Mock composables
vi.mock('@/composables/useNetworkUrlState', () => ({
  default: () => ({
    syncStateToUrl: vi.fn(),
    restoreStateFromUrl: vi.fn().mockReturnValue(null),
    copyShareableUrl: vi.fn(),
    isEncoding: { value: false }
  })
}))

vi.mock('@/composables/useSeoMeta', () => ({
  useSeoMeta: vi.fn()
}))

vi.mock('@/composables/useJsonLd', () => ({
  useJsonLd: vi.fn(),
  getBreadcrumbSchema: vi.fn().mockReturnValue({})
}))

// Mock vue-sonner
vi.mock('vue-sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn(), info: vi.fn() }
}))

// Mock breadcrumbs utility
vi.mock('@/utils/publicBreadcrumbs', () => ({
  PUBLIC_BREADCRUMBS: {
    networkAnalysis: [{ title: 'Home', to: '/' }, { title: 'Network Analysis' }]
  }
}))

// Stub window.logService
vi.stubGlobal('logService', {
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn()
})

// ---------------------------------------------------------------------------
// Global component stubs: register all UI components as no-op stubs
// ---------------------------------------------------------------------------
const stubComponents = [
  'Breadcrumb',
  'BreadcrumbList',
  'BreadcrumbSeparator',
  'BreadcrumbItem',
  'BreadcrumbLink',
  'BreadcrumbPage',
  'Card',
  'CardContent',
  'Button',
  'Badge',
  'Input',
  'Select',
  'SelectTrigger',
  'SelectValue',
  'SelectContent',
  'SelectItem',
  'Separator',
  'Alert',
  'AlertTitle',
  'AlertDescription',
  'Checkbox',
  'Label',
  'Dialog',
  'DialogContent',
  'DialogHeader',
  'DialogTitle',
  'DialogFooter',
  'Popover',
  'PopoverTrigger',
  'PopoverContent',
  'Tabs',
  'TabsList',
  'TabsTrigger',
  'TabsContent',
  'NetworkGraph',
  'EnrichmentTable',
  'ComponentSkeleton',
  'ComponentError'
]

const stubs: Record<string, boolean> = {}
stubComponents.forEach(name => {
  stubs[name] = true
})

// Stub lucide icons as simple <span> elements
const iconNames = [
  'AlertTriangle',
  'ChartBarBig',
  'ChartScatter',
  'Check',
  'ChevronRight',
  'Circle',
  'Filter',
  'Network',
  'RotateCcw',
  'Share2',
  'SlidersHorizontal'
]
iconNames.forEach(name => {
  stubs[name] = true
})

// ---------------------------------------------------------------------------
// Helper: mount the component and return the VM
// ---------------------------------------------------------------------------
function mountComponent() {
  const wrapper = mount(NetworkAnalysis, {
    shallow: true,
    global: {
      stubs: {
        ...stubs,
        // teleport: false avoids issues with Dialog teleport
        teleport: true
      }
    }
  })
  return wrapper
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('NetworkAnalysis.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // -------------------------------------------------------------------------
  // 1. resetAll restores every piece of state to defaults
  // -------------------------------------------------------------------------
  describe('resetAll', () => {
    it('resets all state to default values', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      // Mutate state away from defaults
      vm.filteredGenes = [{ id: '1', gene_symbol: 'PKD1' }]
      vm.networkData = { nodes: 5, edges: 3 }
      vm.clusterData = { nodes: 5, edges: 3 }
      vm.networkStats = { nodes: 5, edges: 3, components: 1 }
      vm.clusterStats = {
        clusters: { gene1: 0 },
        num_clusters: 1,
        modularity: 0.5
      }
      vm.networkError = 'some error'
      vm.selectedClusters = [0, 1]
      vm.enrichmentResults = { results: [], total_terms: 0 }
      vm.enrichmentError = 'enrich error'
      vm.hpoClassifications = { data: [] }
      vm.activeTab = 'enrichment'
      vm.selectedTiers = ['minimal_evidence']
      vm.minScore = 99
      vm.maxGenes = 50
      vm.minStringScore = 900
      vm.clusterAlgorithm = 'walktrap'
      vm.removeIsolated = true
      vm.minDegree = 5
      vm.minClusterSize = 10
      vm.largestComponentOnly = true
      vm.nodeColorMode = 'clinical_group'
      vm.enrichmentType = 'hpo'
      vm.fdrThreshold = 0.001

      await nextTick()

      // Call resetAll
      vm.resetAll()
      await nextTick()

      // Verify data state is cleared
      expect(vm.filteredGenes).toEqual([])
      expect(vm.networkData).toBeNull()
      expect(vm.clusterData).toBeNull()
      expect(vm.networkStats).toBeNull()
      expect(vm.clusterStats).toBeNull()
      expect(vm.networkError).toBeNull()
      expect(vm.selectedClusters).toEqual([])
      expect(vm.enrichmentResults).toBeNull()
      expect(vm.enrichmentError).toBeNull()
      expect(vm.hpoClassifications).toBeNull()
      expect(vm.activeTab).toBe('network')

      // Verify controls reset to config defaults
      expect(vm.selectedTiers).toEqual([
        'comprehensive_support',
        'multi_source_support',
        'established_support'
      ])
      expect(vm.minScore).toBe(networkAnalysisConfig.geneSelection.defaultMinScore)
      expect(vm.maxGenes).toBe(networkAnalysisConfig.geneSelection.defaultMaxGenes)
      expect(vm.minStringScore).toBe(
        networkAnalysisConfig.networkConstruction.defaultMinStringScore
      )
      expect(vm.clusterAlgorithm).toBe(
        networkAnalysisConfig.networkConstruction.defaultClusteringAlgorithm
      )
      expect(vm.removeIsolated).toBe(networkAnalysisConfig.filtering.defaultRemoveIsolated)
      expect(vm.minDegree).toBe(networkAnalysisConfig.filtering.defaultMinDegree)
      expect(vm.minClusterSize).toBe(networkAnalysisConfig.filtering.defaultMinClusterSize)
      expect(vm.largestComponentOnly).toBe(
        networkAnalysisConfig.filtering.defaultLargestComponentOnly
      )
      expect(vm.nodeColorMode).toBe(networkAnalysisConfig.nodeColoring.defaultMode)
      expect(vm.enrichmentType).toBe(networkAnalysisConfig.enrichment.defaultEnrichmentType)
      expect(vm.fdrThreshold).toBe(networkAnalysisConfig.enrichment.defaultFdrThreshold)

      // Verify router.replace was called to clear URL params
      expect(mockRouterReplace).toHaveBeenCalledWith({ path: '/network-analysis' })
    })

    it('increments networkGraphKey to force re-creation', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      const initialKey = vm.networkGraphKey
      vm.resetAll()
      await nextTick()

      expect(vm.networkGraphKey).toBe(initialKey + 1)
    })
  })

  // -------------------------------------------------------------------------
  // 2. displayNetwork computed: clusterData takes priority over networkData
  // -------------------------------------------------------------------------
  describe('displayNetwork computed', () => {
    it('returns null when neither networkData nor clusterData exist', () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      expect(vm.displayNetwork).toBeNull()
    })

    it('returns networkData when only networkData is set', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      const mockNetwork = { nodes: 3, edges: 2, cytoscape_json: { elements: [] } }
      vm.networkData = mockNetwork
      await nextTick()

      expect(vm.displayNetwork).toEqual(mockNetwork)
    })

    it('returns clusterData when both networkData and clusterData exist', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      const mockNetwork = { nodes: 3, edges: 2 }
      const mockCluster = { nodes: 3, edges: 2, clusters: {} }
      vm.networkData = mockNetwork
      vm.clusterData = mockCluster
      await nextTick()

      expect(vm.displayNetwork).toEqual(mockCluster)
    })

    it('falls back to networkData when clusterData is cleared', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      const mockNetwork = { nodes: 3, edges: 2 }
      vm.networkData = mockNetwork
      vm.clusterData = { nodes: 3, edges: 2, clusters: {} }
      await nextTick()

      vm.clusterData = null
      await nextTick()

      expect(vm.displayNetwork).toEqual(mockNetwork)
    })
  })

  // -------------------------------------------------------------------------
  // 3. toggleTier and toggleCluster
  // -------------------------------------------------------------------------
  describe('toggleTier', () => {
    it('adds a tier when checked=true', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      // Start with default 3 tiers
      const initialLength = vm.selectedTiers.length

      vm.toggleTier('minimal_evidence', true)
      await nextTick()

      expect(vm.selectedTiers).toContain('minimal_evidence')
      expect(vm.selectedTiers.length).toBe(initialLength + 1)
    })

    it('does not duplicate a tier if already present', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      const tier = vm.selectedTiers[0]
      const initialLength = vm.selectedTiers.length

      vm.toggleTier(tier, true)
      await nextTick()

      expect(vm.selectedTiers.length).toBe(initialLength)
    })

    it('removes a tier when checked=false', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      const tier = vm.selectedTiers[0]
      vm.toggleTier(tier, false)
      await nextTick()

      expect(vm.selectedTiers).not.toContain(tier)
    })
  })

  describe('toggleCluster', () => {
    it('adds a cluster ID when checked=true', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      expect(vm.selectedClusters).toEqual([])

      vm.toggleCluster(2, true)
      await nextTick()

      expect(vm.selectedClusters).toContain(2)
    })

    it('does not duplicate a cluster ID if already present', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      vm.selectedClusters = [2]
      vm.toggleCluster(2, true)
      await nextTick()

      expect(vm.selectedClusters).toEqual([2])
    })

    it('removes a cluster ID when checked=false', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      vm.selectedClusters = [1, 2, 3]
      vm.toggleCluster(2, false)
      await nextTick()

      expect(vm.selectedClusters).toEqual([1, 3])
    })
  })

  // -------------------------------------------------------------------------
  // 4. clusterList computed
  // -------------------------------------------------------------------------
  describe('clusterList computed', () => {
    it('returns empty array when clusterStats is null', () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      expect(vm.clusterList).toEqual([])
    })

    it('builds sorted cluster list from clusterStats', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      // Set up cluster stats with 3 clusters of different sizes
      // Cluster 0: 2 genes, Cluster 1: 5 genes, Cluster 2: 1 gene
      vm.clusterStats = {
        clusters: {
          '100': 0,
          '101': 0,
          '200': 1,
          '201': 1,
          '202': 1,
          '203': 1,
          '204': 1,
          '300': 2
        },
        num_clusters: 3,
        modularity: 0.45
      }
      // Need networkData or clusterData for clusterColors to work
      vm.clusterData = {
        nodes: 8,
        edges: 5,
        cytoscape_json: {
          elements: [
            { data: { id: '100', cluster_id: 0, color: '#1f77b4' } },
            { data: { id: '200', cluster_id: 1, color: '#ff7f0e' } },
            { data: { id: '300', cluster_id: 2, color: '#2ca02c' } }
          ]
        }
      }
      await nextTick()

      const list = vm.clusterList

      // Should be sorted by size descending: cluster 1 (5), cluster 0 (2), cluster 2 (1)
      expect(list.length).toBe(3)
      expect(list[0].size).toBe(5)
      expect(list[1].size).toBe(2)
      expect(list[2].size).toBe(1)

      // Each entry has required properties
      list.forEach((cluster: any) => {
        expect(cluster).toHaveProperty('title')
        expect(cluster).toHaveProperty('value')
        expect(cluster).toHaveProperty('displayId')
        expect(cluster).toHaveProperty('backendId')
        expect(cluster).toHaveProperty('size')
        expect(cluster).toHaveProperty('genes')
        expect(cluster).toHaveProperty('color')
        expect(cluster.title).toMatch(/^Cluster \d+$/)
      })
    })

    it('genes array contains parsed integer gene IDs', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      vm.clusterStats = {
        clusters: { '42': 0, '99': 0 },
        num_clusters: 1,
        modularity: 0.3
      }
      vm.clusterData = {
        nodes: 2,
        edges: 1,
        cytoscape_json: { elements: [] }
      }
      await nextTick()

      const list = vm.clusterList
      expect(list.length).toBe(1)
      expect(list[0].genes).toEqual(expect.arrayContaining([42, 99]))
      // Ensure they are numbers, not strings
      list[0].genes.forEach((geneId: any) => {
        expect(typeof geneId).toBe('number')
      })
    })
  })

  // -------------------------------------------------------------------------
  // 5. hasAnyState computed
  // -------------------------------------------------------------------------
  describe('hasAnyState computed', () => {
    it('returns falsy when no genes, network, or clusters', () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      expect(vm.hasAnyState).toBeFalsy()
    })

    it('returns truthy when filteredGenes has items', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      vm.filteredGenes = [{ id: '1', gene_symbol: 'PKD1' }]
      await nextTick()

      expect(vm.hasAnyState).toBeTruthy()
    })

    it('returns truthy when networkData exists', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      vm.networkData = { nodes: 5, edges: 3 }
      await nextTick()

      expect(vm.hasAnyState).toBeTruthy()
    })

    it('returns truthy when clusterData exists', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      vm.clusterData = { nodes: 5, edges: 3, clusters: {} }
      await nextTick()

      expect(vm.hasAnyState).toBeTruthy()
    })

    it('returns falsy after resetAll clears everything', async () => {
      const wrapper = mountComponent()
      const vm = wrapper.vm as any

      vm.filteredGenes = [{ id: '1', gene_symbol: 'PKD1' }]
      vm.networkData = { nodes: 5, edges: 3 }
      await nextTick()
      expect(vm.hasAnyState).toBeTruthy()

      vm.resetAll()
      await nextTick()

      expect(vm.hasAnyState).toBeFalsy()
    })
  })
})
