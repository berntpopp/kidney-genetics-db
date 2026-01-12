<template>
  <div class="protein-domain-visualization">
    <!-- Filter Controls -->
    <div v-if="hasVariants" class="filter-controls mb-4">
      <!-- Classification Filter -->
      <div class="filter-group mb-2">
        <span class="filter-label text-caption text-medium-emphasis mr-2">Classification:</span>
        <v-chip-group
          v-model="selectedClassifications"
          multiple
          selected-class="bg-primary"
          class="d-inline-flex"
        >
          <v-chip
            v-for="cat in classificationOptions"
            :key="cat.value"
            :value="cat.value"
            size="small"
            variant="outlined"
            :color="getClassificationColor(cat.value)"
            filter
          >
            {{ cat.label }} ({{ getClassificationCount(cat.value) }})
          </v-chip>
        </v-chip-group>
      </div>

      <!-- Effect Filter -->
      <div class="filter-group">
        <span class="filter-label text-caption text-medium-emphasis mr-2">Effect:</span>
        <v-chip-group
          v-model="selectedEffects"
          multiple
          selected-class="bg-secondary"
          class="d-inline-flex"
        >
          <v-chip
            v-for="eff in effectOptions"
            :key="eff.value"
            :value="eff.value"
            size="small"
            variant="outlined"
            :color="getEffectColor(eff.value)"
            filter
          >
            {{ eff.label }} ({{ getEffectCount(eff.value) }})
          </v-chip>
        </v-chip-group>
      </div>

      <!-- Variant count summary -->
      <div class="text-caption text-medium-emphasis mt-2">
        Showing {{ filteredVariants.length }} of {{ allVariants.length }} variants with protein
        positions
      </div>
    </div>

    <!-- Zoom Controls -->
    <div class="zoom-controls mb-2">
      <v-btn-group density="compact" variant="outlined" divided>
        <v-btn size="small" :disabled="!canZoomIn" @click="zoomIn">
          <v-icon icon="mdi-magnify-plus-outline" size="small" />
        </v-btn>
        <v-btn size="small" :disabled="!canZoomOut" @click="zoomOut">
          <v-icon icon="mdi-magnify-minus-outline" size="small" />
        </v-btn>
        <v-btn size="small" :disabled="!isZoomed" @click="resetZoom">
          <v-icon icon="mdi-magnify-remove-outline" size="small" class="mr-1" />
          Reset
        </v-btn>
      </v-btn-group>
      <span v-if="isZoomed" class="text-caption text-medium-emphasis ml-2">
        Viewing: {{ Math.round(zoomDomain[0]) }} - {{ Math.round(zoomDomain[1]) }} aa ({{
          Math.round(zoomLevel * 100)
        }}% zoom)
      </span>
      <span class="text-caption text-medium-emphasis ml-2">
        <v-icon icon="mdi-gesture-swipe-horizontal" size="x-small" class="mr-1" />
        Drag to pan, scroll to zoom
      </span>
    </div>

    <!-- Visualization Container -->
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import { useTheme } from 'vuetify'
import * as d3 from 'd3'
import { useD3Tooltip } from '@/composables/useD3Tooltip'

const theme = useTheme()
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
  }
})

// Filter state
const selectedClassifications = ref(['pathogenic', 'likely_pathogenic'])
const selectedEffects = ref([])

// Zoom state
const zoomDomain = ref([0, 0]) // Current visible domain [start, end]
const zoomLevel = ref(1) // Current zoom level (1 = no zoom)
const isZoomed = computed(() => zoomLevel.value > 1.01)
const canZoomIn = computed(() => zoomLevel.value < 20)
const canZoomOut = computed(() => zoomLevel.value > 1.01)

// D3 zoom behavior reference
let zoomBehavior = null
let currentTransform = d3.zoomIdentity

// Classification options for filter
const classificationOptions = [
  { value: 'pathogenic', label: 'Pathogenic' },
  { value: 'likely_pathogenic', label: 'Likely Path.' },
  { value: 'vus', label: 'VUS' },
  { value: 'conflicting', label: 'Conflicting' },
  { value: 'likely_benign', label: 'Likely Ben.' },
  { value: 'benign', label: 'Benign' }
]

// Effect options for filter
const effectOptions = [
  { value: 'truncating', label: 'Truncating' },
  { value: 'missense', label: 'Missense' },
  { value: 'inframe', label: 'Inframe' },
  { value: 'splice_region', label: 'Splice' },
  { value: 'synonymous', label: 'Synonymous' },
  { value: 'other', label: 'Other' }
]

// Get all variants from ClinVar data
const allVariants = computed(() => {
  if (!props.clinvarData?.protein_variants) return []
  return props.clinvarData.protein_variants
})

// Check if we have variants to display
const hasVariants = computed(() => allVariants.value.length > 0)

// Get count by classification
const getClassificationCount = category => {
  return allVariants.value.filter(v => v.category === category).length
}

// Get count by effect
const getEffectCount = effect => {
  return allVariants.value.filter(v => v.effect_category === effect).length
}

// Filter variants based on selected filters
const filteredVariants = computed(() => {
  let variants = allVariants.value

  // Filter by classification (if any selected)
  if (selectedClassifications.value.length > 0) {
    variants = variants.filter(v => selectedClassifications.value.includes(v.category))
  }

  // Filter by effect (if any selected)
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

// Color scale for different domain types
const domainColors = {
  Domain: '#7B1FA2', // Purple
  Region: '#00796B', // Teal
  Motif: '#F57C00', // Orange
  Transmembrane: '#C62828', // Red
  Signal: '#1565C0', // Blue
  Propeptide: '#558B2F', // Green
  Chain: '#455A64' // Blue Grey
}

// Colors for clinical classifications
const classificationColors = {
  pathogenic: '#D32F2F', // Red
  likely_pathogenic: '#F57C00', // Orange
  vus: '#FBC02D', // Yellow
  conflicting: '#7B1FA2', // Purple
  likely_benign: '#0288D1', // Light Blue
  benign: '#388E3C', // Green
  other: '#757575' // Grey
}

// Colors for effect categories
const effectColors = {
  truncating: '#B71C1C', // Dark Red
  missense: '#E65100', // Dark Orange
  inframe: '#F9A825', // Amber
  splice_region: '#6A1B9A', // Purple
  synonymous: '#2E7D32', // Green
  other: '#757575' // Grey
}

// Get color for classification
const getClassificationColor = category => {
  return classificationColors[category] || '#757575'
}

// Get color for effect
const getEffectColor = effect => {
  return effectColors[effect] || '#757575'
}

// Get color for domain type
const getDomainColor = type => {
  return domainColors[type] || '#757575'
}

// Colors for visualization
const colors = computed(() => ({
  backbone: theme.global.current.value.dark ? '#616161' : '#E0E0E0',
  text: theme.global.current.value.dark ? '#FFFFFF' : '#333333'
}))

// Zoom control functions
const zoomIn = () => {
  if (!chartContainer.value || !zoomBehavior) return
  const svg = d3.select(chartContainer.value).select('svg')
  svg.transition().duration(300).call(zoomBehavior.scaleBy, 1.5)
}

const zoomOut = () => {
  if (!chartContainer.value || !zoomBehavior) return
  const svg = d3.select(chartContainer.value).select('svg')
  svg.transition().duration(300).call(zoomBehavior.scaleBy, 0.67)
}

const resetZoom = () => {
  if (!chartContainer.value || !zoomBehavior) return
  const svg = d3.select(chartContainer.value).select('svg')
  svg.transition().duration(300).call(zoomBehavior.transform, d3.zoomIdentity)
}

// Build variant tooltip content (for both hover and pinned)
const buildVariantTooltip = (variants, position, isPinned = false) => {
  const count = variants.length
  const firstVariant = variants[0]
  const color = getClassificationColor(firstVariant.category)

  let tooltipContent = `
    <div style="font-weight: 600; color: ${color}; margin-bottom: 4px;">
      Position ${position}
    </div>
  `

  if (count > 1) {
    tooltipContent += `<div style="margin-bottom: 4px;"><strong>${count} variant${count > 1 ? 's' : ''} at this position</strong></div>`
  }

  // Show all variants if pinned, otherwise limit to 3
  const displayVariants = isPinned ? variants : variants.slice(0, 3)

  displayVariants.forEach(v => {
    const effectColor = getEffectColor(v.effect_category)
    const clinvarId = v.accession ? v.accession.replace('VCV', '').replace(/^0+/, '') : ''

    tooltipContent += `
      <div style="border-top: 1px solid #eee; padding-top: 6px; margin-top: 6px;">
        <div style="font-weight: 600;">${v.protein_change || 'Unknown'}</div>
        ${v.cdna_change ? `<div style="font-size: 11px; color: #666;">${v.cdna_change}</div>` : ''}
        <div style="font-size: 11px; margin-top: 2px;">
          <span style="color: ${color}; font-weight: 500;">${v.classification || 'Unknown'}</span>
          <span style="color: ${effectColor}; margin-left: 6px; background: ${effectColor}22; padding: 1px 4px; border-radius: 3px;">${v.effect_category || 'other'}</span>
        </div>
        <div style="font-size: 10px; color: #666; margin-top: 2px;">
          ${v.review_status || ''} ${clinvarId ? '•' : ''}
          ${clinvarId ? `<a href="https://www.ncbi.nlm.nih.gov/clinvar/variation/${clinvarId}/" target="_blank" rel="noopener noreferrer" style="color: #1976D2; text-decoration: none;">${v.accession}</a>` : ''}
        </div>
      </div>
    `
  })

  if (!isPinned && count > 3) {
    tooltipContent += `<div style="font-size: 11px; color: #666; margin-top: 6px; font-style: italic;">Click to see all ${count} variants</div>`
  }

  return tooltipContent
}

const renderChart = () => {
  if (!chartContainer.value || !props.uniprotData) {
    return
  }

  // Close any pinned tooltip on re-render
  unpinTooltip()

  // Clear previous chart
  d3.select(chartContainer.value).selectAll('*').remove()

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
    d3.select(chartContainer.value)
      .append('div')
      .style('display', 'flex')
      .style('align-items', 'center')
      .style('justify-content', 'center')
      .style('height', containerHeight + 'px')
      .style('color', 'var(--v-theme-on-surface-variant)')
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
  const svg = d3
    .select(chartContainer.value)
    .append('svg')
    .attr('width', containerWidth)
    .attr('height', containerHeight)

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
  const xScale = d3.scaleLinear().domain([0, proteinLength]).range([0, width])

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
    .style('fill', colors.value.text)
    .text(`${props.uniprotData.protein_name || props.uniprotData.accession} (${proteinLength} aa)`)

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
    .attr('fill', colors.value.backbone)
    .attr('rx', 4)

  // Draw domains
  const domainHeight = 30
  const domainsGroup = contentGroup.append('g').attr('class', 'domains-group')

  const drawDomains = scale => {
    domainsGroup.selectAll('*').remove()

    domains.value.forEach(domain => {
      const x = scale(domain.start)
      const domainWidth = Math.max(scale(domain.end) - scale(domain.start), 4)
      const color = getDomainColor(domain.type)

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
        .attr('stroke', d3.color(color).darker(0.3))
        .attr('stroke-width', 1)
        .style('cursor', 'pointer')

      // Hover effects
      domainRect
        .on('mouseover', function (event) {
          if (isPinned.value) return

          d3.select(this)
            .transition()
            .duration(150)
            .attr('fill', d3.color(color).darker(0.2))
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
                <a href="https://www.ebi.ac.uk/interpro/entry/pfam/${pfam.id}" target="_blank" rel="noopener noreferrer" style="color: #1976D2;">
                  View in Pfam (${pfam.id})
                </a>
              </div>`
            }
          }

          showTooltip(
            event,
            `
            <div style="font-weight: 600; color: ${color}; margin-bottom: 4px;">
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
          d3.select(this)
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
      const color = getClassificationColor(variant.category)
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
        .attr('stroke', d3.color(color).darker(0.5))
        .attr('stroke-width', 1)
        .style('cursor', 'pointer')

      // Hover effects for lollipop
      lollipopHead
        .on('mouseover', function (event) {
          if (isPinned.value) return

          d3.select(this)
            .transition()
            .duration(150)
            .attr('r', radius + 2)
            .attr('stroke-width', 2)

          showTooltip(event, buildVariantTooltip(variants, position, false))
        })
        .on('mouseout', function () {
          d3.select(this).transition().duration(150).attr('r', radius).attr('stroke-width', 1)

          hideTooltip()
        })
        .on('click', function (event) {
          event.stopPropagation()

          d3.select(this)
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
  const xAxis = d3
    .axisBottom(xScale)
    .ticks(Math.min(10, Math.floor(width / 80)))
    .tickFormat(d => d)

  const axisGroup = g
    .append('g')
    .attr('class', 'x-axis')
    .attr('transform', `translate(0, ${axisY})`)
    .call(xAxis)

  axisGroup.selectAll('text').style('font-size', '10px').style('fill', colors.value.text)

  axisGroup.selectAll('.domain, line').style('stroke', colors.value.text).style('opacity', 0.5)

  // Axis label
  svg
    .append('text')
    .attr('x', containerWidth / 2)
    .attr('y', containerHeight - 5)
    .attr('text-anchor', 'middle')
    .style('font-size', '10px')
    .style('fill', colors.value.text)
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
        .attr('fill', getDomainColor(type))
        .attr('rx', 2)

      // Label
      g.append('text')
        .attr('x', x + 16)
        .attr('y', legendY + 10)
        .style('font-size', '10px')
        .style('fill', colors.value.text)
        .text(type)
    })
  }

  // Initial draw
  drawDomains(xScaleZoomed)
  drawLollipops(xScaleZoomed)

  // Setup zoom behavior
  zoomBehavior = d3
    .zoom()
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
      drawDomains(xScaleZoomed)
      drawLollipops(xScaleZoomed)

      // Update axis
      axisGroup.call(d3.axisBottom(xScaleZoomed).ticks(Math.min(10, Math.floor(width / 80))))
      axisGroup.selectAll('text').style('font-size', '10px').style('fill', colors.value.text)
      axisGroup.selectAll('.domain, line').style('stroke', colors.value.text).style('opacity', 0.5)

      // Update backbone width
      contentGroup
        .select('.backbone')
        .attr('x', xScaleZoomed(0))
        .attr('width', xScaleZoomed(proteinLength) - xScaleZoomed(0))
    })

  // Apply zoom to SVG
  svg.call(zoomBehavior)

  // Apply existing transform if any
  if (currentTransform !== d3.zoomIdentity) {
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
  d3.selectAll('.visualization-tooltip').remove()
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
  () => theme.global.name.value,
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

.filter-controls {
  padding: 12px;
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 8px;
}

.filter-group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.filter-label {
  min-width: 90px;
}

.zoom-controls {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
