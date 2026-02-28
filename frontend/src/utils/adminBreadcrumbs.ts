/**
 * Admin breadcrumb navigation utility
 *
 * Provides consistent breadcrumb generation for all admin views.
 * Follows Material Design 3 navigation patterns.
 */

/** A single breadcrumb item for v-breadcrumbs */
export interface BreadcrumbItem {
  title: string
  to?: string | null
  disabled: boolean
}

/**
 * Generate breadcrumbs for an admin page
 * @param currentPageTitle - The title of the current page
 * @returns Breadcrumb items for v-breadcrumbs
 */
export const getAdminBreadcrumbs = (currentPageTitle: string): BreadcrumbItem[] => {
  return [
    {
      title: 'Admin Dashboard',
      to: '/admin',
      disabled: false
    },
    {
      title: currentPageTitle,
      disabled: true
    }
  ]
}

/**
 * Breadcrumb configurations for each admin section
 */
export const ADMIN_BREADCRUMBS: Record<string, BreadcrumbItem[]> = {
  dashboard: getAdminBreadcrumbs('Dashboard'),
  users: getAdminBreadcrumbs('User Management'),
  cache: getAdminBreadcrumbs('Cache Management'),
  logs: getAdminBreadcrumbs('System Logs'),
  pipeline: getAdminBreadcrumbs('Pipeline Management'),
  staging: getAdminBreadcrumbs('Gene Staging'),
  annotations: getAdminBreadcrumbs('Annotation Sources'),
  releases: getAdminBreadcrumbs('Data Releases'),
  backups: getAdminBreadcrumbs('Database Backups'),
  settings: getAdminBreadcrumbs('System Settings'),
  hybridSources: getAdminBreadcrumbs('Hybrid Source Management')
}
