<template>
  <div ref="chartContainer" class="protein-domain-visualization"></div>
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
  uniprotData: {
    type: Object,
    required: true
  },
  height: {
    type: Number,
    default: 200
  }
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

// Get color for domain type
const getDomainColor = type => {
  return domainColors[type] || '#757575'
}

// Colors for visualization
const colors = computed(() => ({
  backbone: theme.global.current.value.dark ? '#616161' : '#E0E0E0',
  text: theme.global.current.value.dark ? '#FFFFFF' : '#333333'
}))

const renderChart = () => {
  if (!chartContainer.value || !props.uniprotData) {
    return
  }

  // Clear previous chart
  d3.select(chartContainer.value).selectAll('*').remove()

  // Get container dimensions
  const containerWidth = chartContainer.value.clientWidth
  const containerHeight = props.height

  // Margins
  const margin = { top: 40, right: 40, bottom: 50, left: 40 }
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

  // Create SVG
  const svg = d3
    .select(chartContainer.value)
    .append('svg')
    .attr('width', containerWidth)
    .attr('height', containerHeight)

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

  // Create scale
  const xScale = d3.scaleLinear().domain([0, proteinLength]).range([0, width])

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

  g.append('rect')
    .attr('x', 0)
    .attr('y', backboneY - backboneHeight / 2)
    .attr('width', width)
    .attr('height', backboneHeight)
    .attr('fill', colors.value.backbone)
    .attr('rx', 4)

  // Draw domains
  const domainHeight = 30

  domains.value.forEach(domain => {
    const x = xScale(domain.start)
    const domainWidth = Math.max(xScale(domain.end) - xScale(domain.start), 4)
    const color = getDomainColor(domain.type)

    // Domain rectangle
    const domainRect = g
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
              <a href="https://www.ebi.ac.uk/interpro/entry/pfam/${pfam.id}" target="_blank" rel="noopener noreferrer" style="color: var(--v-theme-primary);">
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

  // Draw axis at bottom
  const axisY = height + 5
  const xAxis = d3
    .axisBottom(xScale)
    .ticks(Math.min(10, Math.floor(width / 80)))
    .tickFormat(d => d)

  g.append('g')
    .attr('transform', `translate(0, ${axisY})`)
    .call(xAxis)
    .selectAll('text')
    .style('font-size', '10px')
    .style('fill', colors.value.text)

  g.selectAll('.domain line, .domain path').style('stroke', colors.value.text).style('opacity', 0.5)

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

  // Draw legend
  const uniqueTypes = [...new Set(domains.value.map(d => d.type))]
  if (uniqueTypes.length > 0) {
    const legendY = -15
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
  () => theme.global.name.value,
  () => nextTick(renderChart)
)
</script>

<style scoped>
.protein-domain-visualization {
  width: 100%;
  min-height: 200px;
  position: relative;
}
</style>
