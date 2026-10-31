<script setup lang="ts">
/**
 * AlphaFold predicted model of the gene's canonical UniProt protein, coloured by pLDDT, with
 * ClinVar missense variants as spheres on their C-alpha atoms (colours from variantColors.ts,
 * same as the 2D plots). The variant list is the accessible equivalent of the canvas.
 * NGL is imported dynamically on mount (SSG-safe, own chunk) and runs without web workers:
 * the production CSP has no worker-src / blob:.
 */
import {
  computed,
  markRaw,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  useTemplateRef,
  watch
} from 'vue'
import type {
  Colormaker,
  PickingProxy,
  RepresentationElement,
  Stage,
  StructureComponent
} from 'ngl'
import { Download, ExternalLink, Eye, EyeOff, FilterX, RotateCcw, Search, X } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Chip, DataState } from '@/components/shared'
import { useAppTheme } from '@/composables/useAppTheme'
import {
  SIGNIFICANCE,
  computedColor,
  featureColor,
  significanceColor
} from '@/components/gene/variantColors'
import { STATUS_TONE_CLASSES } from '@/utils/status'
import { ontologyUrl } from '@/utils/ontology'
import { downloadFile, fileSlug } from '@/utils/csv'
import type { usePositionStats } from '@/composables/usePositionStats'
import { residueRanges } from '@/utils/stats/sentences'
import SpatialStatistics from './stats/SpatialStatistics.vue'
import {
  CATEGORY_ORDER,
  PLDDT_BINS,
  alphafoldEntryUrl,
  caSelection,
  cssHex,
  featureByResidue,
  fetchModel,
  filterVariants,
  mapMissenseVariants,
  plddtColor,
  proteinRegions,
  residuesByCategory,
  type AlphaFoldEntry,
  type ClinVarProteinVariant,
  type MissenseVariant,
  type ProteinFeature
} from '@/utils/alphafold'

interface UniProtData {
  accession?: string
  length?: number
  protein_name?: string
  gene_symbol?: string
  domains?: ProteinFeature[]
}

const props = defineProps<{
  uniprotData: UniProtData | null
  clinvarData?: { protein_variants?: ClinVarProteinVariant[]; last_updated?: string } | null
  /** The page's position statistics (Ruling R2: one instance per page); 3D runs on our model */
  stats?: ReturnType<typeof usePositionStats>
}>()

type Representation = 'cartoon' | 'backbone' | 'ball+stick'
const REPRESENTATIONS: { value: Representation; label: string }[] = [
  { value: 'cartoon', label: 'Cartoon' },
  { value: 'backbone', label: 'Backbone' },
  { value: 'ball+stick', label: 'Atoms' }
]

const { isDark } = useAppTheme()
const viewport = useTemplateRef('viewport')
const status = ref<'loading' | 'ready' | 'empty' | 'error' | 'nowebgl'>('loading')
const errorMessage = ref('')
const model = ref<AlphaFoldEntry | null>(null)
const representation = ref<Representation>('cartoon')
// Colour the chain by AlphaFold confidence or by UniProt feature (same colours as the 2D view)
const COLOR_MODES = [
  { value: 'plddt', label: 'Confidence', title: 'Colour by AlphaFold model confidence (pLDDT)' },
  { value: 'domains', label: 'Domains', title: 'Colour by UniProt domains and regions' },
  {
    value: 'hotspots',
    label: 'Hotspots',
    title: 'Colour the significant 3D hotspot residues (see Spatial statistics below)'
  }
] as const
const colorMode = ref<(typeof COLOR_MODES)[number]['value']>('plddt')
// Filters: classifications (multi-select), one UniProt domain/region, free text
const selectedCategories = ref<string[]>([...CATEGORY_ORDER])
const regionKey = ref('all')
const query = ref('')
// Residues of a selected 3D hotspot cluster (from Spatial statistics)
const residueFilter = ref<number[] | null>(null)
const focusedKey = ref<string | null>(null)
const hover = ref<{ x: number; y: number; title: string; lines: string[] } | null>(null)

// NGL objects stay out of Vue reactivity
let NGL: typeof import('ngl') | null = null
let stage: Stage | null = null
let structure: StructureComponent | null = null
let mainRep: RepresentationElement | null = null
let focusRep: RepresentationElement | null = null
let variantReps: RepresentationElement[] = []
let resizeObserver: InstanceType<typeof window.ResizeObserver> | null = null
let abort: InstanceType<typeof window.AbortController> | null = null
let colorScheme = ''
let disposed = false

const accession = computed(() => props.uniprotData?.accession ?? '')
const mapping = computed(() =>
  mapMissenseVariants(props.clinvarData?.protein_variants, {
    length: props.uniprotData?.length,
    model: model.value ?? undefined
  })
)
const regions = computed(() => proteinRegions(props.uniprotData?.domains))
const region = computed(() => regions.value.find(r => r.key === regionKey.value) ?? null)
// Chip counts follow the region and search, so they say what a click will show
const inScope = computed(() => {
  const list = filterVariants(mapping.value.mapped, {
    categories: CATEGORY_ORDER,
    region: region.value,
    query: query.value
  })
  const only = residueFilter.value && new Set(residueFilter.value)
  return only ? list.filter(v => only.has(v.residue)) : list
})
const categories = computed(() =>
  CATEGORY_ORDER.map(key => ({
    key,
    label: SIGNIFICANCE[key]?.label ?? 'Other',
    color: significanceColor(key),
    count: inScope.value.filter(v => v.category === key).length,
    present: mapping.value.mapped.some(v => v.category === key)
  })).filter(c => c.present)
)
const visible = computed(() =>
  inScope.value.filter(v => selectedCategories.value.includes(v.category))
)
// Pinned variants (one or several, picked in the list): while any are pinned, 3D shows only them
const pinned = ref<string[]>([])
const shown = computed(() =>
  pinned.value.length
    ? mapping.value.mapped.filter(v => pinned.value.includes(variantKey(v)))
    : visible.value
)
const isPinned = (v: MissenseVariant) => pinned.value.includes(variantKey(v))
const togglePin = (v: MissenseVariant) => {
  const key = variantKey(v)
  pinned.value = isPinned(v) ? pinned.value.filter(k => k !== key) : [...pinned.value, key]
}
const pinListed = () => {
  pinned.value = [...new Set([...pinned.value, ...visible.value.map(variantKey)])]
}
const filtersActive = computed(
  () =>
    !!region.value ||
    !!query.value.trim() ||
    !!residueFilter.value ||
    categories.value.some(c => !selectedCategories.value.includes(c.key))
)
const regionCount = (r: { start: number; end: number }) =>
  mapping.value.mapped.filter(v => v.residue >= r.start && v.residue <= r.end).length
const partialModel = computed(() => {
  const m = model.value
  const length = props.uniprotData?.length
  return m && length && (m.uniprotStart > 1 || m.uniprotEnd < length)
})
// Significant 3D hotspot residues for the Hotspots colour mode
const hotspotResidues = computed(
  () => new Set(props.stats?.spatial.value?.hotspots.clusters.flatMap(c => c.residues) ?? [])
)
const modelLabel = computed(() =>
  model.value ? `${model.value.entryId} v${model.value.latestVersion}` : undefined
)
const showList = computed(() => status.value === 'loading' || status.value === 'ready')
const viewerLabel = computed(
  () =>
    `AlphaFold predicted model of ${props.uniprotData?.protein_name ?? accession.value}, ` +
    `coloured by pLDDT confidence, with ${shown.value.length} ClinVar missense variants ` +
    'marked as spheres. The variant list beside the viewer lists the same variants.'
)
const emptyMessage = computed(() =>
  accession.value
    ? `AlphaFold DB has no predicted model for ${accession.value}.`
    : 'No UniProt accession for this gene, so no AlphaFold model can be shown.'
)

const variantKey = (v: MissenseVariant) => `${v.accession}-${v.proteinChange}`
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
const duration = () => (reducedMotion() ? 0 : 600)

const newColorCtx = () =>
  document.createElement('canvas').getContext('2d', { willReadFrequently: true })
let colorCtx: ReturnType<typeof newColorCtx> = null
/** CSS colour (tokens, color-mix, oklch) -> 0xRRGGBB for NGL, via one canvas pixel */
function nglColor(css: string): number {
  colorCtx ??= newColorCtx()
  if (!colorCtx) return 0x808080
  colorCtx.clearRect(0, 0, 1, 1)
  colorCtx.fillStyle = computedColor(css, viewport.value)
  colorCtx.fillRect(0, 0, 1, 1)
  const [r, g, b] = colorCtx.getImageData(0, 0, 1, 1).data
  return (r! << 16) | (g! << 8) | b!
}

function hasWebGL(): boolean {
  try {
    const canvas = document.createElement('canvas')
    return !!(canvas.getContext('webgl2') ?? canvas.getContext('webgl'))
  } catch {
    return false
  }
}

function createStage(ngl: typeof import('ngl'), el: NonNullable<typeof viewport.value>): Stage {
  const s = markRaw(
    new ngl.Stage(el, {
      backgroundColor: cssHex(nglColor('var(--card)')),
      workerDefault: false, // blob: workers are blocked by the production CSP
      tooltip: false
    })
  )
  s.signals.hovered.add(onHover)
  resizeObserver = new window.ResizeObserver(() => s.handleResize())
  resizeObserver.observe(el)
  return s
}

async function load() {
  abort?.abort()
  abort = new window.AbortController()
  status.value = 'loading'
  errorMessage.value = ''
  hover.value = null
  focusedKey.value = null
  if (!accession.value) return void (status.value = 'empty')
  if (!hasWebGL()) return void (status.value = 'nowebgl')
  try {
    const signal = abort.signal
    // The viewer library downloads while the model metadata and file arrive, not after them
    const [loaded, ngl] = await Promise.all([fetchModel(accession.value), NGL ?? import('ngl')])
    NGL = ngl
    if (signal.aborted || disposed) return
    model.value = loaded?.entry ?? null
    if (!loaded) return void (status.value = 'empty')
    if (!viewport.value) return
    stage ??= createStage(NGL, viewport.value)
    stage.removeAllComponents()
    mainRep = focusRep = null
    variantReps = []
    const component = await stage.loadFile(loaded.file, {
      ext: 'cif',
      defaultRepresentation: false
    })
    if (signal.aborted || disposed || !component) return
    structure = markRaw(component as StructureComponent)
    renderMain()
    renderVariants()
    structure.autoView()
    status.value = 'ready'
  } catch (err) {
    if (abort?.signal.aborted || disposed) return
    errorMessage.value = err instanceof Error ? err.message : String(err)
    status.value = 'error'
  }
}

function renderMain() {
  if (!structure || !NGL) return
  if (mainRep) structure.removeRepresentation(mainRep)
  if (colorScheme) NGL.ColormakerRegistry.removeScheme(colorScheme)
  // Base colour: AlphaFold's pLDDT bins (stored in the B-factor column), or the 2D protein
  // view's feature colours. A selected region keeps it; the rest recedes to a neutral tone.
  const byFeature = colorMode.value === 'domains' ? featureByResidue(regions.value) : null
  const hot = colorMode.value === 'hotspots' ? hotspotResidues.value : null
  const hotTint = nglColor(significanceColor('pathogenic'))
  const featureTint = new Map(regions.value.map(f => [f.type, nglColor(featureColor(f.type))]))
  const chain = nglColor(featureColor('Chain'))
  const r = region.value
  const muted = nglColor('color-mix(in oklch, var(--muted-foreground) 35%, var(--card))')
  // Function form: NGL's addScheme does not recognise Colormaker subclasses
  // eslint-disable-next-line no-unused-vars -- TypeScript `this` parameter
  colorScheme = NGL.ColormakerRegistry.addScheme(function (this: Colormaker) {
    this.atomColor = atom => {
      if (r && (atom.resno < r.start || atom.resno > r.end)) return muted
      if (hot) return hot.has(atom.resno) ? hotTint : muted
      if (!byFeature) return plddtColor(atom.bfactor)
      const f = byFeature.get(atom.resno)
      return f ? featureTint.get(f.type)! : chain
    }
  })
  mainRep = structure.addRepresentation(representation.value, { colorScheme })
}

function showRegion() {
  renderMain()
  const r = region.value
  if (r) structure?.autoView(`${r.start}-${r.end}`, duration())
  else structure?.autoView(duration())
}

function clearFilters() {
  selectedCategories.value = [...CATEGORY_ORDER]
  regionKey.value = 'all'
  query.value = ''
  residueFilter.value = null
}

function selectCluster(residues: number[]) {
  // Second click on the selected hotspot clears the filter (toggle)
  if (residueFilter.value?.join(',') === residues.join(',')) {
    residueFilter.value = null
    structure?.autoView(duration())
    return
  }
  residueFilter.value = residues
  colorMode.value = 'hotspots' // the zoom target is legible only when tinted
  structure?.autoView(caSelection(residues), duration())
  // The hotspot table sits below the viewer: bring the zoom into view
  viewport.value?.scrollIntoView({
    block: 'nearest',
    behavior: reducedMotion() ? 'auto' : 'smooth'
  })
}

// Above this many pinned residues labels become clutter; the spheres alone stay readable
const MAX_PINNED_LABELS = 10

function renderVariants() {
  if (!structure || !NGL) return
  for (const rep of variantReps) structure.removeRepresentation(rep)
  variantReps = [...residuesByCategory(shown.value)].map(([category, residues]) =>
    structure!.addRepresentation('spacefill', {
      sele: caSelection(residues),
      color: nglColor(significanceColor(category)),
      radiusType: 'size',
      radiusSize: 1.8
    })
  )
  if (!pinned.value.length) return
  const byResidue = new Map<number, MissenseVariant[]>()
  for (const v of shown.value) byResidue.set(v.residue, [...(byResidue.get(v.residue) ?? []), v])
  if (!byResidue.size || byResidue.size > MAX_PINNED_LABELS) return
  const sele = caSelection([...byResidue.keys()])
  const labelText: string[] = [] // sparse, indexed by atom index
  structure.structure.eachAtom(atom => {
    const here = byResidue.get(atom.resno)!
    // ASCII only: NGL's glyph atlas lacks typographic characters
    labelText[atom.index] =
      here.length > 1 ? `${atom.resno} (${here.length})` : here[0]!.proteinChange.slice(2)
  }, new NGL.Selection(sele))
  variantReps.push(
    structure.addRepresentation('label', {
      sele,
      labelType: 'text',
      labelText,
      color: nglColor('var(--foreground)'),
      fontFamily: 'sans-serif',
      fontSize: 12,
      yOffset: 2,
      zOffset: 4, // toward the camera so ribbons don't hide it
      fixedSize: true,
      attachment: 'middle-center',
      showBackground: true,
      backgroundColor: nglColor('var(--card)'),
      backgroundOpacity: 0.8,
      backgroundMargin: 2
    })
  )
}

function focusVariant(v: MissenseVariant) {
  if (!structure) return
  focusedKey.value = variantKey(v)
  if (focusRep) structure.removeRepresentation(focusRep)
  focusRep = structure.addRepresentation('ball+stick', {
    sele: String(v.residue),
    colorScheme: 'element',
    radiusScale: 1.4
  })
  structure.autoView(`${Math.max(1, v.residue - 8)}-${v.residue + 8}`, duration())
}

function resetView() {
  if (!structure) return
  if (focusRep) structure.removeRepresentation(focusRep)
  focusRep = null
  focusedKey.value = null
  structure.autoView(duration())
}

async function exportPng() {
  if (!stage || !model.value) return
  const blob = await stage.makeImage({
    factor: 2,
    antialias: true,
    trim: false,
    transparent: false
  })
  const gene = fileSlug(props.uniprotData?.gene_symbol ?? accession.value)
  downloadFile(
    blob,
    `${gene}_${model.value.entryId}_v${model.value.latestVersion}.png`,
    'image/png'
  )
}

function onHover(pp: PickingProxy | undefined) {
  const atom = pp?.atom
  if (!pp || !atom) return void (hover.value = null)
  const here = shown.value.filter(v => v.residue === atom.resno)
  hover.value = {
    x: pp.canvasPosition.x,
    y: pp.canvasPosition.y,
    title: `${atom.resname} ${atom.resno} · pLDDT ${atom.bfactor.toFixed(1)}`,
    lines: here.map(v => `${v.proteinChange} · ${SIGNIFICANCE[v.category]?.label ?? 'Other'}`)
  }
}

const toggleCategory = (key: string) => {
  selectedCategories.value = selectedCategories.value.includes(key)
    ? selectedCategories.value.filter(k => k !== key)
    : [...selectedCategories.value, key]
}

watch([representation, colorMode], renderMain)
// A new run (gene, star filter) clears the hotspots: leave the mode and the cluster filter
watch(hotspotResidues, hot => {
  if (!hot.size) {
    residueFilter.value = null
    if (colorMode.value === 'hotspots') colorMode.value = 'plddt'
  } else if (colorMode.value === 'hotspots') renderMain()
})
watch(region, showRegion)
watch(shown, renderVariants)
watch(accession, load)
// Background and variant colours follow the theme tokens
watch(isDark, () =>
  nextTick(() => {
    stage?.setParameters({ backgroundColor: cssHex(nglColor('var(--card)')) })
    renderMain() // muted and feature colours are theme tokens
    renderVariants()
  })
)

onMounted(load)
onBeforeUnmount(() => {
  disposed = true
  abort?.abort()
  resizeObserver?.disconnect()
  stage?.dispose()
  stage = structure = mainRep = focusRep = null
  variantReps = []
})
</script>

<template>
  <section class="space-y-3" aria-label="3D protein structure">
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div class="min-w-0">
        <h2 class="text-sm font-semibold">AlphaFold predicted model</h2>
        <p class="text-xs text-muted-foreground">
          <template v-if="model">
            <a
              :href="alphafoldEntryUrl(accession)"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1 rounded-sm font-mono text-primary hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            >
              {{ model.entryId }}
              <ExternalLink class="size-3" aria-hidden="true" />
              <span class="sr-only">(AlphaFold DB, opens in a new tab)</span>
            </a>
            · model v{{ model.latestVersion }}
            <template v-if="model.globalMetricValue != null">
              · mean pLDDT
              <span class="tabular-nums">{{ model.globalMetricValue.toFixed(1) }}</span>
            </template>
            · predicted, not experimentally determined
          </template>
          <template v-else>
            Predicted structure from AlphaFold DB, not experimentally determined
          </template>
        </p>
      </div>
      <div role="toolbar" aria-label="3D view controls" class="flex flex-wrap items-center gap-1.5">
        <div role="group" aria-label="Colour the chain by" class="inline-flex rounded-md border">
          <Button
            v-for="m in COLOR_MODES"
            :key="m.value"
            type="button"
            variant="ghost"
            size="sm"
            class="h-7 rounded-none px-2.5 text-xs first:rounded-l-md last:rounded-r-md"
            :class="colorMode === m.value ? 'bg-muted font-semibold' : 'text-muted-foreground'"
            :aria-pressed="colorMode === m.value"
            :disabled="
              status !== 'ready' ||
              (m.value === 'domains' && !regions.length) ||
              (m.value === 'hotspots' && !hotspotResidues.size)
            "
            :title="m.title"
            @click="colorMode = m.value"
          >
            {{ m.label }}
          </Button>
        </div>
        <div role="group" aria-label="Representation" class="inline-flex rounded-md border">
          <Button
            v-for="r in REPRESENTATIONS"
            :key="r.value"
            type="button"
            variant="ghost"
            size="sm"
            class="h-7 rounded-none px-2.5 text-xs first:rounded-l-md last:rounded-r-md"
            :class="representation === r.value ? 'bg-muted font-semibold' : 'text-muted-foreground'"
            :aria-pressed="representation === r.value"
            :disabled="status !== 'ready'"
            @click="representation = r.value"
          >
            {{ r.label }}
          </Button>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          class="h-7 text-xs"
          :disabled="status !== 'ready'"
          @click="resetView"
        >
          <RotateCcw aria-hidden="true" />
          Reset view
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          class="h-7 text-xs"
          :disabled="status !== 'ready'"
          @click="exportPng"
        >
          <Download aria-hidden="true" />
          PNG
        </Button>
      </div>
    </div>

    <div class="grid gap-4" :class="showList && 'lg:grid-cols-[minmax(0,1fr)_21rem]'">
      <div class="relative h-[22rem] overflow-hidden rounded-lg border bg-card sm:h-[30rem]">
        <div
          ref="viewport"
          class="ngl-viewport absolute inset-0"
          role="img"
          :aria-label="viewerLabel"
        />
        <div
          v-if="hover"
          class="pointer-events-none absolute z-10 max-w-60 rounded-md border bg-popover px-2 py-1 text-xs text-popover-foreground shadow-md"
          :style="{ left: `${hover.x + 12}px`, bottom: `${hover.y + 12}px` }"
          aria-hidden="true"
        >
          <p class="font-medium">{{ hover.title }}</p>
          <p v-for="line in hover.lines" :key="line" class="font-mono">{{ line }}</p>
        </div>
        <div v-if="status !== 'ready'" class="absolute inset-0 flex items-center bg-card p-4">
          <p
            v-if="status === 'nowebgl'"
            role="status"
            class="w-full text-center text-sm text-muted-foreground"
          >
            The 3D view needs WebGL, which this browser does not support or has turned off.
          </p>
          <DataState
            v-else
            :class="status === 'loading' ? 'h-full w-full' : 'w-full'"
            :loading="status === 'loading'"
            :error="status === 'error' ? errorMessage || true : null"
            :empty="status === 'empty'"
            :empty-message="emptyMessage"
            error-title="Could not load the AlphaFold model"
            @retry="load"
          >
            <template #loading>
              <div
                class="h-full rounded-md bg-muted motion-safe:animate-pulse"
                aria-hidden="true"
              />
            </template>
          </DataState>
        </div>
      </div>

      <aside
        v-if="showList"
        class="flex min-h-0 flex-col rounded-lg border bg-card lg:h-[30rem]"
        aria-labelledby="missense-list-title"
      >
        <div class="space-y-2 border-b p-3">
          <div class="flex items-baseline justify-between gap-2">
            <h3 id="missense-list-title" class="text-sm font-semibold">
              ClinVar missense variants
            </h3>
            <span
              v-if="status === 'ready'"
              class="flex shrink-0 items-center gap-1 text-xs whitespace-nowrap text-muted-foreground tabular-nums"
              aria-live="polite"
            >
              {{ visible.length }} of {{ mapping.mapped.length }}
              <Button
                v-if="filtersActive"
                type="button"
                variant="ghost"
                size="sm"
                class="h-6 gap-1 px-1.5 text-xs"
                @click="clearFilters"
              >
                <FilterX aria-hidden="true" />
                Clear
              </Button>
            </span>
          </div>
          <div class="relative">
            <Search
              class="pointer-events-none absolute top-1/2 left-2 size-3.5 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              v-model="query"
              type="search"
              placeholder="Search p.Arg177, VCV or residue"
              aria-label="Search missense variants by protein change, ClinVar ID or residue"
              class="h-8 pl-7 text-xs"
              :disabled="status !== 'ready'"
            />
          </div>
          <Select v-if="regions.length" v-model="regionKey" :disabled="status !== 'ready'">
            <SelectTrigger class="h-8 w-full text-xs" aria-label="Domain or region">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" class="text-xs">
                Whole protein · {{ mapping.mapped.length }}
              </SelectItem>
              <SelectItem v-for="r in regions" :key="r.key" :value="r.key" class="text-xs">
                {{ r.label }}
                <span class="text-muted-foreground tabular-nums">
                  {{ r.type }} {{ r.start }}–{{ r.end }} · {{ regionCount(r) }}
                </span>
              </SelectItem>
            </SelectContent>
          </Select>
          <div
            v-if="categories.length"
            role="group"
            aria-label="Classification filter"
            class="flex flex-wrap items-center gap-1.5"
          >
            <Button
              v-for="c in categories"
              :key="c.key"
              type="button"
              variant="outline"
              size="sm"
              class="h-7 gap-1.5 px-2 text-xs"
              :class="
                selectedCategories.includes(c.key)
                  ? 'bg-muted font-medium'
                  : 'text-muted-foreground'
              "
              :aria-pressed="selectedCategories.includes(c.key)"
              @click="toggleCategory(c.key)"
            >
              <span
                class="size-2.5 shrink-0 rounded-full border border-border"
                :style="{
                  backgroundColor: selectedCategories.includes(c.key) ? c.color : 'transparent'
                }"
                aria-hidden="true"
              />
              {{ c.label }}
              <span class="tabular-nums">{{ c.count }}</span>
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              class="h-7 px-2 text-xs"
              @click="selectedCategories = [...CATEGORY_ORDER]"
            >
              All
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              class="h-7 px-2 text-xs"
              @click="selectedCategories = []"
            >
              None
            </Button>
          </div>
          <p v-if="residueFilter" class="text-xs font-medium">
            3D hotspot residues {{ residueRanges(residueFilter) }} only
          </p>
          <p v-if="status === 'ready' && partialModel" class="text-xs text-muted-foreground">
            This model covers residues {{ model?.uniprotStart }}–{{ model?.uniprotEnd }} of
            {{ uniprotData?.length }}.
          </p>
          <p v-if="status === 'ready' && mapping.dropped" class="text-xs text-muted-foreground">
            {{ mapping.dropped }} missense
            {{ mapping.dropped === 1 ? 'variant is' : 'variants are' }} not shown: the residue is
            outside the model or its reference amino acid differs from the UniProt sequence.
          </p>
          <!-- One fixed-height row with the same controls in every state: pinning never moves the list -->
          <div
            v-if="status === 'ready'"
            class="flex h-7 items-center gap-1 text-xs whitespace-nowrap"
          >
            <span
              class="inline-flex min-w-0 flex-1 items-center gap-1"
              :class="pinned.length ? 'font-medium' : 'text-muted-foreground'"
              aria-live="polite"
              :title="
                pinned.length ? '' : 'Pin variants with the eye button to show only those in 3D'
              "
            >
              <Eye v-if="pinned.length" class="size-3.5 shrink-0 text-primary" aria-hidden="true" />
              <EyeOff v-else class="size-3.5 shrink-0" aria-hidden="true" />
              <span class="truncate">
                {{ pinned.length ? `3D: ${pinned.length} pinned` : '3D: all listed' }}
              </span>
            </span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              class="h-7 px-2 text-xs"
              :disabled="!visible.length || visible.every(isPinned)"
              @click="pinListed"
            >
              Pin listed
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              class="h-7 gap-1 px-2 text-xs"
              :disabled="!pinned.length"
              @click="pinned = []"
            >
              <X aria-hidden="true" />
              Unpin all
            </Button>
          </div>
        </div>
        <ul v-if="status === 'loading'" class="space-y-2 p-3" aria-hidden="true">
          <li v-for="i in 8" :key="i" class="h-8 rounded-md bg-muted motion-safe:animate-pulse" />
        </ul>
        <div v-else-if="!visible.length" class="space-y-2 p-3 text-sm text-muted-foreground">
          <p>
            {{
              mapping.mapped.length
                ? 'No variants match these filters.'
                : 'No ClinVar missense variants map onto this model.'
            }}
          </p>
        </div>
        <ul v-else class="max-h-80 min-h-0 flex-1 overflow-y-auto lg:max-h-none">
          <li
            v-for="v in visible"
            :key="variantKey(v)"
            class="relative border-b py-1.5 pr-10 pl-3 last:border-0"
            :class="focusedKey === variantKey(v) && 'bg-muted'"
          >
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              class="absolute top-1 right-1"
              :class="isPinned(v) ? 'text-primary' : 'text-muted-foreground'"
              :aria-pressed="isPinned(v)"
              :aria-label="`${isPinned(v) ? 'Unpin' : 'Pin'} ${v.proteinChange} in the 3D view`"
              :title="isPinned(v) ? 'Unpin from the 3D view' : 'Pin: show in the 3D view'"
              @click="togglePin(v)"
            >
              <Eye v-if="isPinned(v)" aria-hidden="true" />
              <EyeOff v-else aria-hidden="true" />
            </Button>
            <button
              type="button"
              class="flex min-h-6 w-full items-center gap-2 rounded-sm text-left focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
              :aria-current="focusedKey === variantKey(v) ? 'true' : undefined"
              :title="`Zoom to residue ${v.residue} in the 3D view`"
              @click="focusVariant(v)"
            >
              <span
                class="size-2.5 shrink-0 rounded-full"
                :style="{ backgroundColor: significanceColor(v.category) }"
                aria-hidden="true"
              />
              <span class="min-w-0 flex-1 truncate font-mono text-xs">{{ v.proteinChange }}</span>
              <Chip
                kind="neutral"
                :class="STATUS_TONE_CLASSES[SIGNIFICANCE[v.category]?.tone ?? 'neutral']"
                :label="SIGNIFICANCE[v.category]?.label ?? (v.classification || 'Other')"
              />
            </button>
            <a
              v-if="v.accession"
              :href="ontologyUrl(v.accession, 'ClinVar') ?? undefined"
              target="_blank"
              rel="noopener noreferrer"
              class="ml-4.5 inline-flex min-h-6 items-center gap-1 rounded-sm font-mono text-xs text-primary hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            >
              {{ v.accession }}
              <ExternalLink class="size-3" aria-hidden="true" />
              <span class="sr-only">(ClinVar, opens in a new tab)</span>
            </a>
          </li>
        </ul>
      </aside>
    </div>

    <div class="space-y-1 text-xs text-muted-foreground">
      <!-- Domain colouring: the legend doubles as the domain filter (same state as the select) -->
      <div
        v-if="colorMode === 'domains'"
        role="group"
        aria-label="Domains and regions: select one to filter variants and zoom to it"
        class="flex flex-wrap items-center gap-1.5"
      >
        <span class="mr-1 font-medium text-foreground">Domains and regions</span>
        <Button
          v-for="r in regions"
          :key="r.key"
          type="button"
          variant="outline"
          size="sm"
          class="h-7 gap-1.5 px-2 text-xs"
          :class="regionKey === r.key ? 'bg-muted font-medium text-foreground' : ''"
          :aria-pressed="regionKey === r.key"
          :disabled="status !== 'ready'"
          @click="regionKey = regionKey === r.key ? 'all' : r.key"
        >
          <span
            class="size-2.5 shrink-0 rounded-sm"
            :style="{ backgroundColor: featureColor(r.type) }"
            aria-hidden="true"
          />
          {{ r.label }}
          <span class="tabular-nums text-muted-foreground">{{ r.start }}–{{ r.end }}</span>
        </Button>
        <span class="inline-flex items-center gap-1.5">
          <span
            class="size-2.5 shrink-0 rounded-sm"
            :style="{ backgroundColor: featureColor('Chain') }"
            aria-hidden="true"
          />
          No annotated feature
        </span>
      </div>
      <div v-else-if="colorMode === 'hotspots'" class="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span class="font-medium text-foreground">3D hotspots</span>
        <span class="inline-flex items-center gap-1.5">
          <span
            class="size-2.5 shrink-0 rounded-sm"
            :style="{ backgroundColor: significanceColor('pathogenic') }"
            aria-hidden="true"
          />
          Significant hotspot residue (family-wise adjusted p &lt; 0.05)
        </span>
        <span class="inline-flex items-center gap-1.5">
          <span
            class="size-2.5 shrink-0 rounded-sm"
            :style="{
              backgroundColor: 'color-mix(in oklch, var(--muted-foreground) 35%, var(--card))'
            }"
            aria-hidden="true"
          />
          Other residues
        </span>
      </div>
      <div v-else class="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span class="font-medium text-foreground">Model confidence (pLDDT)</span>
        <span v-for="bin in PLDDT_BINS" :key="bin.label" class="inline-flex items-center gap-1.5">
          <span
            class="size-2.5 shrink-0 rounded-sm"
            :style="{ backgroundColor: cssHex(bin.color) }"
            aria-hidden="true"
          />
          {{ bin.label }} <span class="tabular-nums">({{ bin.range }})</span>
        </span>
      </div>
      <p>
        Spheres mark residues with ClinVar missense variants, coloured by classification (the most
        severe one when a residue has several). Structure from
        <a
          href="https://alphafold.ebi.ac.uk/"
          target="_blank"
          rel="noopener noreferrer"
          class="text-primary hover:underline"
          >AlphaFold DB</a
        >
        (Google DeepMind and EMBL-EBI), licensed
        <a
          href="https://creativecommons.org/licenses/by/4.0/"
          target="_blank"
          rel="noopener noreferrer"
          class="text-primary hover:underline"
          >CC BY 4.0</a
        >; cite Jumper et al., Nature 2021 and Varadi et al., Nucleic Acids Res. 2024.
      </p>
    </div>

    <SpatialStatistics
      v-if="stats"
      :state="stats"
      :model-status="status"
      :model="model && { ...model, label: modelLabel }"
      :length="uniprotData?.length"
      :clinvar-date="clinvarData?.last_updated"
      :selected="residueFilter"
      @select-cluster="selectCluster"
    />
  </section>
</template>

<style scoped>
/* NGL sizes its wrapper from the container only at creation (nglviewer/ngl#890) */
.ngl-viewport :deep(> div) {
  width: 100%;
  height: 100%;
}
</style>
