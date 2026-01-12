/**
 * D3 Tooltip Composable
 *
 * Provides reusable tooltip functionality for D3 visualizations.
 * Supports pinning tooltips on click for interactive content (links, scrolling).
 */

import * as d3 from 'd3'
import { ref, onUnmounted } from 'vue'

/**
 * Create a D3 tooltip composable
 * @returns {Object} Tooltip functions: show, hide, pin, unpin, remove, isPinned
 */
export function useD3Tooltip() {
  let tooltip = null
  const isPinned = ref(false)

  /**
   * Create tooltip element if it doesn't exist
   */
  const ensureTooltip = () => {
    if (!tooltip) {
      tooltip = d3
        .select('body')
        .append('div')
        .attr('class', 'visualization-tooltip')
        .style('position', 'absolute')
        .style('pointer-events', 'none')
        .style('background', '#ffffff')
        .style('color', '#333333')
        .style('border', '1px solid #e0e0e0')
        .style('padding', '0')
        .style('border-radius', '8px')
        .style('font-size', '12px')
        .style('line-height', '1.5')
        .style('z-index', '9999')
        .style('box-shadow', '0 4px 16px rgba(0,0,0,0.2)')
        .style('max-width', '350px')
        .style('max-height', '400px')
        .style('opacity', 0)
    }
    return tooltip
  }

  /**
   * Show tooltip with HTML content
   * @param {MouseEvent} event - Mouse event for positioning
   * @param {string} content - HTML content for tooltip
   * @param {Object} options - Additional options
   */
  const show = (event, content, _options = {}) => {
    if (isPinned.value) return // Don't update if pinned

    ensureTooltip()

    tooltip
      .style('pointer-events', 'none')
      .html(`<div style="padding: 10px 14px;">${content}</div>`)
      .transition()
      .duration(200)
      .style('opacity', 1)

    // Position tooltip
    const tooltipNode = tooltip.node()
    const rect = tooltipNode.getBoundingClientRect()
    let left = event.pageX + 12
    let top = event.pageY - 10

    // Adjust if tooltip would go off screen
    if (left + rect.width > window.innerWidth - 20) {
      left = event.pageX - rect.width - 12
    }
    if (top + rect.height > window.innerHeight + window.scrollY - 20) {
      top = event.pageY - rect.height - 10
    }
    if (top < window.scrollY + 10) {
      top = window.scrollY + 10
    }

    tooltip.style('left', left + 'px').style('top', top + 'px')
  }

  /**
   * Pin tooltip with full content (scrollable, with close button)
   * @param {MouseEvent} event - Mouse event for positioning
   * @param {string} content - HTML content for tooltip
   */
  const pin = (event, content) => {
    ensureTooltip()
    isPinned.value = true

    // Create pinned tooltip with close button and scrollable content
    const pinnedContent = `
      <div style="position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid #eee; background: #f5f5f5; border-radius: 8px 8px 0 0;">
          <span style="font-weight: 600; font-size: 11px; color: #666;">VARIANT DETAILS</span>
          <button class="tooltip-close-btn" style="background: none; border: none; cursor: pointer; font-size: 18px; color: #666; padding: 0 4px; line-height: 1;">&times;</button>
        </div>
        <div style="padding: 10px 14px; max-height: 300px; overflow-y: auto;">
          ${content}
        </div>
      </div>
    `

    tooltip
      .style('pointer-events', 'auto')
      .html(pinnedContent)
      .transition()
      .duration(200)
      .style('opacity', 1)

    // Add close button handler
    tooltip.select('.tooltip-close-btn').on('click', () => {
      unpin()
    })

    // Position tooltip
    const tooltipNode = tooltip.node()
    const rect = tooltipNode.getBoundingClientRect()
    let left = event.pageX + 12
    let top = event.pageY - 10

    // Adjust if tooltip would go off screen
    if (left + rect.width > window.innerWidth - 20) {
      left = event.pageX - rect.width - 12
    }
    if (top + rect.height > window.innerHeight + window.scrollY - 20) {
      top = event.pageY - rect.height - 10
    }
    if (top < window.scrollY + 10) {
      top = window.scrollY + 10
    }

    tooltip.style('left', left + 'px').style('top', top + 'px')

    // Close on click outside
    setTimeout(() => {
      d3.select('body').on('click.tooltip-close', event => {
        if (!tooltip.node().contains(event.target)) {
          unpin()
        }
      })
    }, 100)
  }

  /**
   * Unpin and hide tooltip
   */
  const unpin = () => {
    isPinned.value = false
    d3.select('body').on('click.tooltip-close', null)
    hide()
  }

  /**
   * Hide tooltip with fade animation
   */
  const hide = () => {
    if (tooltip && !isPinned.value) {
      tooltip.transition().duration(300).style('opacity', 0)
    }
  }

  /**
   * Remove tooltip from DOM completely
   */
  const remove = () => {
    isPinned.value = false
    d3.select('body').on('click.tooltip-close', null)
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
    pin,
    unpin,
    remove,
    isPinned
  }
}
