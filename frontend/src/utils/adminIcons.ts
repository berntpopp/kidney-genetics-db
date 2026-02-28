/**
 * Admin Icon Mapping System
 * Provides consistent icon vocabulary for admin sections
 * Following Material Design Icons (mdi) naming convention
 *
 * Usage:
 * import { ADMIN_ICONS } from '@/utils/adminIcons'
 * <AdminHeader :icon="ADMIN_ICONS.users" />
 */

export const ADMIN_ICONS: Record<string, string> = {
  // Main dashboard
  dashboard: 'mdi-view-dashboard-variant',

  // User management
  users: 'mdi-account-group',

  // System management
  cache: 'mdi-memory',
  logs: 'mdi-file-document-outline',
  settings: 'mdi-cog',

  // Data pipeline
  pipeline: 'mdi-pipe',
  staging: 'mdi-dna',
  annotations: 'mdi-tag-multiple',

  // Data management
  releases: 'mdi-package-variant',
  backups: 'mdi-database-export',
  hybridSources: 'mdi-database-import',

  // Actions
  refresh: 'mdi-refresh',
  play: 'mdi-play',
  stop: 'mdi-stop',
  delete: 'mdi-delete',
  edit: 'mdi-pencil',
  add: 'mdi-plus',

  // Status indicators
  success: 'mdi-check-circle',
  error: 'mdi-alert-circle',
  warning: 'mdi-alert',
  info: 'mdi-information'
}

/**
 * Get icon color based on admin section
 * Maps to Material Design 3 color system
 */
export const getAdminIconColor = (section: string): string => {
  const colorMap: Record<string, string> = {
    dashboard: 'primary',
    users: 'primary',
    cache: 'purple',
    logs: 'orange',
    pipeline: 'green',
    staging: 'red',
    annotations: 'teal',
    releases: 'indigo',
    backups: 'blue-grey',
    settings: 'deep-purple',
    hybridSources: 'cyan'
  }

  return colorMap[section] ?? 'primary'
}

export default ADMIN_ICONS
