<template>
  <div ref="chartContainer" class="gene-structure-visualization"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import { useTheme } from 'vuetify'
import * as d3 from 'd3'
import { useD3Tooltip } from '@/composables/useD3Tooltip'

const theme = useTheme()
const chartContainer = ref(null)
let resizeObserver = null

const { show: showTooltip, hide: hideTooltip, remove: removeTooltip } = useD3Tooltip()

const props = defineProps({
  geneSymbol: {
    type: String,
    required: true
  },
  ensemblData: {
    type: Object,
    required: true
  },
  height: {
    type: Number,
    default: 200
  }
})

// Get exons from canonical transcript
const exons = computed(() => {
  const transcript = props.ensemblData?.canonical_transcript
  if (!transcript?.exons) return []
  return [...transcript.exons].sort((a, b) => a.start - b.start)
})

// Colors for visualization
const colors = computed(() => ({
  exon: '#1976D2',
  exonHover: '#1565C0',
  intron: '#E0E0E0',
  intronDark: '#9E9E9E',
  utr: '#90CAF9',
  text: theme.global.current.value.dark ? '#FFFFFF' : '#333333'
}))

const renderChart = () => {
  if (!chartContainer.value || exons.value.length === 0) {
    return
  }

  // Clear previous chart
  d3.select(chartContainer.value).selectAll('*').remove()

  // Get container dimensions
  const containerWidth = chartContainer.value.clientWidth
  const containerHeight = props.height

  // Margins
  const margin = { top: 40, right: 40, bottom: 40, left: 40 }
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

  // Get gene coordinates
  const geneStart = props.ensemblData.start
  const geneEnd = props.ensemblData.end

  // Create SVG
  const svg = d3
    .select(chartContainer.value)
    .append('svg')
    .attr('width', containerWidth)
    .attr('height', containerHeight)

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

  // Create scale
  const xScale = d3.scaleLinear().domain([geneStart, geneEnd]).range([0, width])

  // Draw title
  svg
    .append('text')
    .attr('x', containerWidth / 2)
    .attr('y', 20)
    .attr('text-anchor', 'middle')
    .style('font-size', '14px')
    .style('font-weight', '600')
    .style('fill', colors.value.text)
    .text(
      `${props.geneSymbol} - ${props.ensemblData.canonical_transcript?.transcript_id || 'Canonical Transcript'}`
    )

  // Draw gene backbone (intron line)
  const backboneY = height / 2
  const backboneHeight = 4

  g.append('rect')
    .attr('x', 0)
    .attr('y', backboneY - backboneHeight / 2)
    .attr('width', width)
    .attr('height', backboneHeight)
    .attr('fill', colors.value.intron)
    .attr('rx', 2)

  // Draw strand direction arrow
  const strandSymbol = props.ensemblData.strand === '+' ? '\u25B6' : '\u25C0' // Triangle right or left
  g.append('text')
    .attr('x', props.ensemblData.strand === '+' ? width + 10 : -10)
    .attr('y', backboneY + 5)
    .attr('text-anchor', props.ensemblData.strand === '+' ? 'start' : 'end')
    .style('font-size', '16px')
    .style('fill', colors.value.text)
    .text(strandSymbol)

  // Draw exons
  const exonHeight = 40

  exons.value.forEach(exon => {
    const x = xScale(exon.start)
    const exonWidth = Math.max(xScale(exon.end) - xScale(exon.start), 2) // Minimum width of 2px

    // Exon rectangle
    const exonRect = g
      .append('rect')
      .attr('x', x)
      .attr('y', backboneY - exonHeight / 2)
      .attr('width', exonWidth)
      .attr('height', exonHeight)
      .attr('fill', colors.value.exon)
      .attr('rx', 3)
      .attr('stroke', '#1565C0')
      .attr('stroke-width', 1)
      .style('cursor', 'pointer')

    // Hover effects
    exonRect
      .on('mouseover', function (event) {
        d3.select(this)
          .transition()
          .duration(150)
          .attr('fill', colors.value.exonHover)
          .attr('y', backboneY - exonHeight / 2 - 2)
          .attr('height', exonHeight + 4)

        showTooltip(
          event,
          `
          <div style="font-weight: 600; color: var(--v-theme-primary); margin-bottom: 4px;">
            Exon ${exon.exon_number}
          </div>
          <div><strong>ID:</strong> ${exon.exon_id}</div>
          <div><strong>Start:</strong> ${exon.start?.toLocaleString()}</div>
          <div><strong>End:</strong> ${exon.end?.toLocaleString()}</div>
          <div><strong>Length:</strong> ${exon.length?.toLocaleString()} bp</div>
        `
        )
      })
      .on('mouseout', function () {
        d3.select(this)
          .transition()
          .duration(150)
          .attr('fill', colors.value.exon)
          .attr('y', backboneY - exonHeight / 2)
          .attr('height', exonHeight)

        hideTooltip()
      })

    // Exon number label (only if wide enough)
    if (exonWidth > 20) {
      g.append('text')
        .attr('x', x + exonWidth / 2)
        .attr('y', backboneY + 4)
        .attr('text-anchor', 'middle')
        .style('font-size', '10px')
        .style('fill', 'white')
        .style('pointer-events', 'none')
        .text(exon.exon_number)
    }
  })

  // Draw scale bar at bottom
  const scaleBarY = height + 10
  const geneLengthKb = Math.round((geneEnd - geneStart) / 1000)
  const scaleBarLength = Math.min(width / 4, 100)
  const scaleBarValue = Math.round(((scaleBarLength / width) * (geneEnd - geneStart)) / 1000)

  g.append('line')
    .attr('x1', 0)
    .attr('y1', scaleBarY)
    .attr('x2', scaleBarLength)
    .attr('y2', scaleBarY)
    .attr('stroke', colors.value.text)
    .attr('stroke-width', 2)

  g.append('text')
    .attr('x', scaleBarLength / 2)
    .attr('y', scaleBarY + 14)
    .attr('text-anchor', 'middle')
    .style('font-size', '10px')
    .style('fill', colors.value.text)
    .text(`${scaleBarValue} kb`)

  // Chromosome location label
  svg
    .append('text')
    .attr('x', containerWidth - margin.right)
    .attr('y', containerHeight - 10)
    .attr('text-anchor', 'end')
    .style('font-size', '10px')
    .style('fill', colors.value.text)
    .style('opacity', 0.7)
    .text(
      `chr${props.ensemblData.chromosome}:${geneStart?.toLocaleString()}-${geneEnd?.toLocaleString()} (${geneLengthKb} kb)`
    )
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
  () => props.ensemblData,
  () => nextTick(renderChart),
  { deep: true }
)

watch(
  () => theme.global.name.value,
  () => nextTick(renderChart)
)
</script>

<style scoped>
.gene-structure-visualization {
  width: 100%;
  min-height: 200px;
  position: relative;
}
</style>
