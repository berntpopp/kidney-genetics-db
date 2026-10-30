/* global AbortController -- browser global; the shared ESLint globals list predates it */
/**
 * Network analysis pipeline state: Filter -> Build -> Cluster -> Enrich.
 *
 * Each pipeline keeps one in-flight request. Starting a pipeline aborts its previous request and
 * every downstream one (a new network invalidates its clusters and their enrichment), and a
 * response whose controller was aborted is ignored, so results can never land out of order.
 * Every successful step resets the state that depended on the previous result.
 */

import { ref, computed, watch, onUnmounted, getCurrentInstance } from 'vue'
import { toast } from 'vue-sonner'
import { geneApi } from '@/api/genes'
import { networkApi } from '@/api/network'
import type {
  EnrichmentResponse,
  EnrichmentTerm,
  NetworkBuildResponse,
  NetworkClusterResponse
} from '@/api/network'
import type { HPOClassificationsResult } from '@/api/genes'
import type { Gene } from '@/types/gene'
import { networkAnalysisConfig } from '@/config/networkAnalysis'
import { clusterStyle } from '@/components/network/clusterPalette'

const cfg = networkAnalysisConfig

export const DEFAULT_TIERS = [
  'comprehensive_support',
  'multi_source_support',
  'established_support'
]

/** Network-construction parameters a network was built with */
export interface BuildParams {
  min_string_score: number
  remove_isolated: boolean
  min_degree: number
  largest_component_only: boolean
}

export interface ClusterStats {
  clusters: Record<string, number>
  num_clusters: number
  modularity: number
  algorithm?: string
  resolution?: number | null
  /** Resolution used to compute the reported modularity Q */
  modularityResolution?: number | null
}

export interface ClusterListItem {
  title: string
  value: number
  displayId: number
  backendId: number
  size: number
  genes: number[]
  color: string
  /** Most specific enriched HPO term, once the background labelling has finished */
  labelTerm?: EnrichmentTerm
}

/** What an enrichment result was computed from, so the UI can label it truthfully */
export interface EnrichmentRun {
  type: string
  geneSet: string
  fdr: number
  geneCount: number
  clusterLabel: string
  /** 'reference' = genome (GO) or all kidney HPO genes (HPO); 'network' = the network on screen */
  background: EnrichmentBackground
  backgroundSize: number
}

export type EnrichmentBackground = 'reference' | 'network'

type Pipeline = 'genes' | 'build' | 'cluster' | 'enrich' | 'hpo' | 'labels'
/** Downstream pipelines a new run of the key invalidates */
const DOWNSTREAM: Record<Pipeline, Pipeline[]> = {
  genes: [],
  build: ['cluster', 'enrich', 'hpo', 'labels'],
  cluster: ['enrich', 'labels'],
  enrich: [],
  hpo: [],
  labels: []
}

/** Tooltip for a cluster label: what it is and how strongly it is supported */
export const clusterLabelNote = (t: EnrichmentTerm): string =>
  `Most specific enriched HPO term (FDR ${t.fdr.toExponential(1)}, ${t.gene_count} genes)`

/** Labelling thresholds: a label must be significant and carried by several cluster genes */
export const LABEL_MAX_FDR = 0.05
export const LABEL_MIN_GENES = 3

/**
 * The most specific informative term of one cluster, or null.
 *
 * Ranks qualifying terms by the share of the term's background genes that fall in the cluster
 * (gene_count / background_count, proportional to fold enrichment within one cluster), ties by
 * lowest p. Not by p (true-path propagation makes broad ancestors win on p) and not by odds ratio
 * (the backend caps it at 1000 when every annotated cluster gene carries the term, which again
 * is exactly the broad ancestors). Terms without a resolved name are skipped: ids are never bare.
 */
export function pickClusterLabel(terms: EnrichmentTerm[]): EnrichmentTerm | null {
  const share = (t: EnrichmentTerm) => (t.background_count ? t.gene_count / t.background_count : 0)
  let best: EnrichmentTerm | null = null
  for (const t of terms) {
    if (t.fdr >= LABEL_MAX_FDR || t.gene_count < LABEL_MIN_GENES) continue
    if (!t.term_name || t.term_name === t.term_id) continue
    if (!best || share(t) > share(best) || (share(t) === share(best) && t.p_value < best.p_value))
      best = t
  }
  return best
}

const errorMessage = (error: unknown, fallback: string): string =>
  (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail?.toString() ||
  (error as Error)?.message ||
  fallback

/**
 * Coerce a numeric input to [min, max]; empty or invalid input falls back. Warns when the value
 * had to change, so a cleared field never silently becomes 0.
 */
export function clampInput(
  value: unknown,
  {
    min,
    max,
    fallback,
    label,
    integer = true
  }: {
    min: number
    max: number
    fallback: number
    label: string
    integer?: boolean
  }
): number {
  const n = value === '' || value === null || value === undefined ? NaN : Number(value)
  const out = Number.isFinite(n)
    ? Math.min(max, Math.max(min, integer ? Math.round(n) : n))
    : fallback
  if (out !== n) toast.warning(`${label} must be between ${min} and ${max}; using ${out}.`)
  return out
}

export function useNetworkAnalysis() {
  // Gene selection
  const selectedTiers = ref<string[]>([...DEFAULT_TIERS])
  const minScore = ref<number>(cfg.geneSelection.defaultMinScore)
  const maxGenes = ref<number>(cfg.geneSelection.defaultMaxGenes)
  const filteredGenes = ref<Gene[]>([])
  const loadingGenes = ref(false)

  // Network construction and filtering
  const minStringScore = ref<number>(cfg.networkConstruction.defaultMinStringScore)
  const clusterAlgorithm = ref<string>(cfg.networkConstruction.defaultClusteringAlgorithm)
  const removeIsolated = ref<boolean>(cfg.filtering.defaultRemoveIsolated)
  const minDegree = ref<number>(cfg.filtering.defaultMinDegree)
  const minClusterSize = ref<number>(cfg.filtering.defaultMinClusterSize)
  const largestComponentOnly = ref<boolean>(cfg.filtering.defaultLargestComponentOnly)

  const buildingNetwork = ref(false)
  const clustering = ref(false)
  const networkData = ref<NetworkBuildResponse | null>(null)
  const clusterData = ref<NetworkClusterResponse | null>(null)
  const clusterStats = ref<ClusterStats | null>(null)
  const networkError = ref<string | null>(null)
  /** Genes and parameters the current network was built from (the share URL encodes these) */
  const networkGenes = ref<Gene[]>([])
  const builtParams = ref<BuildParams | null>(null)
  const clusteredWith = ref<{ algorithm: string; minClusterSize: number } | null>(null)

  // Enrichment
  const selectedClusters = ref<number[]>([])
  const enrichmentType = ref<string>(cfg.enrichment.defaultEnrichmentType)
  // Reference background by default: a network background asks a narrower question (what sets
  // a cluster apart from the rest of the network) and is often underpowered on small networks
  const enrichmentBackground = ref<EnrichmentBackground>('reference')
  const geneSet = ref<string>(cfg.enrichment.goGeneSets[0]!)
  const fdrThreshold = ref<number>(cfg.enrichment.defaultFdrThreshold)
  const runningEnrichment = ref(false)
  const enrichmentResults = ref<EnrichmentResponse | null>(null)
  const enrichmentError = ref<string | null>(null)
  const enrichmentRun = ref<EnrichmentRun | null>(null)

  const hpoClassifications = ref<HPOClassificationsResult | null>(null)
  const loadingHPOClassifications = ref(false)

  /** Backend cluster id -> its label term (see pickClusterLabel) */
  const clusterLabelTerms = ref(new Map<number, EnrichmentTerm>())
  const loadingClusterLabels = ref(false)

  // --- request bookkeeping -------------------------------------------------
  const inflight: Partial<Record<Pipeline, AbortController>> = {}
  const flags: Partial<Record<Pipeline, { value: boolean }>> = {
    genes: loadingGenes,
    build: buildingNetwork,
    cluster: clustering,
    enrich: runningEnrichment,
    hpo: loadingHPOClassifications,
    labels: loadingClusterLabels
  }

  function abort(p: Pipeline) {
    inflight[p]?.abort()
    delete inflight[p]
    flags[p]!.value = false
  }

  function start(p: Pipeline): AbortController {
    for (const q of [p, ...DOWNSTREAM[p]]) abort(q)
    const controller = new AbortController()
    inflight[p] = controller
    flags[p]!.value = true
    return controller
  }

  function finish(p: Pipeline, controller: AbortController) {
    if (inflight[p] !== controller) return // superseded: the newer request owns the flag
    delete inflight[p]
    flags[p]!.value = false
  }

  const abortAll = () => (Object.keys(flags) as Pipeline[]).forEach(abort)
  if (getCurrentInstance()) onUnmounted(abortAll)

  // --- derived -------------------------------------------------------------
  const displayNetwork = computed(() => clusterData.value || networkData.value)

  /** Gene IDs of the network on screen: the enrichment background */
  const networkGeneIds = computed<number[]>(() =>
    clusterStats.value
      ? Object.keys(clusterStats.value.clusters).map(Number)
      : networkGenes.value.map(g => Number(g.id))
  )

  const clusterList = computed<ClusterListItem[]>(() => {
    if (!clusterStats.value) return []
    const byCluster = new Map<number, number[]>()
    for (const [geneId, clusterId] of Object.entries(clusterStats.value.clusters)) {
      const id = Number(clusterId)
      if (!byCluster.has(id)) byCluster.set(id, [])
      byCluster.get(id)!.push(Number(geneId))
    }
    // Rank by size (stable for ties), so display ids and colours follow size
    return [...byCluster.entries()]
      .sort((a, b) => b[1].length - a[1].length)
      .map(([backendId, genes], displayId) => {
        const labelTerm = clusterLabelTerms.value.get(backendId)
        return {
          title: labelTerm
            ? `Cluster ${displayId + 1} · ${labelTerm.term_name}`
            : `Cluster ${displayId + 1}`,
          value: backendId,
          displayId,
          backendId,
          size: genes.length,
          genes,
          color: clusterStyle(displayId, genes.length, clusteredWith.value?.minClusterSize ?? 1)
            .color,
          labelTerm
        }
      })
  })

  /** Backend cluster id -> display index (0 = largest) */
  const clusterIdMapping = computed(
    () => new Map(clusterList.value.map(c => [c.backendId, c.displayId]))
  )

  /** Backend cluster id -> label term name; the graph shows it next to the cluster */
  const clusterLabels = computed(
    () => new Map([...clusterLabelTerms.value].map(([id, t]) => [id, t.term_name]))
  )

  /** Backend cluster id -> colour by size rank; colours the graph, legend and list alike */
  const clusterColors = computed(() => new Map(clusterList.value.map(c => [c.backendId, c.color])))

  /** gene_id -> HGNC ID, so genes are named by their identifier, never by internal ids */
  const hgncIds = computed(
    () =>
      new Map(
        [...networkGenes.value, ...filteredGenes.value]
          .filter(g => g.hgnc_id)
          .map(g => [Number(g.id), g.hgnc_id])
      )
  )

  /** Submitted genes the network filters removed, with the reasons that were active */
  const hiddenGenes = computed(() => {
    const p = builtParams.value
    if (!p || !displayNetwork.value) return null
    const submitted = networkGenes.value.length
    const hidden = submitted - displayNetwork.value.nodes
    if (hidden <= 0) return null
    const reasons: string[] = []
    if (p.min_degree > 1)
      reasons.push(`fewer than ${p.min_degree} interactions at STRING ≥ ${p.min_string_score}`)
    else if (p.min_degree === 1 || p.remove_isolated)
      reasons.push(`no interaction at STRING ≥ ${p.min_string_score}`)
    if (p.largest_component_only) reasons.push('outside the largest connected component')
    if (clusterData.value && clusteredWith.value && clusteredWith.value.minClusterSize > 1)
      reasons.push(`in a cluster of fewer than ${clusteredWith.value.minClusterSize} genes`)
    const unknown = displayNetwork.value.unknown_gene_ids?.length ?? 0
    if (unknown > 0) reasons.push(`not found in STRING (${unknown})`)
    return { hidden, submitted, reasons }
  })

  const buildKey = () =>
    JSON.stringify([
      filteredGenes.value.map(g => Number(g.id)),
      minStringScore.value,
      removeIsolated.value,
      minDegree.value,
      largestComponentOnly.value
    ])
  const builtKey = ref<string | null>(null)

  /** The step the user should take next (1-4), or 0 when the pipeline is current */
  const nextStep = computed<number>(() => {
    if (filteredGenes.value.length === 0) return 1
    if (!networkData.value || builtKey.value !== buildKey()) return 2
    const cw = clusteredWith.value
    if (
      !clusterData.value ||
      !cw ||
      cw.algorithm !== clusterAlgorithm.value ||
      cw.minClusterSize !== minClusterSize.value
    )
      return 3
    if (!enrichmentResults.value) return 4
    return 0
  })

  // --- actions -------------------------------------------------------------
  const readBuildParams = (): BuildParams => {
    minStringScore.value = clampInput(minStringScore.value, {
      ...cfg.networkConstruction.minStringScoreRange,
      fallback: cfg.networkConstruction.defaultMinStringScore,
      label: 'STRING score'
    })
    minDegree.value = clampInput(minDegree.value, {
      min: 0,
      max: cfg.filtering.maxMinDegree,
      fallback: cfg.filtering.defaultMinDegree,
      label: 'Min Degree'
    })
    return {
      min_string_score: minStringScore.value,
      remove_isolated: removeIsolated.value,
      min_degree: minDegree.value,
      largest_component_only: largestComponentOnly.value
    }
  }

  const clearEnrichment = () => {
    abort('enrich')
    enrichmentResults.value = null
    enrichmentError.value = null
    enrichmentRun.value = null
  }

  const fetchFilteredGenes = async () => {
    minScore.value = clampInput(minScore.value, {
      min: 0,
      max: 100,
      fallback: cfg.geneSelection.defaultMinScore,
      label: 'Min Score'
    })
    maxGenes.value = clampInput(maxGenes.value, {
      min: cfg.geneSelection.minGenesLimit,
      max: cfg.geneSelection.maxGenesHardLimit,
      fallback: cfg.geneSelection.defaultMaxGenes,
      label: 'Max Genes'
    })
    if (selectedTiers.value.length === 0) {
      toast.error('Select at least one evidence tier.')
      return
    }
    const controller = start('genes')
    try {
      const allGenes: Gene[] = []
      let page = 1
      const perPage = 100
      while (allGenes.length < maxGenes.value) {
        const response = await geneApi.getGenes({
          page,
          perPage,
          tiers: selectedTiers.value,
          minScore: minScore.value,
          hideZeroScores: true
        })
        if (controller.signal.aborted) return
        if (!response.items || response.items.length === 0) break
        allGenes.push(...response.items)
        if (allGenes.length >= response.total || response.items.length < perPage) break
        page++
      }
      filteredGenes.value = allGenes.slice(0, maxGenes.value)
      if (filteredGenes.value.length === 0) {
        toast.info('No genes match these filters. Lower Min Score or add evidence tiers.')
      }
      window.logService?.info(`Filtered ${filteredGenes.value.length} genes (${page} page(s))`)
    } catch (error) {
      if (controller.signal.aborted) return
      window.logService?.error('Failed to fetch genes:', error)
      toast.error(`Could not load genes: ${errorMessage(error, 'request failed')}`)
    } finally {
      finish('genes', controller)
    }
  }

  const fetchHPOClassifications = async () => {
    const geneIds = (networkData.value?.cytoscape_json?.elements ?? [])
      .filter(el => el.data?.id && !el.data?.source)
      .map(el => el.data?.gene_id as number)
      .filter(Boolean)
    if (geneIds.length === 0) return
    const controller = start('hpo')
    try {
      const response = await geneApi.getHPOClassifications(geneIds)
      if (!controller.signal.aborted) hpoClassifications.value = response
    } catch (error) {
      if (controller.signal.aborted) return
      window.logService?.error('[HPO] Failed to fetch HPO classifications:', error)
      hpoClassifications.value = null
    } finally {
      finish('hpo', controller)
    }
  }

  // ponytail: the batch endpoint takes at most 200 communities; the smallest beyond that stay unlabelled
  const MAX_LABELLED_CLUSTERS = 200

  /** Background HPO labelling of every cluster of >= 3 genes; any failure keeps "Cluster N" */
  const fetchClusterLabels = async () => {
    const clusters = clusterList.value
      .filter(c => c.size >= LABEL_MIN_GENES)
      .slice(0, MAX_LABELLED_CLUSTERS)
    if (clusters.length === 0) return
    const controller = start('labels')
    try {
      const response = await networkApi.enrichHPOBatch(
        { communities: clusters.map(c => c.genes), fdr_threshold: LABEL_MAX_FDR },
        controller.signal
      )
      if (controller.signal.aborted) return
      const labels = new Map<number, EnrichmentTerm>()
      clusters.forEach((c, i) => {
        const term = pickClusterLabel(response.results[i] ?? [])
        if (term) labels.set(c.backendId, term)
      })
      clusterLabelTerms.value = labels
    } catch (error) {
      if (controller.signal.aborted) return
      window.logService?.warn(
        '[Network] Cluster labelling failed; keeping numbered clusters',
        error
      )
    } finally {
      finish('labels', controller)
    }
  }

  const buildNetwork = async () => {
    const genes = filteredGenes.value
    if (genes.length === 0) return
    const params = readBuildParams()
    const key = buildKey()
    const controller = start('build')
    networkError.value = null
    try {
      const response = await networkApi.buildNetwork(
        { gene_ids: genes.map(g => Number(g.id)), ...params },
        controller.signal
      )
      if (controller.signal.aborted) return
      networkData.value = response
      networkGenes.value = genes
      builtParams.value = params
      builtKey.value = key
      clusterData.value = null
      clusterStats.value = null
      clusteredWith.value = null
      selectedClusters.value = []
      clusterLabelTerms.value = new Map()
      clearEnrichment()
      hpoClassifications.value = null
      window.logService?.info('Network built successfully')
      void fetchHPOClassifications()
    } catch (error) {
      if (controller.signal.aborted) return
      window.logService?.error('Failed to build network:', error)
      networkError.value = errorMessage(error, 'Failed to build network')
    } finally {
      finish('build', controller)
    }
  }

  const clusterNetwork = async () => {
    // Cluster exactly the network on screen: its genes and construction parameters
    if (!networkData.value || !builtParams.value) return
    minClusterSize.value = clampInput(minClusterSize.value, {
      min: 1,
      max: cfg.filtering.maxMinClusterSize,
      fallback: cfg.filtering.defaultMinClusterSize,
      label: 'Min Cluster'
    })
    const settings = { algorithm: clusterAlgorithm.value, minClusterSize: minClusterSize.value }
    const controller = start('cluster')
    networkError.value = null
    try {
      const response = await networkApi.clusterNetwork(
        {
          gene_ids: networkGenes.value.map(g => Number(g.id)),
          ...builtParams.value,
          algorithm: settings.algorithm,
          min_cluster_size: settings.minClusterSize
        },
        controller.signal
      )
      if (controller.signal.aborted) return
      clusterData.value = response
      clusterStats.value = {
        clusters: response.clusters,
        num_clusters: response.num_clusters,
        modularity: response.modularity,
        algorithm: response.algorithm,
        resolution:
          response.resolution ?? (response.parameters?.resolution as number | undefined) ?? null,
        modularityResolution:
          (response.parameters?.modularity_resolution as number | undefined) ?? null
      }
      clusteredWith.value = settings
      clusterLabelTerms.value = new Map()
      clearEnrichment()
      // Default to the largest cluster; pooling every cluster tests the whole network
      selectedClusters.value = clusterList.value[0] ? [clusterList.value[0].value] : []
      void fetchClusterLabels()
      window.logService?.info(
        `Detected ${response.num_clusters} clusters (modularity: ${response.modularity.toFixed(3)})`
      )
    } catch (error) {
      if (controller.signal.aborted) return
      window.logService?.error('Failed to cluster network:', error)
      networkError.value = errorMessage(error, 'Failed to cluster network')
    } finally {
      finish('cluster', controller)
    }
  }

  const runEnrichment = async () => {
    const selected = clusterList.value.filter(c => selectedClusters.value.includes(c.value))
    const genes = [...new Set(selected.flatMap(c => c.genes))]
    if (genes.length === 0) return
    const fdr = clampInput(fdrThreshold.value, {
      min: 0.001,
      max: 0.2,
      fallback: cfg.enrichment.defaultFdrThreshold,
      label: 'FDR',
      integer: false
    })
    fdrThreshold.value = fdr
    const background = enrichmentBackground.value === 'network' ? networkGeneIds.value : null
    const run: EnrichmentRun = {
      type: enrichmentType.value,
      geneSet: geneSet.value,
      fdr,
      geneCount: genes.length,
      clusterLabel:
        selected.length === 1 ? selected[0]!.title : `${selected.length} clusters (pooled)`,
      background: enrichmentBackground.value,
      backgroundSize: background?.length ?? 0
    }
    clearEnrichment()
    enrichmentRun.value = run
    const controller = start('enrich')
    try {
      const response =
        run.type === 'hpo'
          ? await networkApi.enrichHPO(
              { cluster_genes: genes, background_genes: background, fdr_threshold: fdr },
              controller.signal
            )
          : await networkApi.enrichGO(
              {
                cluster_genes: genes,
                background_genes: background,
                gene_set: run.geneSet,
                fdr_threshold: fdr
              },
              controller.signal
            )
      if (controller.signal.aborted) return
      enrichmentResults.value = response
      window.logService?.info(
        `Found ${response.total_terms} significant terms in ${run.clusterLabel} (${genes.length} genes)`
      )
    } catch (error) {
      if (controller.signal.aborted) return
      window.logService?.error('Failed to run enrichment:', error)
      enrichmentError.value = errorMessage(error, 'Failed to run enrichment analysis')
    } finally {
      finish('enrich', controller)
    }
  }

  /** Results at the current FDR; a stricter FDR filters client-side, a looser one re-runs */
  const visibleEnrichmentTerms = computed(() => {
    const results = enrichmentResults.value?.results ?? []
    const fdr = Number(fdrThreshold.value)
    return fdr > 0 ? results.filter(r => r.fdr <= fdr) : results
  })

  const onFdrChange = (value: unknown) => {
    fdrThreshold.value = Number(value)
    const run = enrichmentRun.value
    if (run && fdrThreshold.value > run.fdr) void runEnrichment()
  }

  // Type or gene set changed: the old results no longer answer the question, so re-run
  watch([enrichmentType, geneSet, enrichmentBackground], () => {
    const run = enrichmentRun.value
    if (!run) return
    if (
      run.type !== enrichmentType.value ||
      run.background !== enrichmentBackground.value ||
      (run.type === 'go' && run.geneSet !== geneSet.value)
    )
      void runEnrichment()
  })

  const reset = () => {
    abortAll()
    filteredGenes.value = []
    networkData.value = null
    clusterData.value = null
    clusterStats.value = null
    networkError.value = null
    networkGenes.value = []
    builtParams.value = null
    builtKey.value = null
    clusteredWith.value = null
    selectedClusters.value = []
    clusterLabelTerms.value = new Map()
    clearEnrichment()
    hpoClassifications.value = null

    selectedTiers.value = [...DEFAULT_TIERS]
    minScore.value = cfg.geneSelection.defaultMinScore
    maxGenes.value = cfg.geneSelection.defaultMaxGenes
    minStringScore.value = cfg.networkConstruction.defaultMinStringScore
    clusterAlgorithm.value = cfg.networkConstruction.defaultClusteringAlgorithm
    removeIsolated.value = cfg.filtering.defaultRemoveIsolated
    minDegree.value = cfg.filtering.defaultMinDegree
    minClusterSize.value = cfg.filtering.defaultMinClusterSize
    largestComponentOnly.value = cfg.filtering.defaultLargestComponentOnly
    enrichmentType.value = cfg.enrichment.defaultEnrichmentType
    enrichmentBackground.value = 'reference'
    geneSet.value = cfg.enrichment.goGeneSets[0]!
    fdrThreshold.value = cfg.enrichment.defaultFdrThreshold
  }

  return {
    // gene selection
    selectedTiers,
    minScore,
    maxGenes,
    filteredGenes,
    loadingGenes,
    // network
    minStringScore,
    clusterAlgorithm,
    removeIsolated,
    minDegree,
    minClusterSize,
    clusteredWith,
    largestComponentOnly,
    buildingNetwork,
    clustering,
    networkData,
    clusterData,
    clusterStats,
    networkError,
    networkGenes,
    builtParams,
    displayNetwork,
    networkGeneIds,
    clusterList,
    clusterIdMapping,
    clusterColors,
    clusterLabels,
    hgncIds,
    hiddenGenes,
    nextStep,
    // enrichment
    selectedClusters,
    enrichmentType,
    enrichmentBackground,
    geneSet,
    fdrThreshold,
    runningEnrichment,
    enrichmentResults,
    enrichmentError,
    enrichmentRun,
    visibleEnrichmentTerms,
    hpoClassifications,
    loadingHPOClassifications,
    // actions
    fetchFilteredGenes,
    buildNetwork,
    clusterNetwork,
    runEnrichment,
    fetchHPOClassifications,
    onFdrChange,
    reset
  }
}

export default useNetworkAnalysis
