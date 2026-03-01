/**
 * Vue Router configuration
 */

import 'vue-router'
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw, NavigationGuardNext, RouteLocationNormalized } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  // eslint-disable-next-line no-unused-vars
  interface RouteMeta {
    requiresAuth?: boolean
    requiresAdmin?: boolean
    title?: string
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/Home.vue'),
    meta: { title: 'Home' }
  },
  {
    path: '/genes',
    name: 'genes',
    component: () => import('../views/Genes.vue'),
    meta: { title: 'Gene Browser' }
  },
  {
    path: '/genes/:symbol',
    name: 'gene-detail',
    component: () => import('../views/GeneDetail.vue'),
    props: true,
    meta: { title: 'Gene Detail' }
  },
  {
    path: '/genes/:symbol/structure',
    name: 'gene-structure',
    component: () => import('../views/GeneStructure.vue'),
    props: true,
    meta: { title: 'Gene Structure' },
    beforeEnter: async (
      to: RouteLocationNormalized,
      _from: RouteLocationNormalized,
      next: NavigationGuardNext
    ) => {
      // Validate gene symbol format
      const symbol = to.params['symbol']
      if (typeof symbol !== 'string' || !/^[A-Z0-9][A-Z0-9-]*$/i.test(symbol)) {
        next({ name: 'genes' })
        return
      }
      next()
    }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: 'Dashboard' }
  },
  {
    path: '/about',
    name: 'about',
    component: () => import('../views/About.vue'),
    meta: { title: 'About' }
  },
  {
    path: '/data-sources',
    name: 'data-sources',
    component: () => import('../views/DataSources.vue'),
    meta: { title: 'Data Sources' }
  },
  {
    path: '/network-analysis',
    name: 'network-analysis',
    component: () => import('../views/NetworkAnalysis.vue'),
    meta: { title: 'Network Analysis' }
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/Login.vue'),
    meta: { title: 'Login' }
  },
  {
    path: '/forgot-password',
    name: 'forgot-password',
    component: () => import('../views/ForgotPassword.vue'),
    meta: { title: 'Forgot Password' }
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('../views/Profile.vue'),
    meta: { title: 'Profile' }
  },
  // Admin routes (protected)
  {
    path: '/admin',
    name: 'admin',
    component: () => import('../views/admin/AdminDashboard.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Admin Dashboard' }
  },
  {
    path: '/admin/users',
    name: 'admin-users',
    component: () => import('../views/admin/AdminUserManagement.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'User Management' }
  },
  {
    path: '/admin/cache',
    name: 'admin-cache',
    component: () => import('../views/admin/AdminCacheManagement.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Cache Management' }
  },
  {
    path: '/admin/logs',
    name: 'admin-logs',
    component: () => import('../views/admin/AdminLogViewer.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Log Viewer' }
  },
  {
    path: '/admin/pipeline',
    name: 'admin-pipeline',
    component: () => import('../views/admin/AdminPipeline.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Pipeline Management' }
  },
  {
    path: '/admin/staging',
    name: 'admin-staging',
    component: () => import('../views/admin/AdminGeneStaging.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Gene Staging' }
  },
  {
    path: '/admin/annotations',
    name: 'admin-annotations',
    component: () => import('../views/admin/AdminAnnotations.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Annotations' }
  },
  {
    path: '/admin/releases',
    name: 'admin-releases',
    component: () => import('../views/admin/AdminReleases.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Releases' }
  },
  {
    path: '/admin/backups',
    name: 'admin-backups',
    component: () => import('../views/admin/AdminBackups.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Backups' }
  },
  {
    path: '/admin/settings',
    name: 'admin-settings',
    component: () => import('../views/admin/AdminSettings.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Settings' }
  },
  {
    path: '/admin/hybrid-sources',
    name: 'admin-hybrid-sources',
    component: () => import('../views/admin/AdminHybridSources.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: 'Hybrid Sources' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Set document title from route meta
const DEFAULT_TITLE = 'KGDB - Kidney Genetics Database'
router.afterEach(to => {
  const baseTitle = to.meta.title
  if (baseTitle) {
    // Include gene symbol in title for gene-specific pages
    const symbol = typeof to.params.symbol === 'string' ? to.params.symbol : ''
    if (symbol && (to.name === 'gene-detail' || to.name === 'gene-structure')) {
      document.title = `${symbol} - ${baseTitle} | KGDB`
    } else {
      document.title = `${baseTitle} | KGDB`
    }
  } else {
    document.title = DEFAULT_TITLE
  }
})

// Navigation guards
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login?redirect=' + to.fullPath)
  } else if (to.meta.requiresAdmin && !authStore.isAdmin) {
    next('/')
  } else {
    next()
  }
})

export default router
