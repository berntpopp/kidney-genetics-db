/**
 * Admin Icon Mapping System
 * Provides consistent icon vocabulary for admin sections
 * Using Lucide Vue components instead of mdi-* strings
 *
 * Usage:
 * import { ADMIN_ICONS } from '@/utils/adminIcons'
 * <component :is="ADMIN_ICONS.users" class="size-5" />
 */

import type { Component } from 'vue'
import {
  LayoutDashboard,
  Users,
  MemoryStick,
  FileText,
  Settings,
  Minus,
  Dna,
  Tags,
  Package,
  DatabaseBackup,
  DatabaseZap,
  RefreshCw,
  Play,
  Square,
  Trash2,
  Pencil,
  Plus,
  CircleCheck,
  CircleAlert,
  AlertTriangle,
  Info
} from 'lucide-vue-next'

export const ADMIN_ICONS: Record<string, Component> = {
  // Main dashboard
  dashboard: LayoutDashboard,

  // User management
  users: Users,

  // System management
  cache: MemoryStick,
  logs: FileText,
  settings: Settings,

  // Data pipeline
  pipeline: Minus,
  staging: Dna,
  annotations: Tags,

  // Data management
  releases: Package,
  backups: DatabaseBackup,
  hybridSources: DatabaseZap,

  // Actions
  refresh: RefreshCw,
  play: Play,
  stop: Square,
  delete: Trash2,
  edit: Pencil,
  add: Plus,

  // Status indicators
  success: CircleCheck,
  error: CircleAlert,
  warning: AlertTriangle,
  info: Info
}

/**
 * Get Tailwind text color class based on admin section.
 * Replaces Vuetify color string with Tailwind equivalent.
 */
export const getAdminIconColor = (section: string): string => {
  const colorMap: Record<string, string> = {
    dashboard: 'text-primary',
    users: 'text-primary',
    cache: 'text-purple-600 dark:text-purple-400',
    logs: 'text-orange-600 dark:text-orange-400',
    pipeline: 'text-green-600 dark:text-green-400',
    staging: 'text-red-600 dark:text-red-400',
    annotations: 'text-teal-600 dark:text-teal-400',
    releases: 'text-indigo-600 dark:text-indigo-400',
    backups: 'text-slate-600 dark:text-slate-400',
    settings: 'text-violet-600 dark:text-violet-400',
    hybridSources: 'text-cyan-600 dark:text-cyan-400'
  }

  return colorMap[section] ?? 'text-primary'
}

export default ADMIN_ICONS
