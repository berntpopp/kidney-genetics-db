<template>
  <div ref="chartContainer" class="d3-donut-chart"></div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppTheme } from '@/composables/useAppTheme'
import * as d3 from 'd3'

const { isDark } = useAppTheme()
const chartContainer = ref(null)
let resizeObserver = null
let tooltip = null

const props = defineProps({
  data: {
    type: Array,
    required: true,
    validator: value => {
      return value.every(
        item =>
          Object.prototype.hasOwnProperty.call(item, 'category') &&
          Object.prototype.hasOwnProperty.call(item, 'gene_count')
      )
    }
  },
  total: {
    type: Number,
    default: null
  },
  average: {
    type: Number,
    default: null
  },
  averageLabel: {
    type: String,
    default: 'Average'
  },
  centerLabel: {
    type: String,
    default: 'Total'
  },
  height: {
    type: Number,
    default: 400
  },
  showTotal: {
    type: Boolean,
    default: true
  },
  valueLabel: {
    type: String,
    default: 'genes'
  },
  valueFormatter: {
    type: Function,
    default: value => Math.round(value)
  },
  isPercentage: {
    type: Boolean,
    default: false
  }
})

// Computed total if not provided
const computedTotal = computed(() => {
  if (props.total !== null) return props.total
  return props.data.reduce((sum, d) => sum + d.gene_count, 0)
})

// Color scale for segments (use provided colors or generate)
const colorScale = computed(() => {
  return d3
    .scaleOrdinal()
    .domain(props.data.map(d => d.category))
    .range(d3.schemeTableau10)
})

const renderChart = () => {
  if (!chartContainer.value || !props.data || props.data.length === 0) {
    return
  }

  // Clear previous chart
  d3.select(chartContainer.value).selectAll('*').remove()

  // Get container dimensions
  const containerWidth = chartContainer.value.clientWidth
  const containerHeight = props.height

  // Validate dimensions
  const minSize = 200
  if (containerWidth < minSize || containerHeight < minSize) {
    window.logService.warn('Container too small for donut chart', {
      containerWidth,
      containerHeight,
      minSize
    })

    // Show message
    d3
      .select(chartContainer.value)
      .append('div')
      .style('display', 'flex')
      .style('align-items', 'center')
      .style('justify-content', 'center')
      .style('height', containerHeight + 'px')
      .style('color', 'var(--v-theme-on-surface-variant)')
      .style('text-align', 'center').html(`
        <div>
          <p>Container too small for chart</p>
          <p style="font-size: 0.875rem; margin-top: 8px;">
            Minimum: ${minSize}px × ${minSize}px
          </p>
        </div>
      `)
    return
  }

  // Calculate radius based on smaller dimension
  const width = containerWidth
  const height = containerHeight
  const radius = Math.min(width, height) / 2 - 20 // 20px margin

  // Create SVG
  const svg = d3
    .select(chartContainer.value)
    .append('svg')
    .attr('width', width)
    .attr('height', height)

  // Create main group centered
  const g = svg.append('g').attr('transform', `translate(${width / 2}, ${height / 2})`)

  // Create pie layout
  const pie = d3
    .pie()
    .value(d => d.gene_count)
    .sort(null) // Keep original order

  // Create arc generator for donut
  const arc = d3
    .arc()
    .innerRadius(radius * 0.6) // Donut hole
    .outerRadius(radius)

  // Create arc generator for hover effect
  const arcHover = d3
    .arc()
    .innerRadius(radius * 0.6)
    .outerRadius(radius + 5) // Slightly larger on hover

  // Get theme colors
  const textColor = window
    .getComputedStyle(chartContainer.value)
    .getPropertyValue('--v-theme-on-surface')
    .trim()

  // Generate pie data
  const pieData = pie(props.data)

  // Create donut segments
  const paths = g
    .selectAll('path')
    .data(pieData)
    .enter()
    .append('path')
    .attr('d', arc)
    .attr('fill', d => d.data.color || colorScale.value(d.data.category))
    .attr('stroke', 'var(--v-theme-surface)')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')
    .on('mouseover', function (event, d) {
      // Highlight segment
      d3.select(this).transition().duration(200).attr('d', arcHover)

      // Show tooltip
      showTooltip(event, d)
    })
    .on('mouseout', function () {
      // Return to normal
      d3.select(this).transition().duration(200).attr('d', arc)

      // Hide tooltip
      hideTooltip()
    })

  // Add smooth entrance animation
  paths
    .transition()
    .duration(750)
    .attrTween('d', function (d) {
      const interpolate = d3.interpolate({ startAngle: 0, endAngle: 0 }, d)
      return function (t) {
        return arc(interpolate(t))
      }
    })

  // Add center text group (only if showTotal is true)
  if (props.showTotal) {
    const centerGroup = g.append('g').attr('text-anchor', 'middle')

    const hasAverage = props.average !== null

    if (props.isPercentage && hasAverage) {
      // Percentage view with gene count: 4-line hierarchical composition
      // Line 1: Large percentage (lower and more centered)
      centerGroup
        .append('text')
        .attr('dy', '-0.8em')
        .style('font-size', '42px')
        .style('font-weight', 'bold')
        .style('fill', textColor)
        .text(`${computedTotal.value}%`)

      // Line 2: Small label for percentage
      centerGroup
        .append('text')
        .attr('dy', '0.5em')
        .style('font-size', '11px')
        .style('font-weight', 'normal')
        .style('fill', textColor)
        .style('opacity', 0.6)
        .text(props.centerLabel)

      // Line 3: Gene count (smaller)
      centerGroup
        .append('text')
        .attr('dy', '1.8em')
        .style('font-size', '16px')
        .style('font-weight', '500')
        .style('fill', textColor)
        .text(props.average.toLocaleString())

      // Line 4: Small label for gene count
      centerGroup
        .append('text')
        .attr('dy', '2.8em')
        .style('font-size', '11px')
        .style('font-weight', 'normal')
        .style('fill', textColor)
        .style('opacity', 0.6)
        .text(props.averageLabel)
    } else if (hasAverage) {
      // Count view with average: 3-line composition
      centerGroup
        .append('text')
        .attr('dy', '-1.2em')
        .style('font-size', '36px')
        .style('font-weight', 'bold')
        .style('fill', textColor)
        .text(computedTotal.value)

      centerGroup
        .append('text')
        .attr('dy', '0.3em')
        .style('font-size', '12px')
        .style('font-weight', 'normal')
        .style('fill', textColor)
        .style('opacity', 0.6)
        .text(props.centerLabel)

      centerGroup
        .append('text')
        .attr('dy', '2.1em')
        .style('font-size', '14px')
        .style('font-weight', '500')
        .style('fill', textColor)
        .style('opacity', 0.8)
        .text(`${props.averageLabel}: ${props.average}`)
    } else {
      // Simple 2-line composition: value + label
      centerGroup
        .append('text')
        .attr('dy', '-0.3em')
        .style('font-size', '42px')
        .style('font-weight', 'bold')
        .style('fill', textColor)
        .text(props.isPercentage ? `${computedTotal.value}%` : computedTotal.value)

      centerGroup
        .append('text')
        .attr('dy', '1.5em')
        .style('font-size', '13px')
        .style('font-weight', 'normal')
        .style('fill', textColor)
        .style('opacity', 0.7)
        .text(props.centerLabel)
    }
  }
}

// Tooltip functions
const showTooltip = (event, d) => {
  if (!tooltip) {
    tooltip = d3
      .select('body')
      .append('div')
      .attr('class', 'chart-tooltip')
      .style('position', 'absolute')
      .style('pointer-events', 'none')
      .style('background', 'var(--v-theme-surface)')
      .style('color', 'var(--v-theme-on-surface)')
      .style('border', '1px solid var(--v-theme-outline)')
      .style('padding', '8px 12px')
      .style('border-radius', '4px')
      .style('font-size', '12px')
      .style('line-height', '1.4')
      .style('z-index', '1000')
      .style('box-shadow', '0 2px 8px rgba(0,0,0,0.15)')
      .style('opacity', 0)
  }

  tooltip.transition().duration(200).style('opacity', 0.95)

  // Format tooltip content based on whether values are percentages or counts
  let valueDisplay
  if (props.isPercentage) {
    // Values are already percentages - just show them with % sign
    valueDisplay = `${props.valueFormatter(d.data.gene_count)}%`
  } else {
    // Values are counts - show count + calculated percentage
    const percentage = ((d.data.gene_count / computedTotal.value) * 100).toFixed(1)
    valueDisplay = `${props.valueFormatter(d.data.gene_count)} ${props.valueLabel} (${percentage}%)`
  }

  tooltip
    .html(
      `
    <div>
      <strong style="color: var(--v-theme-primary); display: block; margin-bottom: 4px;">
        ${d.data.category}
      </strong>
      <div>${valueDisplay}</div>
    </div>
  `
    )
    .style('left', event.pageX + 10 + 'px')
    .style('top', event.pageY - 28 + 'px')
}

const hideTooltip = () => {
  if (tooltip) {
    tooltip.transition().duration(500).style('opacity', 0)
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
  if (tooltip) {
    tooltip.remove()
    tooltip = null
  }
})

// Re-render on data changes
watch(
  () => props.data,
  () => nextTick(renderChart),
  { deep: true }
)
watch(
  () => props.total,
  () => nextTick(renderChart)
)
watch(
  () => props.average,
  () => nextTick(renderChart)
)
watch(
  () => props.averageLabel,
  () => nextTick(renderChart)
)
watch(
  () => props.showTotal,
  () => nextTick(renderChart)
)
watch(
  () => isDark.value,
  () => nextTick(renderChart)
)
</script>

<style scoped>
.d3-donut-chart {
  width: 100%;
  min-height: 400px;
  position: relative;
}

/* Ensure tooltip inherits theme colors */
:deep(.chart-tooltip) {
  background: var(--v-theme-surface);
  color: var(--v-theme-on-surface);
  border-color: var(--v-theme-outline);
}
</style>
