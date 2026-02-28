<script setup lang="ts">
/**
 * Unified admin header component
 *
 * Features:
 * - Breadcrumb navigation with shadcn-vue Breadcrumb
 * - Icon + Title alignment (horizontal)
 * - Consistent spacing (mb-6)
 * - Tailwind typography
 * - Action slot for primary actions
 *
 * Usage:
 * <AdminHeader
 *   title="User Management"
 *   subtitle="Manage user accounts and permissions"
 *   icon="mdi-account-group"
 *   icon-color="primary"
 *   :breadcrumbs="[
 *     { title: 'Admin', to: '/admin' },
 *     { title: 'User Management', disabled: true }
 *   ]"
 * />
 */
import type { Component } from 'vue'
import { RouterLink } from 'vue-router'
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { Separator } from '@/components/ui/separator'

interface BreadcrumbItemType {
  title: string
  to?: string
  disabled?: boolean
}

withDefaults(
  defineProps<{
    title: string
    subtitle?: string
    icon?: Component
    iconColor?: string
    showDivider?: boolean
    breadcrumbs?: BreadcrumbItemType[]
  }>(),
  {
    subtitle: '',
    icon: undefined,
    iconColor: 'primary',
    showDivider: false,
    breadcrumbs: () => []
  }
)
</script>

<template>
  <div class="mb-6">
    <!-- Breadcrumbs navigation (if provided) -->
    <Breadcrumb v-if="breadcrumbs && breadcrumbs.length > 0" class="mb-2">
      <BreadcrumbList>
        <template v-for="(item, index) in breadcrumbs" :key="item.title">
          <BreadcrumbItem>
            <BreadcrumbLink v-if="!item.disabled && item.to" as-child>
              <RouterLink :to="item.to">{{ item.title }}</RouterLink>
            </BreadcrumbLink>
            <BreadcrumbPage v-else>{{ item.title }}</BreadcrumbPage>
          </BreadcrumbItem>
          <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1" />
        </template>
      </BreadcrumbList>
    </Breadcrumb>

    <div class="flex items-center">
      <component :is="icon" v-if="icon" class="size-6 mr-3" />

      <!-- Title and subtitle -->
      <div class="flex-1">
        <h1 class="text-2xl font-bold">{{ title }}</h1>
        <p class="text-sm text-muted-foreground m-0">
          {{ subtitle }}
        </p>
      </div>

      <!-- Optional action slot -->
      <div v-if="$slots.actions" class="ml-4">
        <slot name="actions" />
      </div>
    </div>

    <!-- Optional divider -->
    <Separator v-if="showDivider" class="mt-4" />
  </div>
</template>
