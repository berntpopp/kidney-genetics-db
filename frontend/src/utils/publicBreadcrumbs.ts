/**
 * Public view breadcrumb navigation utility
 *
 * Provides consistent breadcrumb generation for all public views.
 * Follows Material Design 3 navigation patterns.
 */

/** A single breadcrumb item for v-breadcrumbs */
export interface BreadcrumbItem {
  title: string
  to?: string | null
  disabled: boolean
}

/** A page entry used to build breadcrumbs with parent pages */
export interface BreadcrumbPage {
  title: string
  to: string
}

/**
 * Generate breadcrumbs for a public page
 * @param currentPageTitle - The title of the current page
 * @param currentPagePath - Optional path override
 * @returns Breadcrumb items for v-breadcrumbs
 */
export const getPublicBreadcrumbs = (
  currentPageTitle: string,
  currentPagePath: string | null = null
): BreadcrumbItem[] => {
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
 * @param pages - Array of {title, to} objects
 * @returns Breadcrumb items for v-breadcrumbs
 */
export const getPublicBreadcrumbsWithParents = (pages: BreadcrumbPage[]): BreadcrumbItem[] => {
  const breadcrumbs: BreadcrumbItem[] = [
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
export const PUBLIC_BREADCRUMBS: Record<string, BreadcrumbItem[]> = {
  genes: getPublicBreadcrumbs('Genes', '/genes'),
  dashboard: getPublicBreadcrumbs('Dashboard', '/dashboard'),
  dataSources: getPublicBreadcrumbs('Data Sources', '/data-sources'),
  about: getPublicBreadcrumbs('About', '/about'),
  networkAnalysis: getPublicBreadcrumbs('Network Analysis', '/network-analysis')
}

/**
 * Generate breadcrumbs for gene detail page
 * @param geneSymbol - The gene symbol
 * @returns Breadcrumb items
 */
export const getGeneDetailBreadcrumbs = (geneSymbol: string): BreadcrumbItem[] => {
  return getPublicBreadcrumbsWithParents([
    { title: 'Genes', to: '/genes' },
    { title: geneSymbol, to: `/genes/${geneSymbol}` }
  ])
}

/**
 * Generate breadcrumbs for gene structure page
 * @param geneSymbol - The gene symbol
 * @returns Breadcrumb items
 */
export const getGeneStructureBreadcrumbs = (geneSymbol: string): BreadcrumbItem[] => {
  return getPublicBreadcrumbsWithParents([
    { title: 'Genes', to: '/genes' },
    { title: geneSymbol, to: `/genes/${geneSymbol}` },
    { title: 'Structure', to: `/genes/${geneSymbol}/structure` }
  ])
}
