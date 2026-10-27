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

    <!-- Visualization Container -->
    <div class="overflow-x-auto">
      <div
        ref="chartContainer"
        class="chart-container"
        :style="{ minWidth: `${MIN_PLOT_WIDTH}px` }"
      ></div>
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
import { select, selectAll } from 'd3-selection'
import { scaleLinear } from 'd3-scale'
import { zoom, zoomIdentity } from 'd3-zoom'
import 'd3-transition'
import { useD3Tooltip } from '@/composables/useD3Tooltip'
import VariantFilters from '@/components/gene/VariantFilters.vue'
import { computedColor, effectColor, significanceColor } from '@/components/gene/variantColors'

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
  },
  height: {
    type: Number,
    default: 280
  }
})

// Filter state
const colorBy = ref('classification') // 'classification' or 'effect'
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

// Get all variants from ClinVar data - use genomic_variants for gene structure view
// This includes ALL variants with genomic positions (including splice variants)
const allVariants = computed(() => {
  if (!props.clinvarData?.genomic_variants) return []
  return props.clinvarData.genomic_variants
})

// Check if we have variants to display
const hasVariants = computed(() => allVariants.value.length > 0)

// Get lollipop color for a variant based on current colorBy mode
const getVariantColor = variant => {
  return colorBy.value === 'classification'
    ? c(significanceColor(variant.category))
    : c(effectColor(variant.effect_category))
}

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

// Get exons from canonical transcript
// Sort by transcript order (5'→3'), not genomic position
const exons = computed(() => {
  const transcript = props.ensemblData?.canonical_transcript
  if (!transcript?.exons) return []

  const strand = props.ensemblData.strand

  // Sort exons by genomic position first
  const sortedByPosition = [...transcript.exons].sort((a, b) => a.start - b.start)

  // For negative strand, exons should be numbered in reverse
  // The first exon in transcript order is the one with highest genomic position
  if (strand === '-') {
    // Assign transcript order number (1 = first exon in 5'→3' direction)
    return sortedByPosition.map((exon, idx) => ({
      ...exon,
      transcript_order: sortedByPosition.length - idx
    }))
  } else {
    // For positive strand, genomic order = transcript order
    return sortedByPosition.map((exon, idx) => ({
      ...exon,
      transcript_order: idx + 1
    }))
  }
})

// Get variants with genomic positions (use actual positions from ClinVar API)
// No mapping needed - we use the real genomic coordinates from the variant data
const variantsWithGenomicPos = computed(() => {
  return filteredVariants.value
    .filter(v => v.genomic_start !== null && v.genomic_start !== undefined)
    .map(variant => ({
      ...variant,
      genomicPosition: variant.genomic_start
    }))
})

// Neutral structure colours; only variants carry meaning (variantColors.ts)
const palette = () => ({
  exon: c('var(--muted-foreground)'),
  exonHover: c('var(--foreground)'),
  exonLabel: c('var(--background)'),
  intron: c('var(--border)'),
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
    link.download = `${props.geneSymbol}_structure.png`
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
const buildVariantTooltip = (variants, isPinned = false) => {
  const count = variants.length
  const firstVariant = variants[0]
  const color = c(significanceColor(firstVariant.category))

  let tooltipContent = `
    <div style="font-weight: 600; margin-bottom: 4px;">
      ${count} variant${count > 1 ? 's' : ''} in this region
    </div>
  `

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
  if (!chartContainer.value || exons.value.length === 0) {
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
  const lollipopHeight = hasVariants.value && variantsWithGenomicPos.value.length > 0 ? 60 : 0
  const margin = { top: 40 + lollipopHeight, right: 50, bottom: 40, left: 40 }
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

  // Get gene coordinates
  const geneStart = props.ensemblData.start
  const geneEnd = props.ensemblData.end
  const strand = props.ensemblData.strand

  // Initialize zoom domain if not set
  if (zoomDomain.value[0] === 0 && zoomDomain.value[1] === 0) {
    zoomDomain.value = [geneStart, geneEnd]
  }

  // Create SVG
  const svg = select(chartContainer.value)
    .append('svg')
    .attr('width', containerWidth)
    .attr('height', containerHeight)
    .attr('role', 'img')
    .attr(
      'aria-label',
      `${props.geneSymbol} gene structure: ${exons.value.length} exons on the ${strand} strand, ${variantsWithGenomicPos.value.length} ClinVar variants shown`
    )

  // Create clip path for zoom
  svg
    .append('defs')
    .append('clipPath')
    .attr('id', 'gene-clip')
    .append('rect')
    .attr('x', 0)
    .attr('y', -lollipopHeight - 20)
    .attr('width', width)
    .attr('height', height + lollipopHeight + 40)

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

  // Create main content group with clip path
  const contentGroup = g.append('g').attr('clip-path', 'url(#gene-clip)')

  // Create scale
  const xScale = scaleLinear().domain([geneStart, geneEnd]).range([0, width])

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
    .text(
      `${props.geneSymbol} - ${props.ensemblData.canonical_transcript?.transcript_id || 'Canonical Transcript'} (${strand} strand)`
    )

  // Draw gene backbone (intron line)
  const backboneY = height / 2
  const backboneHeight = 4

  contentGroup
    .append('rect')
    .attr('class', 'backbone')
    .attr('x', 0)
    .attr('y', backboneY - backboneHeight / 2)
    .attr('width', width)
    .attr('height', backboneHeight)
    .attr('fill', colors.intron)
    .attr('rx', 2)

  // Draw strand direction arrow (outside clip)
  // U+FE0E keeps the arrow a text glyph, not a colour emoji
  const strandSymbol = strand === '+' ? '\u25B6\uFE0E' : '\u25C0\uFE0E'
  g.append('text')
    .attr('class', 'strand-arrow')
    .attr('x', strand === '+' ? width + 10 : -10)
    .attr('y', backboneY + 5)
    .attr('text-anchor', strand === '+' ? 'start' : 'end')
    .style('font-size', '16px')
    .style('fill', colors.text)
    .text(strandSymbol)

  // Draw exons
  const exonHeight = 40
  const exonsGroup = contentGroup.append('g').attr('class', 'exons-group')
  const exonLabelsGroup = contentGroup.append('g').attr('class', 'exon-labels-group')

  const drawExons = scale => {
    exonsGroup.selectAll('*').remove()
    exonLabelsGroup.selectAll('*').remove()

    exons.value.forEach(exon => {
      const x = scale(exon.start)
      const exonWidth = Math.max(scale(exon.end) - scale(exon.start), 2)

      // Skip if outside visible area
      if (x + exonWidth < 0 || x > width) return

      // Exon rectangle
      const exonRect = exonsGroup
        .append('rect')
        .attr('x', x)
        .attr('y', backboneY - exonHeight / 2)
        .attr('width', exonWidth)
        .attr('height', exonHeight)
        .attr('fill', colors.exon)
        .attr('rx', 3)
        .attr('stroke', colors.background)
        .attr('stroke-width', 1)
        .style('cursor', 'pointer')

      // Hover effects
      exonRect
        .on('mouseover', function (event) {
          if (isPinned.value) return

          select(this)
            .transition()
            .duration(150)
            .attr('fill', colors.exonHover)
            .attr('y', backboneY - exonHeight / 2 - 2)
            .attr('height', exonHeight + 4)

          showTooltip(
            event,
            `
            <div style="font-weight: 600; margin-bottom: 4px;">
              Exon ${exon.transcript_order} (of ${exons.value.length})
            </div>
            <div><strong>ID:</strong> ${exon.exon_id}</div>
            <div><strong>Genomic:</strong> ${exon.start?.toLocaleString()} - ${exon.end?.toLocaleString()}</div>
            <div><strong>Length:</strong> ${exon.length?.toLocaleString()} bp</div>
            <div style="font-size: 10px; opacity: 0.75; margin-top: 4px;">
              Transcript order: 5' to 3'
            </div>
          `
          )
        })
        .on('mouseout', function () {
          select(this)
            .transition()
            .duration(150)
            .attr('fill', colors.exon)
            .attr('y', backboneY - exonHeight / 2)
            .attr('height', exonHeight)

          hideTooltip()
        })

      // Exon number label (use transcript order, only if wide enough)
      if (exonWidth > 24) {
        exonLabelsGroup
          .append('text')
          .attr('x', x + exonWidth / 2)
          .attr('y', backboneY + 4)
          .attr('text-anchor', 'middle')
          .style('font-size', '12px')
          .style('fill', colors.exonLabel)
          .style('pointer-events', 'none')
          .text(exon.transcript_order)
      }
    })
  }

  // Draw lollipops for ClinVar variants
  const lollipopGroup = contentGroup.append('g').attr('class', 'lollipop-group')
  const lollipopBaseY = backboneY - exonHeight / 2 - 5
  const lollipopRadius = 4
  const lollipopStalkHeight = 40

  const drawLollipops = scale => {
    lollipopGroup.selectAll('*').remove()

    if (!hasVariants.value || variantsWithGenomicPos.value.length === 0) return

    // Group variants by exact genomic position (only truly overlapping variants are grouped)
    const variantsByPosition = {}
    variantsWithGenomicPos.value.forEach(variant => {
      // Use exact genomic position - no rounding
      const pos = variant.genomicPosition
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
      const radius = count > 1 ? lollipopRadius + Math.min(Math.log2(count) * 2, 6) : lollipopRadius

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

          showTooltip(event, buildVariantTooltip(variants, false))
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
          pinTooltip(event, buildVariantTooltip(variants, true))
        })
    })
  }

  // Draw scale bar at bottom (outside clip)
  const geneLengthKb = Math.round((geneEnd - geneStart) / 1000)
  const scaleBarY = height + 10
  const scaleBarLength = Math.min(width / 4, 100)
  const scaleBarValue = Math.round(((scaleBarLength / width) * (geneEnd - geneStart)) / 1000)

  const scaleBarGroup = g.append('g').attr('class', 'scale-bar')

  scaleBarGroup
    .append('line')
    .attr('x1', 0)
    .attr('y1', scaleBarY)
    .attr('x2', scaleBarLength)
    .attr('y2', scaleBarY)
    .attr('stroke', colors.text)
    .attr('stroke-width', 2)

  scaleBarGroup
    .append('text')
    .attr('x', scaleBarLength / 2)
    .attr('y', scaleBarY + 16)
    .attr('text-anchor', 'middle')
    .style('font-size', '12px')
    .style('fill', colors.text)
    .text(`${scaleBarValue} kb`)

  // Chromosome location label
  svg
    .append('text')
    .attr('x', containerWidth - margin.right)
    .attr('y', containerHeight - 10)
    .attr('text-anchor', 'end')
    .style('font-size', '12px')
    .style('fill', colors.text)
    .text(
      `chr${props.ensemblData.chromosome}:${geneStart?.toLocaleString()}-${geneEnd?.toLocaleString()} (${geneLengthKb} kb)`
    )

  // Initial draw
  drawExons(xScaleZoomed)
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
      drawExons(xScaleZoomed)
      drawLollipops(xScaleZoomed)

      // Update backbone width
      contentGroup
        .select('.backbone')
        .attr('x', xScaleZoomed(geneStart))
        .attr('width', xScaleZoomed(geneEnd) - xScaleZoomed(geneStart))
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
  selectAll('.visualization-tooltip').remove()
})

// Re-render on data changes
watch(
  () => props.ensemblData,
  () => nextTick(renderChart),
  { deep: true }
)

watch(
  () => props.clinvarData,
  () => nextTick(renderChart),
  { deep: true }
)

watch(
  () => props.uniprotData,
  () => nextTick(renderChart),
  { deep: true }
)

// Re-render on filter or color mode changes
watch(
  () => selectedClassifications.value,
  () => nextTick(renderChart),
  { deep: true }
)

watch(
  () => selectedEffects.value,
  () => nextTick(renderChart),
  { deep: true }
)

watch(
  () => colorBy.value,
  () => nextTick(renderChart)
)

watch(
  () => isDark.value,
  () => nextTick(renderChart)
)
</script>

<style scoped>
.gene-structure-visualization {
  width: 100%;
  position: relative;
}

.chart-container {
  width: 100%;
  min-height: 200px;
  cursor: grab;
}

.chart-container:active {
  cursor: grabbing;
}
</style>
