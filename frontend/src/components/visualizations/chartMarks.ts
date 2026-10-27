/**
 * Outline for a chart mark (bar, slice, swatch) of colour `color`: the colour mixed toward the
 * theme foreground, so every series keeps >= 3:1 against the chart background (WCAG 1.4.11)
 * even for light fills such as the Okabe-Ito yellow --source-7 or --strength-1.
 */
export const markOutline = (color: string): string =>
  `color-mix(in oklab, ${color} 55%, var(--foreground))`
