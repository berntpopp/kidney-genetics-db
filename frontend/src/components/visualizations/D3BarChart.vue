<template>
  <div ref="chartContainer" class="d3-bar-chart text-foreground"></div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAppTheme } from '@/composables/useAppTheme'
import { select } from 'd3-selection'
import { scaleBand, scaleLinear } from 'd3-scale'
import { max } from 'd3-array'
import { axisLeft, axisBottom } from 'd3-axis'
import { format } from 'd3-format'
import 'd3-transition'
import { markOutline } from './chartMarks'

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
  /** Any CSS colour, e.g. a source's var(--source-n); defaults to a neutral */
  barColor: {
    type: String,
    default: 'var(--muted-foreground)'
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

// Text alternative for the SVG: every value, not only on hover
const ariaLabel = computed(
  () =>
    `Bar chart of ${props.yAxisLabel} by ${props.xAxisLabel}: ` +
    props.data
      .map(d => `${d.category}: ${props.valueFormatter(d.gene_count)} ${props.valueLabel}`)
      .join('; ')
)

// Animate only when the data changes: a resize (even a scrollbar appearing) redraws in place
const renderChart = (animate = true) => {
  const ms = animate && !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 750 : 0
  if (!chartContainer.value || !props.data || props.data.length === 0) {
    return
  }

  // Clear previous chart
  select(chartContainer.value).selectAll('*').remove()

  // Get container dimensions
  const containerWidth = chartContainer.value.clientWidth
  const containerHeight = props.height

  // Margins for axes and labels (reduced on narrow screens)
  const isNarrow = containerWidth < 400
  const margin = {
    top: 20,
    right: isNarrow ? 10 : 20,
    // Room for the x labels, rotated -35° only when needed (see below); ~6.5px per char
    bottom: isNarrow ? 60 : 80,
    left: isNarrow ? 52 : 70
  }
  const labelPx = (max(props.data, d => String(d.category).length) || 0) * 6.5
  const roughBand = (containerWidth - margin.left - margin.right) / Math.max(props.data.length, 1)
  if (labelPx > roughBand * 0.8)
    margin.bottom = Math.min(160, Math.max(margin.bottom, labelPx * 0.58 + 40))
  const width = containerWidth - margin.left - margin.right
  const height = containerHeight - margin.top - margin.bottom

  // Validate dimensions
  const minWidth = 100
  const minHeight = 150
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
    select(chartContainer.value)
      .append('div')
      .style('display', 'flex')
      .style('align-items', 'center')
      .style('justify-content', 'center')
      .style('height', containerHeight + 'px')
      .style('color', 'var(--muted-foreground)')
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
  const svg = select(chartContainer.value)
    .append('svg')
    .attr('width', containerWidth)
    .attr('height', containerHeight)
    .attr('role', 'img')
    .attr('aria-label', ariaLabel.value)

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

  // Get theme colors from computed style (SVG needs resolved color values)
  const computedStyle = window.getComputedStyle(chartContainer.value)
  const textColor = computedStyle.color
  const gridColor = computedStyle.getPropertyValue('--border').trim()

  // Create scales
  const xScale = scaleBand()
    .domain(props.data.map(d => String(d.category)))
    .range([0, width])
    .padding(0.2)

  const maxValue = max(props.data, d => d.gene_count) || 1
  const yScale = scaleLinear().domain([0, maxValue]).nice().range([height, 0])

  // Add Y-axis grid lines
  g.append('g')
    .attr('class', 'grid')
    .style('stroke', gridColor)
    .style('stroke-opacity', 0.1)
    .call(axisLeft(yScale).tickSize(-width).tickFormat(''))
    .selectAll('line')
    .style('stroke-dasharray', '2,2')

  // Add X axis
  const xAxis = g
    .append('g')
    .attr('class', 'x-axis')
    .attr('transform', `translate(0,${height})`)
    .call(axisBottom(xScale))

  // Style X axis; rotate only when the longest label (~6.5px per char) cannot fit its band
  const xLabels = xAxis.selectAll('text').style('fill', textColor).style('font-size', '11px')
  if (labelPx > xScale.bandwidth()) {
    xLabels
      .attr('transform', 'rotate(-35)')
      .style('text-anchor', 'end')
      .attr('dx', '-0.5em')
      .attr('dy', '0.25em')
  }

  xAxis.selectAll('path, line').style('stroke', gridColor)

  // Add Y axis
  const yAxis = g
    .append('g')
    .attr('class', 'y-axis')
    .call(
      axisLeft(yScale)
        .ticks(5)
        .tickFormat(d => format('.0f')(d))
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
    .attr('rx', 2) // Rounded corners
    .style('fill', d => d.color ?? props.barColor)
    .style('stroke', d => markOutline(d.color ?? props.barColor))
    .style('stroke-width', 1)
    .on('mouseover', function (event, d) {
      select(this).style('fill-opacity', 0.8)
      showTooltip(event, d)
    })
    .on('mouseout', function () {
      select(this).style('fill-opacity', 1)
      hideTooltip()
    })

  // Animate bars
  bars
    .transition()
    .duration(ms)
    .delay((d, i) => (ms ? i * 50 : 0)) // Stagger animation
    .attr('y', d => yScale(d.gene_count))
    .attr('height', d => height - yScale(d.gene_count))

  // Value labels: readable without hover, in print and on touch screens
  g.selectAll('.bar-value')
    .data(props.data)
    .enter()
    .append('text')
    .attr('class', 'bar-value')
    .attr('aria-hidden', 'true')
    .attr('x', d => xScale(String(d.category)) + xScale.bandwidth() / 2)
    .attr('y', d => yScale(d.gene_count) - 4)
    .style('text-anchor', 'middle')
    .style('fill', textColor)
    .style('font-size', '11px')
    .style('font-variant-numeric', 'tabular-nums')
    .text(d => Number(props.valueFormatter(d.gene_count)).toLocaleString())

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
    .attr('y', 12)
    .style('text-anchor', 'middle')
    .style('fill', textColor)
    .style('font-size', '12px')
    .style('font-weight', '500')
    .text(props.yAxisLabel)
}

// Tooltip functions
const showTooltip = (event, d) => {
  if (!tooltip) {
    tooltip = select('body')
      .append('div')
      .attr('class', 'chart-tooltip shadow-md')
      .style('position', 'absolute')
      .style('pointer-events', 'none')
      .style('background', 'var(--card)')
      .style('color', 'var(--foreground)')
      .style('border', '1px solid var(--border)')
      .style('padding', '8px 12px')
      .style('border-radius', '4px')
      .style('font-size', '12px')
      .style('line-height', '1.4')
      .style('z-index', '1000')
      .style('opacity', 0)
  }

  tooltip.transition().duration(200).style('opacity', 0.95)

  tooltip
    .html(
      `
    <div>
      <strong style="display: block; margin-bottom: 4px; font-weight: 600;">
        ${props.xAxisLabel}: ${d.category}
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
    renderChart(false)
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
  background: var(--card);
  color: var(--foreground);
  border-color: var(--border);
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
