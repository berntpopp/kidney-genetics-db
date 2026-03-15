/**
 * Vue Router configuration
 */

import 'vue-router'
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  // eslint-disable-next-line no-unused-vars
  interface RouteMeta {
    requiresAuth?: boolean
    requiresAdmin?: boolean
    title?: string
    description?: string
    noindex?: boolean
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/Home.vue'),
    meta: {
      title: 'Home',
      description:
        'Evidence-based kidney disease gene curation with multi-source integration. Explore 571+ genes with comprehensive annotations.'
    }
  },
  {
    path: '/genes',
    name: 'genes',
    component: () => import('../views/Genes.vue'),
    meta: {
      title: 'Gene Browser',
      description:
        'Search and explore curated kidney disease gene-disease associations with evidence scores from multiple genomic sources.'
    }
  },
  {
    path: '/genes/:symbol',
    name: 'gene-detail',
    component: () => import('../views/GeneDetail.vue'),
    props: true,
    meta: {
      title: 'Gene Detail',
      description: 'Detailed gene information with evidence scores and annotations.'
    }
  },
  {
    path: '/genes/:symbol/structure',
    name: 'gene-structure',
    component: () => import('../views/GeneStructure.vue'),
    props: true,
    meta: {
      title: 'Gene Structure',
      description: 'Gene structure visualization with exon maps and protein domains.'
    },
    beforeEnter: to => {
      // Validate gene symbol format
      const symbol = to.params['symbol']
      if (typeof symbol !== 'string' || !/^[A-Z0-9][A-Z0-9-]*$/i.test(symbol)) {
        return { name: 'genes' }
      }
    }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: {
      title: 'Dashboard',
      description:
        'Comprehensive analysis of kidney disease gene-disease associations across multiple genomic data sources.'
    }
  },
  {
    path: '/about',
    name: 'about',
    component: () => import('../views/About.vue'),
    meta: {
      title: 'About',
      description:
        'Learn about the Kidney Genetics Database, its core concepts, data pipeline, and technical architecture.'
    }
  },
  {
    path: '/data-sources',
    name: 'data-sources',
    component: () => import('../views/DataSources.vue'),
    meta: {
      title: 'Data Sources',
      description:
        'Live status and statistics from integrated genomic data sources including PanelApp, ClinGen, GenCC, and more.'
    }
  },
  {
    path: '/network-analysis',
    name: 'network-analysis',
    component: () => import('../views/NetworkAnalysis.vue'),
    meta: {
      title: 'Network Analysis',
      description:
        'Explore protein-protein interaction networks and functional clusters across kidney disease genes.'
    }
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/Login.vue'),
    meta: { title: 'Login', noindex: true }
  },
  {
    path: '/forgot-password',
    name: 'forgot-password',
    component: () => import('../views/ForgotPassword.vue'),
    meta: { title: 'Forgot Password', noindex: true }
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('../views/Profile.vue'),
    meta: { title: 'Profile', noindex: true }
  },
  // Admin routes (protected)
  {
    path: '/admin',
    name: 'admin',
    component: () => import('../views/admin/AdminDashboard.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Admin Dashboard', noindex: true }
  },
  {
    path: '/admin/users',
    name: 'admin-users',
    component: () => import('../views/admin/AdminUserManagement.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'User Management', noindex: true }
  },
  {
    path: '/admin/cache',
    name: 'admin-cache',
    component: () => import('../views/admin/AdminCacheManagement.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Cache Management', noindex: true }
  },
  {
    path: '/admin/logs',
    name: 'admin-logs',
    component: () => import('../views/admin/AdminLogViewer.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Log Viewer', noindex: true }
  },
  {
    path: '/admin/pipeline',
    name: 'admin-pipeline',
    component: () => import('../views/admin/AdminPipeline.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Pipeline Management', noindex: true }
  },
  {
    path: '/admin/staging',
    name: 'admin-staging',
    component: () => import('../views/admin/AdminGeneStaging.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Gene Staging', noindex: true }
  },
  {
    path: '/admin/annotations',
    name: 'admin-annotations',
    component: () => import('../views/admin/AdminAnnotations.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Annotations', noindex: true }
  },
  {
    path: '/admin/releases',
    name: 'admin-releases',
    component: () => import('../views/admin/AdminReleases.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Releases', noindex: true }
  },
  {
    path: '/admin/backups',
    name: 'admin-backups',
    component: () => import('../views/admin/AdminBackups.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Backups', noindex: true }
  },
  {
    path: '/admin/settings',
    name: 'admin-settings',
    component: () => import('../views/admin/AdminSettings.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Settings', noindex: true }
  },
  {
    path: '/admin/hybrid-sources',
    name: 'admin-hybrid-sources',
    component: () => import('../views/admin/AdminHybridSources.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Hybrid Sources', noindex: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guards — wait for auth initialization before checking protected routes
router.beforeEach(async to => {
  const authStore = useAuthStore()

  // Wait for the silent token refresh to complete before evaluating guards.
  // This prevents redirecting to /login on page refresh while the HttpOnly
  // cookie refresh is still in-flight.
  if (to.meta.requiresAuth || to.meta.requiresAdmin) {
    await authStore.initReady
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return '/login?redirect=' + to.fullPath
  } else if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return '/'
  }
})

// Handle chunk load failures and other navigation errors
router.onError((error, to) => {
  if (error.message.includes('Failed to fetch dynamically imported module')) {
    // Chunk load failure — full page reload to get new chunks
    window.location.href = to.fullPath
  } else {
    // Log other navigation errors
    window.logService?.error('Navigation error', {
      error: error.message,
      stack: error.stack,
      route: to.fullPath
    })
  }
})

export default router
