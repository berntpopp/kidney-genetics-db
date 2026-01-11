/**
 * D3 Tooltip Composable
 *
 * Provides reusable tooltip functionality for D3 visualizations.
 * Handles tooltip creation, positioning, and cleanup.
 */

import * as d3 from 'd3'
import { onUnmounted } from 'vue'

/**
 * Create a D3 tooltip composable
 * @returns {Object} Tooltip functions: show, hide, remove
 */
export function useD3Tooltip() {
  let tooltip = null

  /**
   * Show tooltip with HTML content
   * @param {MouseEvent} event - Mouse event for positioning
   * @param {string} content - HTML content for tooltip
   */
  const show = (event, content) => {
    if (!tooltip) {
      tooltip = d3
        .select('body')
        .append('div')
        .attr('class', 'visualization-tooltip')
        .style('position', 'absolute')
        .style('pointer-events', 'none')
        .style('background', 'var(--v-theme-surface)')
        .style('color', 'var(--v-theme-on-surface)')
        .style('border', '1px solid var(--v-theme-outline)')
        .style('padding', '10px 14px')
        .style('border-radius', '6px')
        .style('font-size', '12px')
        .style('line-height', '1.5')
        .style('z-index', '1000')
        .style('box-shadow', '0 4px 12px rgba(0,0,0,0.15)')
        .style('max-width', '300px')
        .style('opacity', 0)
    }

    tooltip.transition().duration(200).style('opacity', 0.95)

    tooltip
      .html(content)
      .style('left', event.pageX + 12 + 'px')
      .style('top', event.pageY - 10 + 'px')
  }

  /**
   * Hide tooltip with fade animation
   */
  const hide = () => {
    if (tooltip) {
      tooltip.transition().duration(300).style('opacity', 0)
    }
  }

  /**
   * Remove tooltip from DOM completely
   */
  const remove = () => {
    if (tooltip) {
      tooltip.remove()
      tooltip = null
    }
  }

  // Cleanup on unmount
  onUnmounted(() => {
    remove()
  })

  return {
    show,
    hide,
    remove
  }
}
