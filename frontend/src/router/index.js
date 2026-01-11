/**
 * Vue Router configuration
 */

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/genes',
    name: 'genes',
    component: () => import('../views/Genes.vue')
  },
  {
    path: '/genes/:symbol',
    name: 'gene-detail',
    component: () => import('../views/GeneDetail.vue'),
    props: true
  },
  {
    path: '/genes/:symbol/structure',
    name: 'gene-structure',
    component: () => import('../views/GeneStructure.vue'),
    props: true,
    beforeEnter: async (to, from, next) => {
      // Validate gene symbol format
      const symbol = to.params.symbol
      if (!/^[A-Z0-9][A-Z0-9-]*$/i.test(symbol)) {
        next({ name: 'genes' })
        return
      }
      next()
    }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('../views/Dashboard.vue')
  },
  {
    path: '/about',
    name: 'about',
    component: () => import('../views/About.vue')
  },
  {
    path: '/data-sources',
    name: 'data-sources',
    component: () => import('../views/DataSources.vue')
  },
  {
    path: '/network-analysis',
    name: 'network-analysis',
    component: () => import('../views/NetworkAnalysis.vue')
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/forgot-password',
    name: 'forgot-password',
    component: () => import('../views/ForgotPassword.vue')
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('../views/Profile.vue')
  },
  // Admin routes (protected)
  {
    path: '/admin',
    name: 'admin',
    component: () => import('../views/admin/AdminDashboard.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/users',
    name: 'admin-users',
    component: () => import('../views/admin/AdminUserManagement.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/cache',
    name: 'admin-cache',
    component: () => import('../views/admin/AdminCacheManagement.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/logs',
    name: 'admin-logs',
    component: () => import('../views/admin/AdminLogViewer.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/pipeline',
    name: 'admin-pipeline',
    component: () => import('../views/admin/AdminPipeline.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/staging',
    name: 'admin-staging',
    component: () => import('../views/admin/AdminGeneStaging.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/annotations',
    name: 'admin-annotations',
    component: () => import('../views/admin/AdminAnnotations.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/releases',
    name: 'admin-releases',
    component: () => import('../views/admin/AdminReleases.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/backups',
    name: 'admin-backups',
    component: () => import('../views/admin/AdminBackups.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/settings',
    name: 'admin-settings',
    component: () => import('../views/admin/AdminSettings.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/hybrid-sources',
    name: 'admin-hybrid-sources',
    component: () => import('../views/admin/AdminHybridSources.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guards
router.beforeEach((to, from, next) => {
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
