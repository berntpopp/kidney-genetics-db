/**
 * Admin Icon Mapping System
 * Provides consistent icon vocabulary for admin sections
 * Using Lucide Vue components (not icon-name strings)
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
  Workflow,
  Dna,
  Tags,
  Package,
  DatabaseBackup,
  DatabaseZap,
  FileInput,
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
  pipeline: Workflow,
  staging: Dna,
  annotations: Tags,

  // Data management
  releases: Package,
  backups: DatabaseBackup,
  hybridSources: DatabaseZap,
  geneCuratorImport: FileInput,

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

export default ADMIN_ICONS
