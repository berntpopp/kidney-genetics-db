<template>
  <div class="protein-domain-visualization">
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

    <!-- Visualization Container -->
    <div class="relative overflow-x-auto">
      <div
        ref="chartContainer"
        class="chart-container"
        :style="{ minWidth: `${MIN_PLOT_WIDTH}px` }"
      ></div>
      <div
        v-if="scanTip"
        class="pointer-events-none absolute z-10 rounded-md border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md tabular-nums"
        :style="{ left: `${scanTip.left}px`, top: `${scanTip.top}px` }"
        role="presentation"
      >
        <div v-for="(line, i) in scanTip.lines" :key="line" :class="i === 0 ? 'font-semibold' : ''">
          {{ line }}
        </div>
      </div>
    </div>
    <p class="mt-1 text-xs text-muted-foreground sm:hidden">
      Scroll sideways to see the whole plot.
    </p>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import { Download, ZoomIn, ZoomOut, SearchX } from 'lucide-vue-next'
import { useAppTheme } from '@/composables/useAppTheme'
import { Button } from '@/components/ui/button'
import { pointer, select, selectAll } from 'd3-selection'
import { scaleLinear } from 'd3-scale'
import { axisBottom } from 'd3-axis'
import { zoom, zoomIdentity } from 'd3-zoom'
import 'd3-transition'
import { useD3Tooltip } from '@/composables/useD3Tooltip'
import VariantFilters from '@/components/gene/VariantFilters.vue'
import {
  computedColor,
  effectColor,
  featureColor,
  significanceColor
} from '@/components/gene/variantColors'
import { formatP } from '@/utils/stats/sentences'

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
  uniprotData: {
    type: Object,
    required: true
  },
  clinvarData: {
    type: Object,
    default: null
  },
  height: {
    type: Number,
    default: 280
  },
  /** Linear hotspot scan (ScanResult) drawn as a track under the plot */
  scan: {
    type: Object,
    default: null
  },
  /** Reserve the scan track's height while the scan is computing (no layout shift) */
  scanPending: {
    type: Boolean,
    default: false
  }
})

// Scan track: fixed height below the main plot, present while pending or when results exist
const TRACK_GAP = 34
const TRACK_PLOT = 56
const TRACK_H = TRACK_GAP + TRACK_PLOT + 14
const showTrack = computed(() => Boolean(props.scan) || props.scanPending)
const scanTip = ref(null)

// Filter state
const colorBy = ref('classification')
const selectedClassifications = ref(['pathogenic', 'likely_pathogenic'])
const selectedEffects = ref(['truncating', 'missense', 'inframe', 'splice_region'])

// Zoom state
const zoomDomain = ref([0, 0]) // Current visible domain [start, end]
const zoomLevel = ref(1) // Current zoom level (1 = no zoom)
const isZoomed = computed(() => zoomLevel.value > 1.01)
const canZoomIn = computed(() => zoomLevel.value < 20)
const canZoomOut = computed(() => zoomLevel.value > 1.01)

// D3 zoom behavior reference
let zoomBehavior = null
let currentTransform = zoomIdentity

// Get all variants from ClinVar data
const allVariants = computed(() => {
  if (!props.clinvarData?.protein_variants) return []
  return props.clinvarData.protein_variants
})

// Check if we have variants to display
const hasVariants = computed(() => allVariants.value.length > 0)

const getVariantColor = variant => {
  return colorBy.value === 'classification'
    ? c(significanceColor(variant.category))
    : c(effectColor(variant.effect_category))
}

// Filter variants — both dimensions apply simultaneously (AND logic)
const filteredVariants = computed(() => {
  let variants = allVariants.value
  if (selectedClassifications.value.length > 0) {
    variants = variants.filter(v => selectedClassifications.value.includes(v.category))
  } else {
    return []
  }
  if (selectedEffects.value.length > 0) {
    variants = variants.filter(v => selectedEffects.value.includes(v.effect_category))
  }
  return variants
})

// Get domains from UniProt data
const domains = computed(() => {
  if (!props.uniprotData?.domains) return []
  return [...props.uniprotData.domains].sort((a, b) => a.start - b.start)
})

// Get color for effect
// Neutral backbone and text; only features and variants carry colour (variantColors.ts)
const palette = () => ({
  backbone: c('var(--border)'),
  text: c('var(--foreground)'),
  background: c('var(--background)')
})

// Plot is never narrower than this; a narrow screen scrolls it sideways instead of crushing it
const MIN_PLOT_WIDTH = 720

// Resolved token colours: SVG attributes must survive PNG export, so no var() in the plot
// Memoised per CSS string (a DOM style read per lollipop per zoom frame); cleared per render
const colorCache = new Map()
const c = css => {
  if (!colorCache.has(css)) colorCache.set(css, computedColor(css, chartContainer.value))
  return colorCache.get(css)
}
let colors = {}

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
    link.download = `${props.uniprotData?.accession || 'protein'}_domains.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
  }
  img.src = 'data:image/svg+xml;base64,' + window.btoa(unescape(encodeURIComponent(svgData)))
}

// Zoom control functions
const zoomIn = () => {
  if (!chartContainer.value || !zoomBehavior) return
  const svg = select(chartContainer.value).select('svg')
  svg.transition().duration(300).call(zoomBehavior.scaleBy, 1.5)
}

const zoomOut = () => {
  if (!chartContainer.value || !zoomBehavior) return
  const svg = select(chartContainer.value).select('svg')
  svg.transition().duration(300).call(zoomBehavior.scaleBy, 0.67)
}

const resetZoom = () => {
  if (!chartContainer.value || !zoomBehavior) return
  const svg = select(chartContainer.value).select('svg')
  svg.transition().duration(300).call(zoomBehavior.transform, zoomIdentity)
}

// Build variant tooltip content (for both hover and pinned)
const buildVariantTooltip = (variants, position, isPinned = false) => {
  const count = variants.length
  const firstVariant = variants[0]
  const color = c(significanceColor(firstVariant.category))

  let tooltipContent = `
    <div style="font-weight: 600; margin-bottom: 4px;">
      Position ${position}
    </div>
  `

  if (count > 1) {
    tooltipContent += `<div style="margin-bottom: 4px;"><strong>${count} variant${count > 1 ? 's' : ''} at this position</strong></div>`
  }

  // Show all variants if pinned, otherwise limit to 3
  const displayVariants = isPinned ? variants : variants.slice(0, 3)

  displayVariants.forEach(v => {
    const variantEffectColor = c(effectColor(v.effect_category))
    const clinvarId = v.accession ? v.accession.replace('VCV', '').replace(/^0+/, '') : ''

    tooltipContent += `
      <div style="border-top: 1px solid color-mix(in srgb, currentColor 15%, transparent); padding-top: 6px; margin-top: 6px;">
        <div style="font-weight: 600;">${v.protein_change || 'Unknown'}</div>
        ${v.cdna_change ? `<div style="font-size: 11px; opacity: 0.75;">${v.cdna_change}</div>` : ''}
        <div style="font-size: 11px; margin-top: 2px;">
          <span style="font-weight: 500;"><span style="display: inline-block; width: 8px; height: 8px; border-radius: 9999px; margin-right: 4px; background: ${color};"></span>${v.classification || 'Unknown'}</span>
          <span style="margin-left: 8px;"><span style="display: inline-block; width: 8px; height: 8px; border-radius: 9999px; margin-right: 4px; background: ${variantEffectColor};"></span>${v.effect_category || 'other'}</span>
        </div>
        <div style="font-size: 10px; opacity: 0.75; margin-top: 2px;">
          ${v.review_status || ''} ${clinvarId ? '•' : ''}
          ${clinvarId ? `<a href="https://www.ncbi.nlm.nih.gov/clinvar/variation/${clinvarId}/" target="_blank" rel="noopener noreferrer" style="color: inherit; text-decoration: underline;">${v.accession}</a>` : ''}
        </div>
      </div>
    `
  })

  if (!isPinned && count > 3) {
    tooltipContent += `<div style="font-size: 11px; opacity: 0.75; margin-top: 6px; font-style: italic;">Click to see all ${count} variants</div>`
  }

  return tooltipContent
}

const renderChart = () => {
  if (!chartContainer.value || !props.uniprotData) {
    return
  }

  // Close any pinned tooltip on re-render
  unpinTooltip()
  colorCache.clear()
  colors = palette()

  // Clear previous chart
  select(chartContainer.value).selectAll('*').remove()

  // Get container dimensions
  const containerWidth = chartContainer.value.clientWidth
  const containerHeight = props.height

  // Margins - extra top margin for lollipops
  const lollipopHeight = hasVariants.value && filteredVariants.value.length > 0 ? 60 : 0
  const margin = { top: 40 + lollipopHeight, right: 40, bottom: 50, left: 40 }
  const width = containerWidth - margin.left - margin.right
  const height = containerHeight - margin.top - margin.bottom

  // Validate dimensions
  if (width < 200 || height < 60) {
    select(chartContainer.value)
      .append('div')
      .style('display', 'flex')
      .style('align-items', 'center')
      .style('justify-content', 'center')
      .style('height', containerHeight + 'px')
      .style('color', 'var(--muted-foreground)')
      .text('Container too small')
    return
  }

  // Get protein length
  const proteinLength = props.uniprotData.length || 1

  // Initialize zoom domain if not set
  if (zoomDomain.value[0] === 0 && zoomDomain.value[1] === 0) {
    zoomDomain.value = [0, proteinLength]
  }

  // Create SVG
  const svgHeight = containerHeight + (showTrack.value ? TRACK_H : 0)
  const scanRegions = props.scan?.regions ?? []
  const svg = select(chartContainer.value)
    .append('svg')
    .attr('width', containerWidth)
    .attr('height', svgHeight)
    .attr('role', 'img')
    .attr(
      'aria-label',
      `Protein ${props.uniprotData?.accession ?? ''}: ${proteinLength} amino acids, ${domains.value.length} features, ${filteredVariants.value.length} ClinVar variants shown${props.scan ? `; hotspot scan: ${scanRegions.length} significant region${scanRegions.length === 1 ? '' : 's'}` : ''}`
    )

  // Create clip path for zoom
  svg
    .append('defs')
    .append('clipPath')
    .attr('id', 'protein-clip')
    .append('rect')
    .attr('x', 0)
    .attr('y', -lollipopHeight - 20)
    .attr('width', width)
    .attr('height', height + lollipopHeight + 40)

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

  // Create main content group with clip path
  const contentGroup = g.append('g').attr('clip-path', 'url(#protein-clip)')

  // Create scales
  const xScale = scaleLinear().domain([0, proteinLength]).range([0, width])

  // Create a zoom scale that can be transformed
  let xScaleZoomed = xScale.copy()

  // Draw title
  svg
    .append('text')
    .attr('x', containerWidth / 2)
    .attr('y', 20)
    .attr('text-anchor', 'middle')
    .style('font-size', '14px')
    .style('font-weight', '600')
    .style('fill', colors.text)
    .text(`${props.uniprotData.protein_name || props.uniprotData.accession} (${proteinLength} aa)`)

  // Hotspot region bands, behind the backbone, domains and lollipops
  const bandsGroup = contentGroup.append('g').attr('class', 'scan-bands')

  // Draw protein backbone
  const backboneY = height / 2
  const backboneHeight = 8

  contentGroup
    .append('rect')
    .attr('class', 'backbone')
    .attr('x', 0)
    .attr('y', backboneY - backboneHeight / 2)
    .attr('width', width)
    .attr('height', backboneHeight)
    .attr('fill', colors.backbone)
    .attr('rx', 4)

  // Draw domains
  const domainHeight = 30
  const domainsGroup = contentGroup.append('g').attr('class', 'domains-group')

  const drawDomains = scale => {
    domainsGroup.selectAll('*').remove()

    domains.value.forEach(domain => {
      const x = scale(domain.start)
      const domainWidth = Math.max(scale(domain.end) - scale(domain.start), 4)
      const color = c(featureColor(domain.type))

      // Skip if outside visible area
      if (x + domainWidth < 0 || x > width) return

      // Domain rectangle
      const domainRect = domainsGroup
        .append('rect')
        .attr('x', x)
        .attr('y', backboneY - domainHeight / 2)
        .attr('width', domainWidth)
        .attr('height', domainHeight)
        .attr('fill', color)
        .attr('rx', 4)
        .attr('stroke', colors.text)
        .attr('stroke-opacity', 0.25)
        .attr('stroke-width', 1)
        .style('cursor', 'pointer')

      // Hover effects
      domainRect
        .on('mouseover', function (event) {
          if (isPinned.value) return

          select(this)
            .transition()
            .duration(150)
            .attr('fill-opacity', 0.8)
            .attr('y', backboneY - domainHeight / 2 - 3)
            .attr('height', domainHeight + 6)

          // Build Pfam link if available
          let pfamLink = ''
          if (domain.type === 'Domain' && props.uniprotData.pfam_refs) {
            const pfam = props.uniprotData.pfam_refs.find(
              p => domain.description && p.entry_name && domain.description.includes(p.entry_name)
            )
            if (pfam) {
              pfamLink = `<div style="margin-top: 4px;">
                <a href="https://www.ebi.ac.uk/interpro/entry/pfam/${pfam.id}" target="_blank" rel="noopener noreferrer" style="color: inherit; text-decoration: underline;">
                  View in Pfam (${pfam.id})
                </a>
              </div>`
            }
          }

          showTooltip(
            event,
            `
            <div style="font-weight: 600; margin-bottom: 4px;">
              ${domain.type}
            </div>
            <div><strong>Description:</strong> ${domain.description || 'N/A'}</div>
            <div><strong>Position:</strong> ${domain.start} - ${domain.end}</div>
            <div><strong>Length:</strong> ${domain.length} aa</div>
            ${pfamLink}
          `
          )
        })
        .on('mouseout', function () {
          select(this)
            .transition()
            .duration(150)
            .attr('fill', color)
            .attr('y', backboneY - domainHeight / 2)
            .attr('height', domainHeight)

          hideTooltip()
        })
    })
  }

  // Draw lollipops for ClinVar variants
  const lollipopGroup = contentGroup.append('g').attr('class', 'lollipop-group')
  const lollipopBaseY = backboneY - domainHeight / 2 - 5
  const lollipopRadius = 4
  const lollipopStalkHeight = 40

  const drawLollipops = scale => {
    lollipopGroup.selectAll('*').remove()

    if (!hasVariants.value || filteredVariants.value.length === 0) return

    // Group variants by position to handle overlaps
    const variantsByPosition = {}
    filteredVariants.value.forEach(variant => {
      const pos = variant.position
      if (!variantsByPosition[pos]) {
        variantsByPosition[pos] = []
      }
      variantsByPosition[pos].push(variant)
    })

    // Draw each lollipop
    Object.entries(variantsByPosition).forEach(([position, variants]) => {
      const x = scale(parseInt(position))

      // Skip if outside visible area
      if (x < -10 || x > width + 10) return

      const variant = variants[0]
      const color = getVariantColor(variant)
      const count = variants.length

      // Stalk line
      lollipopGroup
        .append('line')
        .attr('x1', x)
        .attr('y1', lollipopBaseY)
        .attr('x2', x)
        .attr('y2', lollipopBaseY - lollipopStalkHeight)
        .attr('stroke', color)
        .attr('stroke-width', 1.5)
        .attr('stroke-opacity', 0.7)

      // Lollipop head (larger if multiple variants)
      const radius = count > 1 ? lollipopRadius + Math.min(Math.log2(count) * 2, 5) : lollipopRadius

      const lollipopHead = lollipopGroup
        .append('circle')
        .attr('cx', x)
        .attr('cy', lollipopBaseY - lollipopStalkHeight - radius)
        .attr('r', radius)
        .attr('fill', color)
        .attr('stroke', colors.background)
        .attr('stroke-width', 1)
        .style('cursor', 'pointer')

      // Hover effects for lollipop
      lollipopHead
        .on('mouseover', function (event) {
          if (isPinned.value) return

          select(this)
            .transition()
            .duration(150)
            .attr('r', radius + 2)
            .attr('stroke-width', 2)

          showTooltip(event, buildVariantTooltip(variants, position, false))
        })
        .on('mouseout', function () {
          select(this).transition().duration(150).attr('r', radius).attr('stroke-width', 1)

          hideTooltip()
        })
        .on('click', function (event) {
          event.stopPropagation()

          select(this)
            .transition()
            .duration(150)
            .attr('r', radius + 3)
            .attr('stroke-width', 2)

          // Pin tooltip with full variant list
          pinTooltip(event, buildVariantTooltip(variants, position, true))
        })
    })
  }

  // Draw axis at bottom
  const axisY = height + 5
  const xAxis = axisBottom(xScale)
    .ticks(Math.min(10, Math.floor(width / 80)))
    .tickFormat(d => d)

  const axisGroup = g
    .append('g')
    .attr('class', 'x-axis')
    .attr('transform', `translate(0, ${axisY})`)
    .call(xAxis)

  axisGroup.selectAll('text').style('font-size', '10px').style('fill', colors.text)

  axisGroup.selectAll('.domain, line').style('stroke', colors.text).style('opacity', 0.5)

  // Axis label
  svg
    .append('text')
    .attr('x', containerWidth / 2)
    .attr('y', containerHeight - 5)
    .attr('text-anchor', 'middle')
    .style('font-size', '10px')
    .style('fill', colors.text)
    .style('opacity', 0.7)
    .text('Amino acid position')

  // Draw domain legend
  const uniqueTypes = [...new Set(domains.value.map(d => d.type))]
  if (uniqueTypes.length > 0) {
    const legendY = -15 - lollipopHeight
    const legendItemWidth = 90
    const legendX = (width - uniqueTypes.length * legendItemWidth) / 2

    uniqueTypes.forEach((type, i) => {
      const x = legendX + i * legendItemWidth

      // Color box
      g.append('rect')
        .attr('x', x)
        .attr('y', legendY)
        .attr('width', 12)
        .attr('height', 12)
        .attr('fill', c(featureColor(type)))
        .attr('rx', 2)

      // Label
      g.append('text')
        .attr('x', x + 16)
        .attr('y', legendY + 10)
        .style('font-size', '10px')
        .style('fill', colors.text)
        .text(type)
    })
  }

  // Hotspot scan track (shares the zoomed x scale) and region bands through the plot
  const meaning = c(significanceColor('pathogenic'))
  const muted = c('var(--muted-foreground)')
  const bandTop = backboneY - domainHeight / 2 - lollipopHeight - 14
  const bandBottom = backboneY + domainHeight / 2 + 6
  const band = (group, scale, r, y, h) =>
    group
      .append('rect')
      .attr('x', scale(r.start - 0.5))
      .attr('y', y)
      .attr('width', Math.max(scale(r.end + 0.5) - scale(r.start - 0.5), 2))
      .attr('height', h)
      .attr('fill', meaning)
      .attr('fill-opacity', 0.08)
  const drawBands = scale => {
    bandsGroup.selectAll('*').remove()
    scanRegions.forEach(r => band(bandsGroup, scale, r, bandTop, bandBottom - bandTop))
  }
  let drawScan = () => {}
  if (showTrack.value) {
    const trackTop = containerHeight + TRACK_GAP
    const track = svg.append('g').attr('transform', `translate(${margin.left},${trackTop})`)
    svg
      .append('text')
      .attr('x', margin.left)
      .attr('y', trackTop - 12)
      .style('font-size', '11px')
      .style('font-weight', '600')
      .style('fill', colors.text)
      .text('Hotspot scan')
      .append('tspan')
      .attr('dx', 8)
      .style('font-weight', '400')
      .style('fill', muted)
      .text(`−log₁₀ family-wise adjusted p, ${props.scan?.w ?? 15}-residue windows`)
    const B = props.scan?.B ?? 10000
    const yCap = Math.log10(B + 1)
    const yScale = scaleLinear().domain([0, yCap]).range([TRACK_PLOT, 0])
    const fwer = yScale(-Math.log10(0.05))
    ;[0, Math.floor(yCap)].forEach(t =>
      track
        .append('text')
        .attr('x', -6)
        .attr('y', yScale(t) + 3)
        .attr('text-anchor', 'end')
        .style('font-size', '10px')
        .style('font-variant-numeric', 'tabular-nums')
        .style('fill', muted)
        .text(t)
    )
    track
      .append('line')
      .attr('x1', 0)
      .attr('x2', width)
      .attr('y1', TRACK_PLOT)
      .attr('y2', TRACK_PLOT)
      .attr('stroke', colors.backbone)
    track
      .append('line')
      .attr('x1', 0)
      .attr('x2', width)
      .attr('y1', fwer)
      .attr('y2', fwer)
      .attr('stroke', muted)
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.6)
    track
      .append('text')
      .attr('x', width)
      .attr('y', fwer - 4)
      .attr('text-anchor', 'end')
      .style('font-size', '10px')
      .style('fill', muted)
      .text('FWER 0.05')
    if (!props.scan) {
      track
        .append('text')
        .attr('x', width / 2)
        .attr('y', TRACK_PLOT / 2 + 4)
        .attr('text-anchor', 'middle')
        .style('font-size', '11px')
        .style('fill', muted)
        .text('Computing hotspot scan…')
    } else {
      svg
        .select('defs')
        .append('clipPath')
        .attr('id', 'protein-scan-clip')
        .append('rect')
        .attr('x', 0)
        .attr('y', -2)
        .attr('width', width)
        .attr('height', TRACK_PLOT + 4)
      const trackContent = track.append('g').attr('clip-path', 'url(#protein-scan-clip)')
      const windows = props.scan.windows
      const yOf = w => yScale(Math.min(yCap, -Math.log10(w.adjP)))
      const crosshair = track
        .append('line')
        .attr('y1', 0)
        .attr('y2', TRACK_PLOT)
        .attr('stroke', colors.text)
        .attr('stroke-opacity', 0.5)
        .style('display', 'none')
      drawScan = scale => {
        trackContent.selectAll('*').remove()
        scanRegions.forEach(r => band(trackContent, scale, r, 0, TRACK_PLOT))
        if (!windows.length) return
        const pts = windows.map(w => `${scale(w.centre).toFixed(1)},${yOf(w).toFixed(1)}`)
        const x0 = scale(windows[0].centre).toFixed(1)
        const x1 = scale(windows[windows.length - 1].centre).toFixed(1)
        trackContent
          .append('path')
          .attr('d', `M${x0},${TRACK_PLOT}L${pts.join('L')}L${x1},${TRACK_PLOT}Z`)
          .attr('fill', meaning)
          .attr('fill-opacity', 0.1)
        trackContent
          .append('path')
          .attr('d', `M${pts.join('L')}`)
          .attr('fill', 'none')
          .attr('stroke', meaning)
          .attr('stroke-width', 2)
          .attr('stroke-linejoin', 'round')
      }
      track
        .append('rect')
        .attr('width', width)
        .attr('height', TRACK_PLOT)
        .attr('fill', 'transparent')
        .on('mousemove', event => {
          if (!windows.length) return
          const [mx] = pointer(event, track.node())
          const residue = xScaleZoomed.invert(mx)
          const i = Math.min(
            windows.length - 1,
            Math.max(0, Math.round(residue - windows[0].centre))
          )
          const w = windows[i]
          const x = xScaleZoomed(w.centre)
          crosshair.attr('x1', x).attr('x2', x).style('display', null)
          const left = margin.left + x
          scanTip.value = {
            left: left > containerWidth - 200 ? left - 190 : left + 12,
            top: trackTop + 4,
            lines: [
              `Residues ${w.start}–${w.end}`,
              `${w.cases} P/LP · ${w.ctrls} gnomAD`,
              `Adjusted p ${formatP(w.adjP, B)}`
            ]
          }
        })
        .on('mouseleave', () => {
          crosshair.style('display', 'none')
          scanTip.value = null
        })
    }
  }

  // Initial draw
  drawBands(xScaleZoomed)
  drawScan(xScaleZoomed)
  drawDomains(xScaleZoomed)
  drawLollipops(xScaleZoomed)

  // Setup zoom behavior
  zoomBehavior = zoom()
    .scaleExtent([1, 20])
    .translateExtent([
      [0, 0],
      [width, height]
    ])
    .extent([
      [0, 0],
      [width, height]
    ])
    .on('zoom', event => {
      currentTransform = event.transform
      xScaleZoomed = event.transform.rescaleX(xScale)

      // Update zoom state
      zoomLevel.value = event.transform.k
      zoomDomain.value = xScaleZoomed.domain()

      // Redraw with new scale
      drawBands(xScaleZoomed)
      drawScan(xScaleZoomed)
      scanTip.value = null
      drawDomains(xScaleZoomed)
      drawLollipops(xScaleZoomed)

      // Update axis
      axisGroup.call(axisBottom(xScaleZoomed).ticks(Math.min(10, Math.floor(width / 80))))
      axisGroup.selectAll('text').style('font-size', '10px').style('fill', colors.text)
      axisGroup.selectAll('.domain, line').style('stroke', colors.text).style('opacity', 0.5)

      // Update backbone width
      contentGroup
        .select('.backbone')
        .attr('x', xScaleZoomed(0))
        .attr('width', xScaleZoomed(proteinLength) - xScaleZoomed(0))
    })

  // Apply zoom to SVG
  svg.call(zoomBehavior)

  // Apply existing transform if any
  if (currentTransform !== zoomIdentity) {
    svg.call(zoomBehavior.transform, currentTransform)
  }
}

// Setup resize observer
onMounted(() => {
  resizeObserver = new window.ResizeObserver(() => {
    renderChart()
  })
  resizeObserver.observe(chartContainer.value)

  nextTick(renderChart)
})

// Cleanup
onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  removeTooltip()
  // Remove any orphaned tooltips
  selectAll('.visualization-tooltip').remove()
})

// Re-render on data changes
watch(
  () => props.uniprotData,
  () => nextTick(renderChart),
  { deep: true }
)

watch(
  () => props.clinvarData,
  () => nextTick(renderChart),
  { deep: true }
)

// Re-render on filter changes
watch(
  () => [selectedClassifications.value, selectedEffects.value],
  () => nextTick(renderChart),
  { deep: true }
)

watch(
  () => colorBy.value,
  () => nextTick(renderChart)
)

watch(
  () => [props.scan, props.scanPending],
  () => nextTick(renderChart)
)

watch(
  () => isDark.value,
  () => nextTick(renderChart)
)
</script>

<style scoped>
.protein-domain-visualization {
  width: 100%;
  position: relative;
}

.chart-container {
  width: 100%;
  min-height: 280px;
  cursor: grab;
}

.chart-container:active {
  cursor: grabbing;
}
</style>
