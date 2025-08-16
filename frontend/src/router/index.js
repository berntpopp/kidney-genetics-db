/**
 * Vue Router configuration
 */

import { createRouter, createWebHistory } from 'vue-router'

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
    path: '/about',
    name: 'about',
    component: () => import('../views/About.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
