<template>
  <div class="gene-structure-visualization">
    <div v-if="hasVariants" class="mb-3 space-y-2">
      <VariantFilters
        v-model:color-by="colorBy"
        v-model:classifications="selectedClassifications"
        v-model:effects="selectedEffects"
      />
      <div class="flex flex-wrap items-center gap-2">
        <p class="text-xs text-muted-foreground">
          {{ filteredVariants.length.toLocaleString() }} shown of
          {{ allVariants.length.toLocaleString() }} loaded variants<template
            v-if="clinvarData?.total_variants"
          >
            ({{ clinvarData.total_variants.toLocaleString() }} in
            <a
              :href="clinvarUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="rounded-sm text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
              >ClinVar</a
            >)</template
          >
        </p>
        <div class="flex-1" />
        <div class="inline-flex rounded-md border" role="group" aria-label="Plot tools">
          <Button
            v-for="tool in tools"
            :key="tool.label"
            variant="ghost"
            size="icon-sm"
            class="rounded-none first:rounded-l-md last:rounded-r-md"
            :disabled="tool.disabled"
            :aria-label="tool.label"
            :title="tool.label"
            @click="tool.action"
          >
            <component :is="tool.icon" aria-hidden="true" />
          </Button>
        </div>
      </div>
    </div>

    <!-- Height is fixed from the props before drawing, so nothing below moves when the plot renders -->
    <div class="overflow-x-auto">
      <div
        ref="chartContainer"
        class="chart-container"
        :style="{ minWidth: `${MIN_PLOT_WIDTH}px`, height: `${plotHeight}px` }"
      ></div>
    </div>
    <p class="mt-1 text-xs text-muted-foreground">
      <span class="sm:hidden">Scroll sideways to see the whole plot. </span>
      <span v-if="hasVariants">
        Drag or use the buttons to zoom; double-click resets. Arrow keys move between variant
        markers, Enter shows details.
      </span>
    </p>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import { Download, ZoomIn, ZoomOut, SearchX } from 'lucide-vue-next'
import { useAppTheme } from '@/composables/useAppTheme'
import { Button } from '@/components/ui/button'
import { select, selectAll } from 'd3-selection'
import { scaleLinear } from 'd3-scale'
import { axisBottom } from 'd3-axis'
import { zoom, zoomIdentity } from 'd3-zoom'
import 'd3-transition'
import { useD3Tooltip } from '@/composables/useD3Tooltip'
import VariantFilters from '@/components/gene/VariantFilters.vue'
import {
  EFFECTS,
  SIGNIFICANCE,
  computedColor,
  effectColor,
  significanceColor
} from '@/components/gene/variantColors'

const { isDark } = useAppTheme()
const chartContainer = ref(null)
let resizeObserver = null

const {
  show: showTooltip,
  hide: hideTooltip,
  pin: pinTooltip,
  unpin: unpinTooltip,
  remove: removeTooltip,
  isPinned
} = useD3Tooltip()

const props = defineProps({
  geneSymbol: {
    type: String,
    required: true
  },
  ensemblData: {
    type: Object,
    required: true
  },
  clinvarData: {
    type: Object,
    default: null
  },
  uniprotData: {
    type: Object,
    default: null
  }
})

// Filter state
const colorBy = ref('classification') // 'classification' or 'effect'
const selectedClassifications = ref(['pathogenic', 'likely_pathogenic'])
const selectedEffects = ref(['truncating', 'missense', 'inframe', 'splice_region'])

// Zoom state
const zoomLevel = ref(1) // Current zoom level (1 = no zoom)
const isZoomed = computed(() => zoomLevel.value > 1.01)
const canZoomIn = computed(() => zoomLevel.value < MAX_ZOOM)
const canZoomOut = computed(() => zoomLevel.value > 1.01)
const MAX_ZOOM = 50

// D3 zoom behavior reference
let zoomBehavior = null
let currentTransform = zoomIdentity
const clipId = `gene-clip-${Math.random().toString(36).slice(2, 8)}`

// Variants with genomic positions (genomic_variants include splice/intronic ones)
const allVariants = computed(() => props.clinvarData?.genomic_variants ?? [])
const hasVariants = computed(() => allVariants.value.length > 0)

// Filter variants — both dimensions apply simultaneously (AND logic)
// Empty selection in a dimension means "no filter" for that dimension
const filteredVariants = computed(() => {
  let variants = allVariants.value
  if (selectedClassifications.value.length > 0) {
    variants = variants.filter(v => selectedClassifications.value.includes(v.category))
  } else {
    return [] // No classifications selected = show nothing
  }
  if (selectedEffects.value.length > 0) {
    variants = variants.filter(v => selectedEffects.value.includes(v.effect_category))
  }
  return variants
})

// SIGNIFICANCE is ordered most to least severe; unknown categories rank lowest
const SEVERITY_ORDER = Object.keys(SIGNIFICANCE)
const severity = category => {
  const i = SEVERITY_ORDER.indexOf(category)
  return i < 0 ? 0 : SEVERITY_ORDER.length - i
}
const isSplice = v =>
  v.effect_category === 'splice_region' ||
  (v.molecular_consequences ?? []).some(m => /splice/i.test(m))

// One marker per genomic position; its most severe variant leads (colour, shape, label)
const markerGroups = computed(() => {
  const byPos = new Map()
  for (const v of filteredVariants.value) {
    if (v.genomic_start === null || v.genomic_start === undefined) continue
    if (!byPos.has(v.genomic_start)) byPos.set(v.genomic_start, [])
    byPos.get(v.genomic_start).push(v)
  }
  return [...byPos].map(([pos, vs]) => {
    const variants = [...vs].sort((a, b) => severity(b.category) - severity(a.category))
    return { pos, variants, lead: variants[0] }
  })
})
const shownVariantCount = computed(() =>
  markerGroups.value.reduce((n, m) => n + m.variants.length, 0)
)

// Exons from the canonical transcript, numbered in transcript order (5'→3', strand-aware).
// The API's exon_number follows genomic order, which is reversed on the minus strand.
const exons = computed(() => {
  const transcript = props.ensemblData?.canonical_transcript
  if (!transcript?.exons) return []
  const sorted = [...transcript.exons].sort((a, b) => a.start - b.start)
  const minus = isMinus.value
  return sorted.map((exon, idx) => ({
    ...exon,
    transcript_order: minus ? sorted.length - idx : idx + 1
  }))
})

const isMinus = computed(() => ['-', -1, '-1'].includes(props.ensemblData?.strand))

// Layout (px). Everything is derived from props, so the height is known before drawing.
const MIN_PLOT_WIDTH = 720 // narrow screens scroll the plot sideways instead of crushing it
const MARGIN_X = 26 // room for the 5'/3' end labels
const CAPTION_H = 22
const EXON_H = 14
const MARKER_R = 4.5
const STEM_BASE = 18
const STEM_STEP = 10
const LEVELS = 8 // stacking levels for nearby markers
const MARKER_GAP = MARKER_R * 2 + 1 // closer than this (px) and markers stack
const lollipopZone = computed(() =>
  hasVariants.value ? STEM_BASE + STEM_STEP * (LEVELS - 1) + MARKER_R * 2 + 6 : 0
)
const exonY = computed(() => CAPTION_H + lollipopZone.value + EXON_H / 2 + 4)
const plotHeight = computed(() => exonY.value + EXON_H / 2 + 62)

// Resolved token colours: SVG attributes must survive PNG export, so no var() in the plot
// Memoised per CSS string (a DOM style read per lollipop per zoom frame); cleared per render
const colorCache = new Map()
const c = css => {
  if (!colorCache.has(css)) colorCache.set(css, computedColor(css, chartContainer.value))
  return colorCache.get(css)
}

const getVariantColor = variant =>
  colorBy.value === 'classification'
    ? c(significanceColor(variant.category))
    : c(effectColor(variant.effect_category))

const clinvarUrl = computed(
  () =>
    `https://www.ncbi.nlm.nih.gov/clinvar/?term=${encodeURIComponent(`${props.clinvarData?.gene_symbol ?? ''}[gene]`)}`
)

const tools = computed(() => [
  { label: 'Zoom in', icon: ZoomIn, disabled: !canZoomIn.value, action: zoomIn },
  { label: 'Zoom out', icon: ZoomOut, disabled: !canZoomOut.value, action: zoomOut },
  { label: 'Reset zoom', icon: SearchX, disabled: !isZoomed.value, action: resetZoom },
  { label: 'Download as PNG', icon: Download, disabled: false, action: downloadPng }
])

// Download as PNG
const downloadPng = () => {
  if (!chartContainer.value) return
  const svgEl = chartContainer.value.querySelector('svg')
  if (!svgEl) return

  const svgData = new window.XMLSerializer().serializeToString(svgEl)
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  const img = new window.Image()
  canvas.width = svgEl.clientWidth * 2
  canvas.height = svgEl.clientHeight * 2
  ctx.scale(2, 2)

  img.onload = () => {
    ctx.fillStyle = c('var(--background)')
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0)
    const link = document.createElement('a')
    link.download = `${props.geneSymbol}_structure.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
  }
  img.src = 'data:image/svg+xml;base64,' + window.btoa(unescape(encodeURIComponent(svgData)))
}

// Zoom control functions
const svgSel = () => chartContainer.value && select(chartContainer.value).select('svg')
const zoomIn = () =>
  zoomBehavior && svgSel()?.transition().duration(300).call(zoomBehavior.scaleBy, 1.5)
const zoomOut = () =>
  zoomBehavior && svgSel()?.transition().duration(300).call(zoomBehavior.scaleBy, 0.67)
const resetZoom = () =>
  zoomBehavior && svgSel()?.transition().duration(300).call(zoomBehavior.transform, zoomIdentity)

// Variant tooltip content (for both hover and pinned)
const buildVariantTooltip = (variants, isPinned = false) => {
  const count = variants.length
  let tooltipContent = `
    <div style="font-weight: 600; margin-bottom: 4px;">
      ${count} variant${count > 1 ? 's' : ''} at chr${props.ensemblData.chromosome}:${variants[0].genomic_start?.toLocaleString()}
    </div>
  `

  // Show all variants if pinned, otherwise limit to 3
  const displayVariants = isPinned ? variants : variants.slice(0, 3)

  displayVariants.forEach(v => {
    const color = c(significanceColor(v.category))
    const variantEffectColor = c(effectColor(v.effect_category))
    const clinvarId = v.accession ? v.accession.replace('VCV', '').replace(/^0+/, '') : ''

    tooltipContent += `
      <div style="border-top: 1px solid color-mix(in srgb, currentColor 15%, transparent); padding-top: 6px; margin-top: 6px;">
        <div style="font-weight: 600;">${v.protein_change || 'No protein change'}</div>
        ${v.cdna_change ? `<div style="font-size: 11px; opacity: 0.75;">${v.cdna_change}</div>` : ''}
        <div style="font-size: 11px; margin-top: 2px;">
          <span style="font-weight: 500;"><span style="display: inline-block; width: 8px; height: 8px; border-radius: 9999px; margin-right: 4px; background: ${color};"></span>${v.classification || 'Unknown'}</span>
          <span style="margin-left: 8px;"><span style="display: inline-block; width: 8px; height: 8px; ${isSplice(v) ? 'transform: rotate(45deg) scale(0.85);' : 'border-radius: 9999px;'} margin-right: 4px; background: ${variantEffectColor};"></span>${EFFECTS[v.effect_category]?.label ?? 'Other'}</span>
        </div>
        <div style="font-size: 10px; opacity: 0.75; margin-top: 2px;">
          ${v.review_status || ''} ${clinvarId ? '•' : ''}
          ${clinvarId ? `<a href="https://www.ncbi.nlm.nih.gov/clinvar/variation/${clinvarId}/" target="_blank" rel="noopener noreferrer" style="color: inherit; text-decoration: underline;">${v.accession}</a>` : ''}
        </div>
      </div>
    `
  })

  if (!isPinned && count > 3) {
    tooltipContent += `<div style="font-size: 11px; opacity: 0.75; margin-top: 6px; font-style: italic;">Click or press Enter to see all ${count} variants</div>`
  }

  return tooltipContent
}

const exonTooltip = exon => `
  <div style="font-weight: 600; margin-bottom: 4px;">Exon ${exon.transcript_order} of ${exons.value.length}</div>
  <div style="font-family: ui-monospace, monospace; font-size: 11px;">${exon.exon_id ?? ''}</div>
  <div>chr${props.ensemblData.chromosome}:${exon.start?.toLocaleString()}-${exon.end?.toLocaleString()}</div>
  <div>${(exon.length ?? exon.end - exon.start + 1).toLocaleString()} bp</div>
  <div style="font-size: 10px; opacity: 0.75; margin-top: 4px;">Numbered in transcript order (5′ to 3′)</div>
`

// A keyboard event has no pointer position; anchor the tooltip to the element instead
const anchorOf = el => {
  const r = el.getBoundingClientRect()
  return { pageX: r.right + window.scrollX, pageY: r.top + window.scrollY }
}

// Mb tick labels with just enough decimals for the current tick step
const mbFormatter = scale => {
  const ticks = scale.ticks(tickCount(scale))
  const step = ticks.length > 1 ? ticks[1] - ticks[0] : 1e6
  const decimals = Math.max(0, Math.ceil(-Math.log10(step / 1e6)))
  return d => (d / 1e6).toFixed(decimals)
}
const tickCount = scale => Math.max(3, Math.floor((scale.range()[1] - scale.range()[0]) / 110))

const renderChart = () => {
  if (!chartContainer.value || exons.value.length === 0) return

  const containerWidth = chartContainer.value.clientWidth
  const width = containerWidth - MARGIN_X * 2
  if (width < 100) return // hidden tab: the ResizeObserver redraws once it is visible

  unpinTooltip()
  colorCache.clear()
  select(chartContainer.value).selectAll('*').remove()

  const colors = {
    exon: c('var(--muted-foreground)'),
    exonHover: c('var(--foreground)'),
    intron: c('var(--muted-foreground)'),
    rule: c('var(--border)'),
    text: c('var(--foreground)'),
    muted: c('var(--muted-foreground)'),
    background: c('var(--background)')
  }
  const H = plotHeight.value
  const y0 = exonY.value
  const exonTop = y0 - EXON_H / 2
  const exonBottom = y0 + EXON_H / 2
  const axisY = exonBottom + 22
  const markerBase = exonTop - 3

  const { start: geneStart, end: geneEnd, chromosome } = props.ensemblData
  const minus = isMinus.value
  const transcript = props.ensemblData.canonical_transcript ?? {}
  const strandText = minus ? 'reverse strand' : 'forward strand'
  const lengthKb = ((geneEnd - geneStart + 1) / 1000).toFixed(1)
  const variantsShown = shownVariantCount.value

  const svg = select(chartContainer.value)
    .append('svg')
    .attr('width', containerWidth)
    .attr('height', H)
    .attr('role', 'group')
    .attr('aria-labelledby', `${clipId}-title ${clipId}-desc`)
    .attr('font-family', window.getComputedStyle(chartContainer.value).fontFamily)

  svg
    .append('title')
    .attr('id', `${clipId}-title`)
    .text(`${props.geneSymbol} gene structure with ClinVar variants`)
  svg
    .append('desc')
    .attr('id', `${clipId}-desc`)
    .text(
      `Canonical transcript ${transcript.transcript_id ?? ''}: ${exons.value.length} exons on the ${strandText}, ` +
        `${lengthKb} kb at chr${chromosome}:${geneStart?.toLocaleString()}-${geneEnd?.toLocaleString()}. ` +
        (hasVariants.value
          ? `${variantsShown} of ${allVariants.value.length} loaded ClinVar variants are shown as markers above the exons; ` +
            'nearby markers are stacked, the most severe classification is drawn on top and diamonds mark splice variants. ' +
            'Use the arrow keys to move between markers and Enter or Space to show details.'
          : 'No ClinVar variants loaded.')
    )

  svg
    .append('defs')
    .append('clipPath')
    .attr('id', clipId)
    .append('rect')
    .attr('x', -MARKER_R - 2)
    .attr('y', 0)
    .attr('width', width + MARKER_R * 2 + 4)
    .attr('height', H)

  // Caption: transcript and orientation (the card header carries IDs and coordinates)
  const caption = svg
    .append('text')
    .attr('aria-hidden', 'true')
    .attr('x', MARGIN_X)
    .attr('y', 14)
    .style('font-size', '11px')
    .style('fill', colors.muted)
  caption
    .append('tspan')
    .style('font-weight', '600')
    .style('fill', colors.text)
    .text(props.geneSymbol)
  caption
    .append('tspan')
    .text(
      [
        ` ${transcript.display_name ?? ''} ${transcript.transcript_id ?? ''}`.trimEnd(),
        `${exons.value.length} exons`,
        `${lengthKb} kb`,
        `${strandText} (5′→3′ ${minus ? 'right to left' : 'left to right'})`
      ].join(' · ')
    )

  const g = svg.append('g').attr('transform', `translate(${MARGIN_X},0)`)
  const plot = g.append('g').attr('clip-path', `url(#${clipId})`)

  // 5'/3' ends in the margins: orientation stays readable when zoomed past the gene ends
  for (const [x, anchor, label] of [
    [-6, 'end', minus ? '3′' : '5′'],
    [width + 6, 'start', minus ? '5′' : '3′']
  ]) {
    g.append('text')
      .attr('aria-hidden', 'true')
      .attr('x', x)
      .attr('y', y0 + 4)
      .attr('text-anchor', anchor)
      .style('font-size', '11px')
      .style('fill', colors.muted)
      .text(label)
  }

  const backbone = plot.append('g').attr('aria-hidden', 'true')
  const exonsGroup = plot.append('g').attr('aria-hidden', 'true')
  const labelsGroup = plot.append('g').attr('aria-hidden', 'true')
  const stemsGroup = plot.append('g').attr('aria-hidden', 'true')
  const markersGroup = plot.append('g').attr('class', 'markers')
  const axisGroup = g
    .append('g')
    .attr('aria-hidden', 'true')
    .attr('transform', `translate(0,${axisY})`)

  g.append('text')
    .attr('aria-hidden', 'true')
    .attr('x', 0)
    .attr('y', axisY + 34)
    .style('font-size', '11px')
    .style('fill', colors.muted)
    .text(`chr${chromosome} position (Mb, ${props.ensemblData.assembly ?? 'GRCh38'})`)

  // Shape key (colours are keyed by the filter chips above)
  if (hasVariants.value) {
    const key = g
      .append('g')
      .attr('aria-hidden', 'true')
      .attr('transform', `translate(${width},${axisY + 30})`)
    const keyItems = [
      ['circle', 'ClinVar variant'],
      ['diamond', 'Splice variant']
    ]
    let kx = 0
    for (const [shape, label] of [...keyItems].reverse()) {
      const t = key
        .append('text')
        .attr('x', kx)
        .attr('y', 4)
        .attr('text-anchor', 'end')
        .style('font-size', '11px')
        .style('fill', colors.muted)
        .text(label)
      kx -= t.node().getComputedTextLength?.() || label.length * 6
      key
        .append('path')
        .attr('d', shapePath(shape === 'diamond', 4))
        .attr('transform', `translate(${kx - 7},0)`)
        .attr('fill', colors.muted)
      kx -= 20
    }
  }

  const xScale = scaleLinear().domain([geneStart, geneEnd]).range([0, width])

  const draw = scale => {
    const [d0, d1] = scale.domain()

    // Intron backbone with strand chevrons; exons are drawn over it
    backbone.selectAll('*').remove()
    const bx0 = Math.max(0, scale(geneStart))
    const bx1 = Math.min(width, scale(geneEnd))
    backbone
      .append('line')
      .attr('x1', bx0)
      .attr('x2', bx1)
      .attr('y1', y0)
      .attr('y2', y0)
      .attr('stroke', colors.intron)
      .attr('stroke-width', 1)
    const dir = minus ? -1 : 1
    for (let x = bx0 + 24; x < bx1 - 12; x += 48) {
      backbone
        .append('path')
        .attr(
          'd',
          `M${x - 2.5 * dir},${y0 - 3.5}L${x + 2.5 * dir},${y0}L${x - 2.5 * dir},${y0 + 3.5}`
        )
        .attr('fill', 'none')
        .attr('stroke', colors.intron)
        .attr('stroke-width', 1.2)
    }

    // Exons: genomic scale, but never thinner than 5px so short exons stay visible
    exonsGroup.selectAll('*').remove()
    labelsGroup.selectAll('*').remove()
    let lastLabelEnd = -Infinity
    for (const exon of exons.value) {
      if (exon.end < d0 || exon.start > d1) continue
      const xs = scale(exon.start)
      const xe = scale(exon.end + 1)
      const w = Math.max(xe - xs, 5)
      const x = (xs + xe) / 2 - w / 2
      exonsGroup
        .append('rect')
        .attr('x', x)
        .attr('y', exonTop)
        .attr('width', w)
        .attr('height', EXON_H)
        .attr('rx', Math.min(2, w / 2))
        .attr('fill', colors.exon)
        .style('cursor', 'pointer')
        .on('mouseover', function (event) {
          if (isPinned.value) return
          select(this).attr('fill', colors.exonHover)
          showTooltip(event, exonTooltip(exon))
        })
        .on('mouseout', function () {
          select(this).attr('fill', colors.exon)
          hideTooltip()
        })

      // Exon number under the exon, skipped where it would collide with its neighbour
      const label = String(exon.transcript_order)
      const cx = x + w / 2
      const half = label.length * 3.2
      if (cx - half > lastLabelEnd + 3) {
        labelsGroup
          .append('text')
          .attr('x', cx)
          .attr('y', exonBottom + 11)
          .attr('text-anchor', 'middle')
          .style('font-size', '10px')
          .style('font-variant-numeric', 'tabular-nums')
          .style('fill', colors.muted)
          .text(label)
        lastLabelEnd = cx + half
      }
    }

    drawMarkers(scale)

    axisGroup.call(
      axisBottom(scale).ticks(tickCount(scale)).tickFormat(mbFormatter(scale)).tickSizeOuter(0)
    )
    axisGroup.selectAll('path, line').attr('stroke', colors.rule)
    axisGroup
      .selectAll('text')
      .style('font-size', '10px')
      .style('font-variant-numeric', 'tabular-nums')
      .attr('fill', colors.muted)
  }

  const drawMarkers = scale => {
    stemsGroup.selectAll('*').remove()
    markersGroup.selectAll('*').remove()

    const placed = markerGroups.value
      .map(m => ({ ...m, x: scale(m.pos) }))
      .filter(m => m.x >= -MARKER_R && m.x <= width + MARKER_R)
      .sort((a, b) => a.x - b.x)

    // Stack nearby markers: lowest level whose previous marker is at least MARKER_GAP away
    const lastX = Array(LEVELS).fill(-Infinity)
    for (const m of placed) {
      let level = lastX.findIndex(x => m.x - x >= MARKER_GAP)
      if (level < 0) level = lastX.indexOf(Math.min(...lastX))
      lastX[level] = m.x
      m.y = markerBase - STEM_BASE - level * STEM_STEP
    }

    // Draw the least severe first so pathogenic markers end up on top
    const ordered = [...placed].sort(
      (a, b) => severity(a.lead.category) - severity(b.lead.category) || a.x - b.x
    )
    for (const m of ordered) {
      stemsGroup
        .append('line')
        .attr('x1', m.x)
        .attr('x2', m.x)
        .attr('y1', markerBase)
        .attr('y2', m.y)
        .attr('stroke', colors.muted)
        .attr('stroke-opacity', 0.45)
        .attr('stroke-width', 1)
    }

    // Keyboard order follows the axis; one tab stop, arrow keys move between markers
    const byX = [...placed]
    ordered.forEach(m => {
      const { lead, variants } = m
      const count = variants.length
      const r = count > 1 ? MARKER_R + Math.min(Math.log2(count), 2.5) : MARKER_R
      const label = [
        lead.protein_change || lead.cdna_change || 'Variant',
        SIGNIFICANCE[lead.category]?.label ?? lead.classification ?? 'unclassified',
        EFFECTS[lead.effect_category]?.label ?? 'other effect',
        `chr${chromosome}:${m.pos.toLocaleString()}`,
        count > 1 ? `${count - 1} more at this position` : null
      ]
        .filter(Boolean)
        .join(', ')

      const node = markersGroup
        .append('path')
        .attr('class', `variant-marker${isSplice(lead) ? ' splice' : ''}`)
        .attr('d', shapePath(isSplice(lead), r))
        .attr('transform', `translate(${m.x},${m.y})`)
        .attr('fill', getVariantColor(lead))
        .attr('stroke', colors.background)
        .attr('stroke-width', 1)
        .attr('role', 'button')
        .attr('tabindex', m === byX[0] ? 0 : -1)
        .attr('aria-label', label)
        .attr('data-x', m.x)
        .style('cursor', 'pointer')
        .on(
          'mouseover',
          event => !isPinned.value && showTooltip(event, buildVariantTooltip(variants))
        )
        .on('mouseout', () => hideTooltip())
        .on('focus', function () {
          if (!isPinned.value) showTooltip(anchorOf(this), buildVariantTooltip(variants))
        })
        .on('blur', () => hideTooltip())
        .on('click', event => {
          event.stopPropagation()
          pinTooltip(event, buildVariantTooltip(variants, true))
        })
        .on('keydown', function (event) {
          const i = byX.indexOf(m)
          const next = { ArrowRight: i + 1, ArrowUp: i + 1, ArrowLeft: i - 1, ArrowDown: i - 1 }[
            event.key
          ]
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            event.stopPropagation()
            pinTooltip(anchorOf(this), buildVariantTooltip(variants, true))
          } else if (event.key === 'Escape') {
            unpinTooltip()
          } else if (next !== undefined && byX[next]) {
            event.preventDefault()
            unpinTooltip()
            this.setAttribute('tabindex', -1)
            const target = byX[next].node
            target.setAttribute('tabindex', 0)
            target.focus()
          }
        })
      m.node = node.node()
    })
  }

  draw(xScale)

  zoomBehavior = zoom()
    .scaleExtent([1, MAX_ZOOM])
    .translateExtent([
      [0, 0],
      [width, H]
    ])
    .extent([
      [0, 0],
      [width, H]
    ])
    .on('zoom', event => {
      currentTransform = event.transform
      zoomLevel.value = event.transform.k
      draw(event.transform.rescaleX(xScale))
    })

  // Double-click resets instead of zooming in (the buttons and wheel zoom in)
  svg.call(zoomBehavior).on('dblclick.zoom', null).on('dblclick', resetZoom)
  if (currentTransform !== zoomIdentity) svg.call(zoomBehavior.transform, currentTransform)
}

// Circle or (splice) diamond centred on 0,0; paths so both take the same focus styling
function shapePath(diamond, r) {
  if (diamond) {
    const d = r * 1.35
    return `M0,${-d}L${d},0L0,${d}L${-d},0Z`
  }
  return `M${-r},0a${r},${r} 0 1,0 ${2 * r},0a${r},${r} 0 1,0 ${-2 * r},0`
}

onMounted(() => {
  resizeObserver = new window.ResizeObserver(() => renderChart())
  resizeObserver.observe(chartContainer.value)
  nextTick(renderChart)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  removeTooltip()
  selectAll('.visualization-tooltip').remove()
})

// Re-render on data, filter, colour mode or theme changes
watch(
  () => [props.ensemblData, props.clinvarData],
  () => {
    currentTransform = zoomIdentity
    zoomLevel.value = 1
    nextTick(renderChart)
  },
  { deep: true }
)
watch([selectedClassifications, selectedEffects, colorBy, isDark], () => nextTick(renderChart), {
  deep: true
})
</script>

<style scoped>
.gene-structure-visualization {
  width: 100%;
  position: relative;
}

.chart-container {
  width: 100%;
  cursor: grab;
}

.chart-container:active {
  cursor: grabbing;
}

.chart-container :deep(.variant-marker:focus) {
  outline: none;
}

.chart-container :deep(.variant-marker:focus-visible) {
  stroke: var(--foreground);
  stroke-width: 2.5px;
}
</style>
