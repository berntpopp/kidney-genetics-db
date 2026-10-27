/**
 * One status vocabulary for pipelines, backups, releases, staging, users and logs: each
 * status maps to one tone (a status token in assets/main.css), a label and an icon, the
 * non-colour cue. Render through StatusBadge; never map statuses to colours locally.
 */
import type { Component } from 'vue'
import {
  Archive,
  Ban,
  Bug,
  CircleCheck,
  CircleDashed,
  CircleHelp,
  CircleMinus,
  CirclePause,
  CircleX,
  Clock,
  FilePen,
  Globe,
  Info,
  LoaderCircle,
  Trash2,
  TriangleAlert
} from 'lucide-vue-next'

export type StatusTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral'

export interface StatusConfig {
  tone: StatusTone
  label: string
  icon: Component
  /** Icon spins (motion-safe) for in-progress states */
  spin?: boolean
}

const s = (tone: StatusTone, label: string, icon: Component, spin?: boolean): StatusConfig =>
  spin ? { tone, label, icon, spin } : { tone, label, icon }

/** Keys are lower-case; look up through getStatusConfig() */
export const STATUS: Record<string, StatusConfig> = {
  // success
  completed: s('success', 'Completed', CircleCheck),
  success: s('success', 'Success', CircleCheck),
  ok: s('success', 'OK', CircleCheck),
  healthy: s('success', 'Healthy', CircleCheck),
  published: s('success', 'Published', Globe),
  approved: s('success', 'Approved', CircleCheck),
  active: s('success', 'Active', CircleCheck),
  // info / in progress
  running: s('info', 'Running', LoaderCircle, true),
  processing: s('info', 'Processing', LoaderCircle, true),
  in_progress: s('info', 'In progress', LoaderCircle, true),
  info: s('info', 'Info', Info),
  // warning / needs attention
  pending: s('warning', 'Pending', Clock),
  queued: s('neutral', 'Queued', Clock),
  paused: s('warning', 'Paused', CirclePause),
  warning: s('warning', 'Warning', TriangleAlert),
  degraded: s('warning', 'Degraded', TriangleAlert),
  stale: s('warning', 'Stale', TriangleAlert),
  // danger
  failed: s('danger', 'Failed', CircleX),
  error: s('danger', 'Error', CircleX),
  critical: s('danger', 'Critical', CircleX),
  unhealthy: s('danger', 'Unhealthy', CircleX),
  rejected: s('danger', 'Rejected', Ban),
  // neutral
  idle: s('neutral', 'Idle', CircleDashed),
  draft: s('neutral', 'Draft', FilePen),
  inactive: s('neutral', 'Inactive', CircleMinus),
  disabled: s('neutral', 'Disabled', CircleMinus),
  cancelled: s('neutral', 'Cancelled', CircleMinus),
  deleted: s('neutral', 'Deleted', Trash2),
  archived: s('neutral', 'Archived', Archive),
  debug: s('neutral', 'Debug', Bug),
  unknown: s('neutral', 'Unknown', CircleHelp)
}

/** Tailwind classes per tone: tinted background, readable text, matching border */
export const STATUS_TONE_CLASSES: Record<StatusTone, string> = {
  success: 'bg-success-subtle text-success border-success/30',
  warning: 'bg-warning-subtle text-warning border-warning/30',
  danger: 'bg-danger-subtle text-danger border-danger/30',
  info: 'bg-info-subtle text-info border-info/30',
  neutral: 'bg-muted text-muted-foreground border-border'
}

function httpStatus(code: number): StatusConfig {
  if (code >= 500) return s('danger', String(code), CircleX)
  if (code >= 400) return s('warning', String(code), TriangleAlert)
  if (code >= 300) return s('info', String(code), Info)
  if (code >= 200) return s('success', String(code), CircleCheck)
  return s('neutral', String(code), CircleHelp)
}

/**
 * Status config for a status string (any case; "in-progress", "IN_PROGRESS", "WARNING")
 * or an HTTP status code. Unknown strings stay neutral and keep their own text as label.
 */
export function getStatusConfig(status: string | number | null | undefined): StatusConfig {
  if (typeof status === 'number') return httpStatus(status)
  const key = (status ?? '')
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, '_')
  if (/^\d{3}$/.test(key)) return httpStatus(Number(key))
  return STATUS[key] ?? s('neutral', status ? String(status) : 'Unknown', CircleHelp)
}
