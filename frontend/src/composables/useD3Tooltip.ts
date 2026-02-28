/**
 * D3 Tooltip Composable
 *
 * Provides reusable tooltip functionality for D3 visualizations.
 * Supports pinning tooltips on click for interactive content (links, scrolling).
 */

import * as d3 from 'd3'
import type { Selection } from 'd3'
import { ref, onUnmounted } from 'vue'
import type { Ref } from 'vue'

/** D3 Selection type for a div tooltip */
type TooltipSelection = Selection<HTMLDivElement, unknown, HTMLElement, unknown>

/** Options for showing a tooltip */
interface TooltipShowOptions {
  [key: string]: unknown
}

/** Return type for useD3Tooltip */
export interface D3TooltipReturn {
  show: (event: MouseEvent, content: string, options?: TooltipShowOptions) => void
  hide: () => void
  pin: (event: MouseEvent, content: string) => void
  unpin: () => void
  remove: () => void
  isPinned: Ref<boolean>
}

/**
 * Create a D3 tooltip composable
 * @returns Tooltip functions: show, hide, pin, unpin, remove, isPinned
 */
export function useD3Tooltip(): D3TooltipReturn {
  let tooltip: TooltipSelection | null = null
  const isPinned = ref(false)

  /**
   * Create tooltip element if it doesn't exist
   */
  const ensureTooltip = (): TooltipSelection => {
    if (!tooltip) {
      tooltip = d3
        .select<HTMLElement, unknown>('body')
        .append<HTMLDivElement>('div')
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
   * @param event - Mouse event for positioning
   * @param content - HTML content for tooltip
   * @param _options - Additional options
   */
  const show = (event: MouseEvent, content: string, _options: TooltipShowOptions = {}): void => {
    if (isPinned.value) return // Don't update if pinned

    const tip = ensureTooltip()

    tip
      .style('pointer-events', 'none')
      .html(`<div style="padding: 10px 14px;">${content}</div>`)
      .transition()
      .duration(200)
      .style('opacity', 1)

    // Position tooltip
    const tooltipNode = tip.node()
    const rect = tooltipNode?.getBoundingClientRect() ?? new DOMRect()
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

    tip.style('left', left + 'px').style('top', top + 'px')
  }

  /**
   * Pin tooltip with full content (scrollable, with close button)
   * @param event - Mouse event for positioning
   * @param content - HTML content for tooltip
   */
  const pin = (event: MouseEvent, content: string): void => {
    const tip = ensureTooltip()
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

    tip
      .style('pointer-events', 'auto')
      .html(pinnedContent)
      .transition()
      .duration(200)
      .style('opacity', 1)

    // Add close button handler
    tip.select('.tooltip-close-btn').on('click', () => {
      unpin()
    })

    // Position tooltip
    const tooltipNode = tip.node()
    const rect = tooltipNode?.getBoundingClientRect() ?? new DOMRect()
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

    tip.style('left', left + 'px').style('top', top + 'px')

    // Close on click outside
    setTimeout(() => {
      d3.select('body').on('click.tooltip-close', (e: MouseEvent) => {
        const tooltipEl = tip.node()
        if (tooltipEl && !tooltipEl.contains(e.target as Node)) {
          unpin()
        }
      })
    }, 100)
  }

  /**
   * Unpin and hide tooltip
   */
  const unpin = (): void => {
    isPinned.value = false
    d3.select('body').on('click.tooltip-close', null)
    hide()
  }

  /**
   * Hide tooltip with fade animation
   */
  const hide = (): void => {
    if (tooltip && !isPinned.value) {
      tooltip.transition().duration(300).style('opacity', 0)
    }
  }

  /**
   * Remove tooltip from DOM completely
   */
  const remove = (): void => {
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
