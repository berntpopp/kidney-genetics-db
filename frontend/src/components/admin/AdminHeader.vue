<script setup lang="ts">
/**
 * Admin view header: PageHeader with the "Admin > {title}" breadcrumb, so the crumb, the
 * H1 and the dashboard card share one section name. The dashboard passes `root`.
 */
import { RouterLink } from 'vue-router'
import { PageHeader } from '@/components/shared'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'

defineProps<{
  title: string
  subtitle?: string
  /** The admin dashboard itself: breadcrumb is just "Admin" */
  root?: boolean
}>()
</script>

<template>
  <PageHeader :title="title" :description="subtitle">
    <template #breadcrumb>
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage v-if="root">Admin</BreadcrumbPage>
            <BreadcrumbLink v-else as-child>
              <RouterLink to="/admin">Admin</RouterLink>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <template v-if="!root">
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage>{{ title }}</BreadcrumbPage>
            </BreadcrumbItem>
          </template>
        </BreadcrumbList>
      </Breadcrumb>
    </template>
    <template v-if="$slots.actions" #actions>
      <slot name="actions" />
    </template>
  </PageHeader>
</template>
