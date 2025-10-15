/**
 * Admin breadcrumb navigation utility
 *
 * Provides consistent breadcrumb generation for all admin views.
 * Follows Material Design 3 navigation patterns.
 */

/**
 * Generate breadcrumbs for an admin page
 * @param {string} currentPageTitle - The title of the current page
 * @returns {Array} Breadcrumb items for v-breadcrumbs
 */
export const getAdminBreadcrumbs = currentPageTitle => {
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
export const ADMIN_BREADCRUMBS = {
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
