<template>
  <div ref="chartContainer" class="d3-bar-chart"></div>
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
  xAxisLabel: {
    type: String,
    default: 'Category'
  },
  yAxisLabel: {
    type: String,
    default: 'Gene Count'
  },
  barColor: {
    type: String,
    default: null
  },
  height: {
    type: Number,
    default: 400
  },
  valueLabel: {
    type: String,
    default: 'genes'
  },
  valueFormatter: {
    type: Function,
    default: value => Math.round(value)
  }
})

// Computed bar color (use theme primary if not provided)
const computedBarColor = computed(() => {
  if (props.barColor) return props.barColor
  return (
    window
      .getComputedStyle(chartContainer.value || document.documentElement)
      .getPropertyValue('--v-theme-primary')
      .trim() || '#1976D2'
  )
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

  // Margins for axes and labels
  const margin = { top: 20, right: 20, bottom: 80, left: 70 }
  const width = containerWidth - margin.left - margin.right
  const height = containerHeight - margin.top - margin.bottom

  // Validate dimensions
  const minWidth = 200
  const minHeight = 200
  if (width < minWidth || height < minHeight) {
    window.logService.warn('Container too small for bar chart', {
      containerWidth,
      containerHeight,
      width,
      height,
      minWidth,
      minHeight
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
            Minimum: ${minWidth + margin.left + margin.right}px × ${minHeight + margin.top + margin.bottom}px
          </p>
        </div>
      `)
    return
  }

  // Create SVG
  const svg = d3
    .select(chartContainer.value)
    .append('svg')
    .attr('width', containerWidth)
    .attr('height', containerHeight)

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

  // Get theme colors
  const textColor = window
    .getComputedStyle(chartContainer.value)
    .getPropertyValue('--v-theme-on-surface')
    .trim()
  const gridColor = window
    .getComputedStyle(chartContainer.value)
    .getPropertyValue('--v-theme-outline')
    .trim()

  // Create scales
  const xScale = d3
    .scaleBand()
    .domain(props.data.map(d => String(d.category)))
    .range([0, width])
    .padding(0.2)

  const maxValue = d3.max(props.data, d => d.gene_count) || 1
  const yScale = d3.scaleLinear().domain([0, maxValue]).nice().range([height, 0])

  // Add Y-axis grid lines
  g.append('g')
    .attr('class', 'grid')
    .style('stroke', gridColor)
    .style('stroke-opacity', 0.1)
    .call(d3.axisLeft(yScale).tickSize(-width).tickFormat(''))
    .selectAll('line')
    .style('stroke-dasharray', '2,2')

  // Add X axis
  const xAxis = g
    .append('g')
    .attr('class', 'x-axis')
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(xScale))

  // Style X axis
  xAxis
    .selectAll('text')
    .style('fill', textColor)
    .style('font-size', '11px')
    .attr('transform', 'rotate(-45)')
    .style('text-anchor', 'end')
    .attr('dx', '-0.5em')
    .attr('dy', '0.25em')

  xAxis.selectAll('path, line').style('stroke', gridColor)

  // Add Y axis
  const yAxis = g
    .append('g')
    .attr('class', 'y-axis')
    .call(
      d3
        .axisLeft(yScale)
        .ticks(5)
        .tickFormat(d => d3.format('.0f')(d))
    )

  // Style Y axis
  yAxis.selectAll('text').style('fill', textColor).style('font-size', '11px')

  yAxis.selectAll('path, line').style('stroke', gridColor)

  // Add bars with animation
  const bars = g
    .selectAll('.bar')
    .data(props.data)
    .enter()
    .append('rect')
    .attr('class', 'bar')
    .attr('x', d => xScale(String(d.category)))
    .attr('width', xScale.bandwidth())
    .attr('y', height) // Start from bottom
    .attr('height', 0) // Start with 0 height
    .attr('fill', computedBarColor.value)
    .attr('rx', 2) // Rounded corners
    .style('cursor', 'pointer')
    .on('mouseover', function (event, d) {
      // Highlight bar
      d3.select(this)
        .transition()
        .duration(200)
        .attr('fill', d3.color(computedBarColor.value).darker(0.3))

      // Show tooltip
      showTooltip(event, d)
    })
    .on('mouseout', function () {
      // Return to normal
      d3.select(this).transition().duration(200).attr('fill', computedBarColor.value)

      // Hide tooltip
      hideTooltip()
    })

  // Animate bars
  bars
    .transition()
    .duration(750)
    .delay((d, i) => i * 50) // Stagger animation
    .attr('y', d => yScale(d.gene_count))
    .attr('height', d => height - yScale(d.gene_count))

  // Add X-axis label
  svg
    .append('text')
    .attr('x', margin.left + width / 2)
    .attr('y', containerHeight - 10)
    .style('text-anchor', 'middle')
    .style('fill', textColor)
    .style('font-size', '12px')
    .style('font-weight', '500')
    .text(props.xAxisLabel)

  // Add Y-axis label
  svg
    .append('text')
    .attr('transform', 'rotate(-90)')
    .attr('x', -(margin.top + height / 2))
    .attr('y', 15)
    .style('text-anchor', 'middle')
    .style('fill', textColor)
    .style('font-size', '12px')
    .style('font-weight', '500')
    .text(props.yAxisLabel)
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

  tooltip
    .html(
      `
    <div>
      <strong style="color: var(--v-theme-primary); display: block; margin-bottom: 4px;">
        ${d.category}
      </strong>
      <div>${props.valueFormatter(d.gene_count)} ${props.valueLabel}</div>
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
  () => props.xAxisLabel,
  () => nextTick(renderChart)
)
watch(
  () => props.yAxisLabel,
  () => nextTick(renderChart)
)
watch(
  () => props.barColor,
  () => nextTick(renderChart)
)
watch(
  () => isDark.value,
  () => nextTick(renderChart)
)
</script>

<style scoped>
.d3-bar-chart {
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

/* Hide default D3 axis domain */
:deep(.x-axis .domain),
:deep(.y-axis .domain) {
  display: none;
}

/* Grid styling */
:deep(.grid .domain) {
  display: none;
}
</style>
