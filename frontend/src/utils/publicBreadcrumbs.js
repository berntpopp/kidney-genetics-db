/**
 * Public view breadcrumb navigation utility
 *
 * Provides consistent breadcrumb generation for all public views.
 * Follows Material Design 3 navigation patterns.
 */

/**
 * Generate breadcrumbs for a public page
 * @param {string} currentPageTitle - The title of the current page
 * @param {string} currentPagePath - Optional path override
 * @returns {Array} Breadcrumb items for v-breadcrumbs
 */
export const getPublicBreadcrumbs = (currentPageTitle, currentPagePath = null) => {
  return [
    {
      title: 'Home',
      to: '/',
      disabled: false
    },
    {
      title: currentPageTitle,
      to: currentPagePath,
      disabled: true
    }
  ]
}

/**
 * Generate breadcrumbs with parent pages
 * @param {Array} pages - Array of {title, to} objects
 * @returns {Array} Breadcrumb items for v-breadcrumbs
 */
export const getPublicBreadcrumbsWithParents = pages => {
  const breadcrumbs = [
    {
      title: 'Home',
      to: '/',
      disabled: false
    }
  ]

  pages.forEach((page, index) => {
    breadcrumbs.push({
      title: page.title,
      to: page.to,
      disabled: index === pages.length - 1 // Last item is always disabled
    })
  })

  return breadcrumbs
}

/**
 * Breadcrumb configurations for each public page
 */
export const PUBLIC_BREADCRUMBS = {
  genes: getPublicBreadcrumbs('Genes', '/genes'),
  dashboard: getPublicBreadcrumbs('Dashboard', '/dashboard'),
  dataSources: getPublicBreadcrumbs('Data Sources', '/data-sources'),
  about: getPublicBreadcrumbs('About', '/about'),
  networkAnalysis: getPublicBreadcrumbs('Network Analysis', '/network-analysis')
}

/**
 * Generate breadcrumbs for gene detail page
 * @param {string} geneSymbol - The gene symbol
 * @returns {Array} Breadcrumb items
 */
export const getGeneDetailBreadcrumbs = geneSymbol => {
  return getPublicBreadcrumbsWithParents([
    { title: 'Genes', to: '/genes' },
    { title: geneSymbol, to: `/genes/${geneSymbol}` }
  ])
}
